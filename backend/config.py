import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
    GEMINI_MODEL = "gemini-1.5-pro"  # or "gemini-1.5-flash" for faster responses
    
    # ChromaDB
    CHROMA_PERSIST_DIR = "./chroma_db"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # ArangoDB
    ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
    ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
    ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "password")
    ARANGO_DB_NAME = "rag_knowledge_graph"
    
    # Neo4j Aura (Permanent Knowledge Graph)
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://demo.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    
    # Embeddings
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # Server
    UPLOAD_FOLDER = "./uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Retrieval
    TOP_K_VECTOR = 5
    TOP_K_GRAPH = 3

    # ---------------------------------------------------------------
    # Extraction Pipeline (enterprise-v2)
    # ---------------------------------------------------------------
    # Set to True to enable HuggingFace dslim/bert-base-NER as a
    # secondary NER model. Improves recall but adds ~2-5 s/chunk on CPU.
    # Requires: pip install transformers torch
    USE_HUGGINGFACE_NER = False

    # Minimum confidence threshold for entity acceptance (EntityFilter)
    ENTITY_MIN_CONFIDENCE = 0.60

    # Minimum confidence threshold for relationship acceptance
    REL_MIN_CONFIDENCE = 0.55

    # ---------------------------------------------------------------
    # Critic Agent Configuration
    # ---------------------------------------------------------------
    CRITIC_GROUNDEDNESS_THRESHOLD = 0.75
    CRITIC_FAITHFULNESS_THRESHOLD = 0.75
    CRITIC_CONFIDENCE_THRESHOLD = 0.75
    CRITIC_MAX_RETRIES = 3