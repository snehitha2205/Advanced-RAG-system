from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import traceback
from werkzeug.utils import secure_filename
from datetime import datetime
import time

from document_processor import DocumentProcessor
from vector_store import VectorStore
from knowledge_graph import KnowledgeGraph
from hybrid_retriever import HybridRetriever
from conversation_manager import ConversationManager
from llm_handler import LLMHandler
from critic_pipeline import CriticPipeline
from extraction_debugger import ExtractionDebugger
from config import Config

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure app
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER

# Create necessary directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)

# Initialize components
print("Initializing system components...")
doc_processor = DocumentProcessor()
vector_store = VectorStore()
knowledge_graph = KnowledgeGraph()
extraction_debugger = ExtractionDebugger()
hybrid_retriever = HybridRetriever(vector_store, knowledge_graph)
conv_manager = ConversationManager()
llm_handler = LLMHandler()
critic_pipeline = CriticPipeline(hybrid_retriever, llm_handler, conv_manager)
print("System & Critic Pipeline initialized successfully!")



@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "vector_store": "operational",
            "knowledge_graph": "operational",
            "llm": Config.GEMINI_MODEL
        }
    }), 200

@app.route('/upload', methods=['POST'])
def upload_document():
    """Upload and process document"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.txt'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"File type {file_ext} not supported. Use PDF or TXT"}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        print(f"Processing document: {filename}")
        start_time = time.time()
        
        # Process document
        processed_doc = doc_processor.process_document(file_path, filename)
        
        # Add to vector store
        print(f"Adding {len(processed_doc['chunks'])} chunks to vector store...")
        vector_store.add_documents(processed_doc['chunks'])
        
        # ── PERSISTENT STORAGE: Neo4j Aura ─────────────────────────────
        # Document & Chunk provenance
        print("[NEO4J] Storing document provenance...")
        knowledge_graph.add_document_provenance(processed_doc['document_id'], filename, processed_doc['chunks'])

        # Batch store entities
        print(f"[NEO4J] Storing {len(processed_doc['entities'])} entities...")
        entity_count = knowledge_graph.add_entities_batch(processed_doc['entities'])
        
        # Batch store relationships
        print(f"[NEO4J] Storing {len(processed_doc['relationships'])} relationships...")
        rel_count = knowledge_graph.add_relationships_batch(processed_doc['relationships'])
        
        # Verify persistence
        print("[NEO4J] Verifying persistence...")
        verification = knowledge_graph.verify_upload(
            processed_doc['document_id'],
            expected_entity_count=len(processed_doc['entities']),
            expected_relationship_count=len(processed_doc['relationships']),
        )
        if verification["verified"]:
            print(f"[NEO4J] ✓ Upload verified — {verification['entity_count']} entities, "
                  f"{verification['relationship_count']} relationships permanently stored")
        else:
            print(f"[NEO4J WARN] Verification issues: {verification.get('errors', [])}")
        
        processing_time = time.time() - start_time
        
        # Save Debug Extractions Artifacts
        graph_stats = knowledge_graph.get_graph_stats()
        extraction_debugger.save(
            filename=filename,
            document_id=processed_doc['document_id'],
            processing_time_seconds=processing_time,
            text_length=processed_doc['text_length'],
            chunks_created=len(processed_doc['chunks']),
            entities=processed_doc['entities'],
            relationships=processed_doc['relationships'],
            stats={},
            neo4j_node_count=verification.get('entity_count', graph_stats.get('entity_count', 0)),
            neo4j_relationship_count=verification.get('relationship_count', graph_stats.get('relationship_count', 0))
        )

        
        # Clean up uploaded file (optional - keep for reference)
        # os.remove(file_path)
        
        return jsonify({
            "message": "Document processed successfully",
            "document_id": processed_doc['document_id'],
            "filename": filename,
            "chunks": len(processed_doc['chunks']),
            "entities_found": len(processed_doc['entities']),
            "relationships_found": len(processed_doc['relationships']),
            "processing_time_seconds": round(processing_time, 2),
            "text_length": processed_doc['text_length']
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error processing document: {traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/query', methods=['POST'])
def query():
    """Handle user query through Agentic Critic Pipeline"""
    try:
        data = request.json or {}
        query_text = data.get('query', '').strip()
        session_id = data.get('session_id')
        thresholds = data.get('thresholds')
        
        if not query_text:
            return jsonify({"error": "No query provided"}), 400
        
        # Create new session if not provided
        if not session_id:
            session_id = conv_manager.create_session()
        
        print(f"Processing Agentic Query: '{query_text[:50]}...' for session {session_id[:8]}")
        
        # Add user message to conversation
        conv_manager.add_message(session_id, "user", query_text)
        
        # Execute Critic Pipeline
        pipeline_result = critic_pipeline.process_query(query_text, session_id, thresholds)
        
        # Add assistant response to conversation with full critic metadata
        conv_manager.add_message(
            session_id, 
            "assistant", 
            pipeline_result['answer'], 
            metadata={
                "sources": pipeline_result['sources'],
                "critic_report": pipeline_result['critic_report'],
                "metrics": pipeline_result['metrics'],
                "correction_history": pipeline_result['correction_history']
            }
        )
        
        return jsonify(pipeline_result), 200
        
    except Exception as e:
        print(f"Error processing query: {traceback.format_exc()}")
        return jsonify({"error": f"Error processing query: {str(e)}"}), 500

@app.route('/critic/settings', methods=['GET', 'POST'])
def critic_settings():
    """Get or update Critic Agent settings & thresholds"""
    try:
        if request.method == 'POST':
            data = request.json or {}
            if 'groundedness_threshold' in data:
                Config.CRITIC_GROUNDEDNESS_THRESHOLD = float(data['groundedness_threshold'])
            if 'faithfulness_threshold' in data:
                Config.CRITIC_FAITHFULNESS_THRESHOLD = float(data['faithfulness_threshold'])
            if 'confidence_threshold' in data:
                Config.CRITIC_CONFIDENCE_THRESHOLD = float(data['confidence_threshold'])
            if 'max_retries' in data:
                Config.CRITIC_MAX_RETRIES = int(data['max_retries'])
            
            return jsonify({
                "message": "Critic settings updated successfully",
                "settings": {
                    "groundedness_threshold": Config.CRITIC_GROUNDEDNESS_THRESHOLD,
                    "faithfulness_threshold": Config.CRITIC_FAITHFULNESS_THRESHOLD,
                    "confidence_threshold": Config.CRITIC_CONFIDENCE_THRESHOLD,
                    "max_retries": Config.CRITIC_MAX_RETRIES
                }
            }), 200

        return jsonify({
            "groundedness_threshold": Config.CRITIC_GROUNDEDNESS_THRESHOLD,
            "faithfulness_threshold": Config.CRITIC_FAITHFULNESS_THRESHOLD,
            "confidence_threshold": Config.CRITIC_CONFIDENCE_THRESHOLD,
            "max_retries": Config.CRITIC_MAX_RETRIES
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/critic/logs', methods=['GET'])
def critic_logs():
    """Get stored critic evaluation logs"""
    try:
        limit = request.args.get('limit', 20, type=int)
        logs = critic_pipeline.logger.get_logs(limit=limit)
        return jsonify({"logs": logs, "count": len(logs)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/session/new', methods=['POST'])
def new_session():
    """Create new conversation session"""
    try:
        data = request.json or {}
        session_id = conv_manager.create_session(metadata=data.get('metadata', {}))
        return jsonify({
            "session_id": session_id,
            "message": "Session created successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get conversation history"""
    try:
        session = conv_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify(session), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/session/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """Clear conversation session"""
    try:
        if conv_manager.clear_session(session_id):
            return jsonify({"message": "Session cleared successfully"}), 200
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all sessions"""
    try:
        sessions = conv_manager.list_sessions()
        return jsonify({"sessions": sessions, "count": len(sessions)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/graph/stats', methods=['GET'])
def get_graph_stats():
    """Get knowledge graph statistics"""
    try:
        stats = knowledge_graph.get_graph_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/graph/search', methods=['POST'])
def search_graph():
    """Search entities in knowledge graph"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        limit = data.get('limit', 20)
        
        if not query:
            return jsonify({"error": "No search query provided"}), 400
        
        results = knowledge_graph.search_entities(query, limit=limit)
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/documents', methods=['GET'])
def list_documents():
    """List uploaded documents"""
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size_bytes": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
        
        files.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        return jsonify({
            "documents": files,
            "count": len(files)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def system_stats():
    """Get overall system statistics"""
    try:
        vector_stats = vector_store.get_stats()
        graph_stats = knowledge_graph.get_graph_stats()
        sessions = conv_manager.list_sessions()
        
        return jsonify({
            "vector_store": vector_stats,
            "knowledge_graph": graph_stats,
            "sessions": {
                "active": len(sessions),
                "total_messages": sum(s.get('message_count', 0) for s in sessions)
            },
            "llm_model": Config.GEMINI_MODEL
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE EXPLORER API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/graph/network', methods=['POST'])
def get_graph_network():
    """Get the full graph network (nodes + edges) for visualization."""
    try:
        data = request.json or {}
        limit = data.get('limit', 200)
        result = knowledge_graph.get_filtered_graph(data.get('filters', {}), limit=limit)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/entity/<entity_id>', methods=['GET'])
def get_entity(entity_id):
    """Get a single entity by ID with full metadata."""
    try:
        entity = knowledge_graph.get_entity_by_id(entity_id)
        if entity is None:
            return jsonify({"error": "Entity not found"}), 404
        return jsonify(entity), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/entity/<entity_id>/relationships', methods=['GET'])
def get_entity_relationships(entity_id):
    """Get all relationships for a specific entity."""
    try:
        limit = request.args.get('limit', 50, type=int)
        relationships = knowledge_graph.get_relationships_for_entity(entity_id, limit=limit)
        return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/expand', methods=['POST'])
def expand_graph():
    """Expand graph by fetching neighbors for given entity IDs."""
    try:
        data = request.json or {}
        entity_ids = data.get('entity_ids', [])
        hops = data.get('hops', 1)
        if not entity_ids:
            return jsonify({"error": "No entity IDs provided"}), 400
        result = knowledge_graph.expand_neighbors(entity_ids, hops=hops)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/analytics', methods=['GET'])
def get_graph_analytics():
    """Get comprehensive graph analytics."""
    try:
        analytics = knowledge_graph.get_graph_analytics()
        return jsonify(analytics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/autocomplete', methods=['POST'])
def autocomplete_search():
    """Fast autocomplete search for entity names."""
    try:
        data = request.json or {}
        query = data.get('query', '').strip()
        limit = data.get('limit', 10)
        if not query:
            return jsonify({"results": []}), 200
        results = knowledge_graph.search_autocomplete(query, limit=limit)
        return jsonify({"results": results, "count": len(results)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/search/relationships', methods=['POST'])
def search_relationships():
    """Search relationships by predicate or entity names."""
    try:
        data = request.json or {}
        query = data.get('query', '').strip()
        limit = data.get('limit', 20)
        if not query:
            return jsonify({"results": []}), 200
        results = knowledge_graph.search_relationships(query, limit=limit)
        return jsonify({"results": results, "count": len(results)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/path', methods=['POST'])
def find_path():
    """Find shortest path between two entities."""
    try:
        data = request.json or {}
        source_id = data.get('source_id', '')
        target_id = data.get('target_id', '')
        max_hops = data.get('max_hops', 6)
        if not source_id or not target_id:
            return jsonify({"error": "Source and target IDs required"}), 400
        result = knowledge_graph.find_path_between(source_id, target_id, max_hops=max_hops)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/entities', methods=['GET'])
def get_all_entities():
    """Get all entities with pagination."""
    try:
        limit = request.args.get('limit', 500, type=int)
        entities = knowledge_graph.get_all_entities(limit=limit)
        return jsonify({"entities": entities, "count": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/relationships', methods=['GET'])
def get_all_relationships():
    """Get all relationships with pagination."""
    try:
        limit = request.args.get('limit', 500, type=int)
        relationships = knowledge_graph.get_all_relationships(limit=limit)
        return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graph/cypher', methods=['POST'])
def execute_cypher():
    """Execute a read-only Cypher query against Neo4j Aura."""
    try:
        data = request.json or {}
        cypher = data.get('cypher', '').strip()
        params = data.get('params', {})
        if not cypher:
            return jsonify({"error": "No Cypher query provided"}), 400
        result = knowledge_graph.execute_cypher_query(cypher, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Advanced RAG System with Gemini API")
    print("="*50)
    print(f"LLM Model: {Config.GEMINI_MODEL}")
    print(f"Vector DB: ChromaDB")
    print(f"Graph DB: Neo4j Aura (Permanent Knowledge Graph)")
    print(f"Server running at: http://localhost:5000")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

