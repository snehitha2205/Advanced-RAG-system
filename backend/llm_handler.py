import requests
import json
from typing import List, Dict, Any
from config import Config
import time

class LLMHandler:
    def __init__(self):
        # Hardcode the API key (temporary for testing)
        self.gemini_api_key = "AQ.Ab8RN6INQWZwHWDQuV4pZe7uRgDttYkE3gq4Mqv23oAYloY3tw"
        
        # Using Gemini 2.5 Flash (confirmed working)
        self.gemini_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
        
        print('🔄 LLMHandler initialized with Gemini 2.5 Flash')
        print(f'🔑 API Key present: {"Yes" if self.gemini_api_key else "No"}')
        
        # Fallback to config if no hardcoded key
        if not self.gemini_api_key:
            self.gemini_api_key = Config.GEMINI_API_KEY
            self.gemini_model = Config.GEMINI_MODEL
            print('⚠️ Using API key from config')
    
    def generate_answer(self, query: str, context: List[Dict], conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Generate answer using Gemini 2.5 Flash with retrieved context"""
        
        print('🤖 Generating answer with Gemini 2.5 Flash...')
        
        # Prepare context text
        context_text = self._prepare_context(context)
        
        # Prepare conversation history
        history_text = ""
        if conversation_history:
            history_text = "Previous conversation:\n"
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                history_text += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
        # Create enhanced prompt for Gemini
        prompt = f"""{history_text}

You are an AI research assistant. Based on the following information from documents and knowledge graph, provide a comprehensive and well-structured answer to the query: "{query}"

Context information from documents and knowledge graph:
{context_text}

Please provide:
1. A direct answer to the question
2. Supporting evidence from the context
3. Any relevant connections or relationships from the knowledge graph
4. Citations to the source documents

If the answer cannot be found in the context, say "I don't have enough information in the provided documents to answer this question accurately."

Format the response in a clear, readable way with appropriate sections.
"""

        # Generate response with retry logic
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f'📤 Sending request to Gemini 2.5 Flash... (Attempt {attempt + 1}/{max_retries})')
                
                response = requests.post(
                    f"{self.gemini_url}?key={self.gemini_api_key}",
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": prompt
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 2048,
                            "topP": 0.95,
                            "topK": 40
                        }
                    },
                    headers={
                        'Content-Type': 'application/json',
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if (response_data and 
                        response_data.get('candidates') and 
                        response_data['candidates'][0].get('content') and 
                        response_data['candidates'][0]['content'].get('parts') and 
                        response_data['candidates'][0]['content']['parts'][0].get('text')):
                        
                        answer = response_data['candidates'][0]['content']['parts'][0]['text']
                        print('✅ Answer generated successfully')
                        
                        # Extract sources from context
                        sources = self._extract_sources(context)
                        
                        return {
                            "answer": answer,
                            "sources": sources,
                            "model": "gemini-2.5-flash",
                            "context_used": len(context)
                        }
                    else:
                        print('❌ Unexpected response structure:', json.dumps(response_data, indent=2)[:500])
                        if attempt == max_retries - 1:
                            return {
                                "answer": "Received an unexpected response format from Gemini API.",
                                "sources": [],
                                "model": "gemini-2.5-flash",
                                "error": "Unexpected response structure"
                            }
                
                elif response.status_code == 404:
                    error_msg = "The Gemini 2.5 Flash model might not be available. Please check the model name."
                    print(f'❌ {error_msg}')
                    if attempt == max_retries - 1:
                        return {
                            "answer": error_msg,
                            "sources": [],
                            "model": "gemini-2.5-flash",
                            "error": "Model not found"
                        }
                
                elif response.status_code == 400:
                    error_data = response.json()
                    print(f'❌ Bad request: {error_data}')
                    if attempt == max_retries - 1:
                        return {
                            "answer": "There was an issue with the request to Gemini. Please check the input and try again.",
                            "sources": [],
                            "model": "gemini-2.5-flash",
                            "error": str(error_data)
                        }
                
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f'⚠️ Rate limit exceeded. Waiting {wait_time} seconds...')
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 403:
                    error_msg = "Access denied. Please check if your API key has permission to use Gemini 2.5 Flash."
                    print(f'❌ {error_msg}')
                    if attempt == max_retries - 1:
                        return {
                            "answer": error_msg,
                            "sources": [],
                            "model": "gemini-2.5-flash",
                            "error": "Access denied"
                        }
                
                else:
                    print(f'❌ Unexpected status code: {response.status_code}')
                    print(f'Response: {response.text[:500]}')
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    
            except requests.exceptions.Timeout:
                print('❌ Request timeout')
                if attempt == max_retries - 1:
                    return {
                        "answer": "The Gemini service is taking too long to respond. Please try again later.",
                        "sources": [],
                        "model": "gemini-2.5-flash",
                        "error": "Timeout"
                    }
                time.sleep(2 ** attempt)
                
            except requests.exceptions.ConnectionError:
                print('❌ Connection error')
                if attempt == max_retries - 1:
                    return {
                        "answer": "Cannot connect to Gemini service. Please check your internet connection.",
                        "sources": [],
                        "model": "gemini-2.5-flash",
                        "error": "Connection error"
                    }
                time.sleep(2 ** attempt)
                
            except Exception as e:
                print(f'❌ Unexpected error: {str(e)}')
                if attempt == max_retries - 1:
                    return {
                        "answer": f"I encountered an issue while generating the response. Error: {str(e)}",
                        "sources": [],
                        "model": "gemini-2.5-flash",
                        "error": str(e)
                    }
                time.sleep(2 ** attempt)
        
        # Fallback response if all retries fail
        return {
            "answer": "I apologize, but I was unable to generate a response after multiple attempts. Please try again later.",
            "sources": [],
            "model": "gemini-2.5-flash",
            "error": "Max retries exceeded"
        }
    
    def _prepare_context(self, context: List[Dict]) -> str:
        """Prepare context text for LLM"""
        context_parts = []
        
        for i, item in enumerate(context):
            source_type = item.get("source_type", "unknown")
            content = item.get("content", "")
            
            if source_type == "vector":
                source = item.get("metadata", {}).get("filename", "Unknown")
                chunk_idx = item.get("metadata", {}).get("chunk_index", 0)
                relevance = item.get("relevance_score", 0)
                context_parts.append(f"\n[Document Source {i+1}: {source} (Chunk {chunk_idx}, Relevance: {relevance:.2f})]\n{content}")
            elif source_type == "graph":
                context_parts.append(f"\n[Knowledge Graph Relationship]\n{content}")
        
        # Limit context length to avoid token limits
        combined_context = "\n" + "="*50 + "\n".join(context_parts)
        if len(combined_context) > 10000:
            combined_context = combined_context[:10000] + "...\n[Context truncated due to length]"
        
        return combined_context
    
    def _extract_sources(self, context: List[Dict]) -> List[Dict]:
        """Extract source information from context"""
        sources = []
        seen_sources = set()
        
        for item in context:
            if item.get("source_type") == "vector":
                metadata = item.get("metadata", {})
                filename = metadata.get('filename', 'Unknown')
                chunk_idx = metadata.get('chunk_index', 0)
                source_key = f"{filename}_{chunk_idx}"
                
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    sources.append({
                        "filename": filename,
                        "chunk_index": chunk_idx,
                        "relevance_score": round(item.get("relevance_score", 0), 3),
                        "preview": item.get("content", "")[:200] + "..."
                    })
        
        # Sort by relevance score
        sources.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return sources[:5]
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Gemini API"""
        try:
            print('🧪 Testing Gemini API connection...')
            
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Hello, please respond with 'Connection successful' if you receive this."
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 50
                    }
                },
                headers={
                    'Content-Type': 'application/json',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('candidates'):
                    text = response_data['candidates'][0]['content']['parts'][0]['text']
                    return {
                        "status": "success",
                        "message": text,
                        "model": "gemini-2.5-flash"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Unexpected response structure",
                        "model": "gemini-2.5-flash"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text[:200]}",
                    "model": "gemini-2.5-flash"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": "gemini-2.5-flash"
            }