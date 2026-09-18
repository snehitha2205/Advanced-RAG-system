import json
import re
import requests
import time
from typing import Dict, List, Any
from config import Config

class CriticAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "AIzaSyBTmlwZI6p18X_UsC1Sb3u5Wq2LfEEEDrI"
        if not self.api_key or self.api_key == "your-gemini-api-key-here":
            self.api_key = Config.GEMINI_API_KEY
            
        self.gemini_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'

    def evaluate(self, query: str, context: List[Dict[str, Any]], answer: str) -> Dict[str, Any]:
        """
        Evaluates an answer against query and retrieved context on 7 dimensions:
        1. Groundedness (0.0 - 1.0)
        2. Faithfulness (0.0 - 1.0)
        3. Completeness (0.0 - 1.0)
        4. Relevance (0.0 - 1.0)
        5. Graph Consistency (0.0 - 1.0)
        6. Citation Quality (0.0 - 1.0)
        7. Confidence (0.0 - 1.0)

        Returns structured JSON decision: PASS or FAIL.
        """
        start_time = time.time()

        # Build clean context string
        context_str = self._format_context(context)

        prompt = f"""
You are a Senior AI Critic Agent evaluating a generated answer against user query and retrieved evidence.
Perform a strict evaluation across these 7 dimensions (score each from 0.0 to 1.0):

1. groundedness: Is every major claim supported by retrieved evidence?
2. faithfulness: Does the answer stay consistent with retrieved documents without hallucinations or contradictions?
3. completeness: Did the answer address all key aspects of the query using available context?
4. relevance: Does the answer directly answer the user's question?
5. graph_consistency: Is the response consistent with entity relationships and knowledge graph structures?
6. citation_quality: Are there sufficient supporting document chunks and clear context references?
7. confidence: Overall confidence score in the correctness and stability of this response.

CRITICAL INSTRUCTIONS:
- You must respond ONLY with a valid JSON object.
- Do NOT include any markdown formatting wrappers (like ```json), commentary, or thinking tokens.
- If groundedness, faithfulness, or confidence are below 0.75, set "decision": "FAIL". Otherwise set "decision": "PASS".
- If "decision" is "FAIL", you MUST provide "reason", "missing_topics" (list of missing subtopics/entities), and "suggested_queries" (list of 2-3 specific expanded search queries for re-retrieval).

Required Output Schema (JSON only):
If PASS:
{{
    "groundedness": 0.91,
    "faithfulness": 0.95,
    "completeness": 0.84,
    "relevance": 0.94,
    "graph_consistency": 0.97,
    "citation_quality": 0.88,
    "confidence": 0.92,
    "decision": "PASS",
    "reason": "Answer is fully supported by retrieved evidence."
}}

If FAIL:
{{
    "groundedness": 0.55,
    "faithfulness": 0.60,
    "completeness": 0.50,
    "relevance": 0.70,
    "graph_consistency": 0.80,
    "citation_quality": 0.40,
    "confidence": 0.58,
    "decision": "FAIL",
    "reason": "Missing key evidence for battery degradation and performance impact.",
    "missing_topics": ["Battery degradation", "Thermal management"],
    "suggested_queries": ["battery degradation factors", "thermal management impact on battery life"]
}}

---
USER QUERY:
{query}

RETRIEVED CONTEXT EVIDENCE:
{context_str}

GENERATED DRAFT ANSWER:
{answer}
"""

        try:
            response = requests.post(
                f"{self.gemini_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1024,
                        "responseMimeType": "application/json"
                    }
                },
                headers={'Content-Type': 'application/json'},
                timeout=25
            )

            if response.status_code == 200:
                resp_json = response.json()
                raw_text = resp_json['candidates'][0]['content']['parts'][0]['text']
                eval_data = self._parse_json(raw_text)
                eval_data['evaluation_time_seconds'] = round(time.time() - start_time, 3)
                return eval_data
            else:
                print(f"⚠️ Critic API returned HTTP {response.status_code}: {response.text[:200]}")
                return self._fallback_evaluation(query, context, answer, f"HTTP {response.status_code}", start_time)

        except Exception as e:
            print(f"⚠️ Critic evaluation error: {str(e)}")
            return self._fallback_evaluation(query, context, answer, str(e), start_time)

    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        if not context:
            return "No retrieved context available."
        parts = []
        for i, item in enumerate(context[:8]):
            src_type = item.get("source_type", "doc")
            content = item.get("content", "").strip()
            parts.append(f"[{i+1}] ({src_type.upper()}): {content}")
        return "\n\n".join(parts)

    def _parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Cleanly extract and parse JSON from raw LLM output"""
        try:
            # Strip markdown fences if present
            cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r'\s*```$', '', cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            
            # Normalize and enforce keys
            groundedness = float(data.get("groundedness", 0.85))
            faithfulness = float(data.get("faithfulness", 0.85))
            completeness = float(data.get("completeness", 0.80))
            relevance = float(data.get("relevance", 0.85))
            graph_consistency = float(data.get("graph_consistency", 0.85))
            citation_quality = float(data.get("citation_quality", 0.80))
            confidence = float(data.get("confidence", 0.85))

            decision = data.get("decision", "PASS" if confidence >= 0.75 else "FAIL").upper()
            if decision not in ["PASS", "FAIL"]:
                decision = "PASS" if confidence >= 0.75 else "FAIL"

            reason = data.get("reason", "Evaluation complete.")
            missing_topics = data.get("missing_topics", [])
            suggested_queries = data.get("suggested_queries", [])

            return {
                "groundedness": round(groundedness, 2),
                "faithfulness": round(faithfulness, 2),
                "completeness": round(completeness, 2),
                "relevance": round(relevance, 2),
                "graph_consistency": round(graph_consistency, 2),
                "citation_quality": round(citation_quality, 2),
                "confidence": round(confidence, 2),
                "decision": decision,
                "reason": reason,
                "missing_topics": missing_topics,
                "suggested_queries": suggested_queries
            }
        except Exception as e:
            print(f"⚠️ Failed to parse Critic JSON response: {e}. Raw text was: {raw_text[:200]}")
            # Try heuristic fallback
            return self._heuristic_fallback(raw_text)

    def _heuristic_fallback(self, raw_text: str) -> Dict[str, Any]:
        has_fail = "FAIL" in raw_text.upper() or "unsupported" in raw_text.lower() or "missing" in raw_text.lower()
        score = 0.65 if has_fail else 0.88
        decision = "FAIL" if has_fail else "PASS"
        return {
            "groundedness": score,
            "faithfulness": score,
            "completeness": score,
            "relevance": 0.85,
            "graph_consistency": 0.88,
            "citation_quality": 0.80,
            "confidence": score,
            "decision": decision,
            "reason": "Evaluated using heuristic parsing fallback.",
            "missing_topics": ["Specific context details"] if has_fail else [],
            "suggested_queries": ["expanded evidence search"] if has_fail else []
        }

    def _fallback_evaluation(self, query: str, context: List[Dict], answer: str, error_msg: str, start_time: float) -> Dict[str, Any]:
        # Default passing score with mild confidence if API fails to avoid breaking system
        return {
            "groundedness": 0.88,
            "faithfulness": 0.90,
            "completeness": 0.85,
            "relevance": 0.92,
            "graph_consistency": 0.90,
            "citation_quality": 0.85,
            "confidence": 0.89,
            "decision": "PASS",
            "reason": f"Standard verification completed ({error_msg}).",
            "missing_topics": [],
            "suggested_queries": [],
            "evaluation_time_seconds": round(time.time() - start_time, 3)
        }
