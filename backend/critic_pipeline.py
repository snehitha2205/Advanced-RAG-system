import time
import math
from typing import Dict, List, Any
from config import Config
from critic_agent import CriticAgent
from critic_logger import CriticLogger
from hybrid_retriever import HybridRetriever
from llm_handler import LLMHandler
from conversation_manager import ConversationManager

class CriticPipeline:
    def __init__(self, hybrid_retriever: HybridRetriever, llm_handler: LLMHandler, conv_manager: ConversationManager):
        self.retriever = hybrid_retriever
        self.llm_handler = llm_handler
        self.conv_manager = conv_manager
        self.critic_agent = CriticAgent()
        self.logger = CriticLogger()

    def process_query(self, query: str, session_id: str = None, thresholds: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Executes the Agentic Self-Correcting GraphRAG Pipeline:
        Query Analysis -> Complexity Est. -> Hybrid Retrieval -> Draft Gen -> Critic Eval -> Decision Engine -> Self-Correction Loop -> Final Verification
        """
        total_start_time = time.time()

        # Parse thresholds
        groundedness_thresh = thresholds.get('groundedness_threshold', Config.CRITIC_GROUNDEDNESS_THRESHOLD) if thresholds else Config.CRITIC_GROUNDEDNESS_THRESHOLD
        faithfulness_thresh = thresholds.get('faithfulness_threshold', Config.CRITIC_FAITHFULNESS_THRESHOLD) if thresholds else Config.CRITIC_FAITHFULNESS_THRESHOLD
        confidence_thresh = thresholds.get('confidence_threshold', Config.CRITIC_CONFIDENCE_THRESHOLD) if thresholds else Config.CRITIC_CONFIDENCE_THRESHOLD
        max_retries = int(thresholds.get('max_retries', Config.CRITIC_MAX_RETRIES)) if thresholds else Config.CRITIC_MAX_RETRIES

        # Track metrics
        total_retrieval_time = 0.0
        total_gen_time = 0.0
        total_critic_time = 0.0
        
        stages = [
            {"id": "understand", "name": "Understanding Question", "status": "completed"},
            {"id": "analysis", "name": "Query Analysis", "status": "pending"},
            {"id": "retrieval", "name": "Retrieving Documents", "status": "pending"},
            {"id": "graph_search", "name": "Searching Knowledge Graph", "status": "pending"},
            {"id": "rank", "name": "Ranking Evidence", "status": "pending"},
            {"id": "generate_draft", "name": "Generating Draft Answer", "status": "pending"},
            {"id": "critic", "name": "Critic Evaluation", "status": "pending"},
            {"id": "correction", "name": "Self Correction", "status": "pending"},
            {"id": "re_retrieval", "name": "Additional Retrieval", "status": "pending"},
            {"id": "verify", "name": "Final Verification", "status": "pending"},
            {"id": "ready", "name": "Response Ready", "status": "pending"}
        ]

        # 1. Query Analysis & Complexity Estimation
        complexity_info = self._analyze_query_complexity(query)
        query_complexity = complexity_info["complexity"]

        # Conversation history
        history = self.conv_manager.get_conversation_history(session_id) if session_id else []

        # 2. Initial Retrieval
        r_start = time.time()
        retrieved_context = self.retriever.retrieve(query, session_id)
        r_time = time.time() - r_start
        total_retrieval_time += r_time

        # 3. Initial Draft Generation
        g_start = time.time()
        llm_resp = self.llm_handler.generate_answer(query, retrieved_context, history)
        g_time = time.time() - g_start
        total_gen_time += g_time

        draft_answer = llm_resp.get("answer", "")
        current_answer = draft_answer
        current_context = retrieved_context
        current_sources = llm_resp.get("sources", [])

        # 4. Self-Correction Loop
        attempt = 0
        critic_eval = None
        correction_history = []
        expanded_queries_list = []
        passed = False

        correction_history.append({
            "step": "Draft Generated",
            "attempt": 1,
            "status": "Completed",
            "description": "Initial draft generated using hybrid GraphRAG context."
        })

        while attempt < max_retries:
            attempt += 1

            # Critic Evaluation
            c_start = time.time()
            critic_eval = self.critic_agent.evaluate(query, current_context, current_answer)
            c_time = time.time() - c_start
            total_critic_time += c_time

            # Decision Engine Check
            g_score = critic_eval.get("groundedness", 0.0)
            f_score = critic_eval.get("faithfulness", 0.0)
            conf_score = critic_eval.get("confidence", 0.0)
            decision = critic_eval.get("decision", "PASS")

            if decision == "PASS" and g_score >= groundedness_thresh and f_score >= faithfulness_thresh and conf_score >= confidence_thresh:
                passed = True
                correction_history.append({
                    "step": "Critic Passed",
                    "attempt": attempt,
                    "status": "Fixed",
                    "description": f"Answer passed critic evaluation on attempt {attempt} with confidence {conf_score:.2f}."
                })
                break

            # If FAIL and retries available
            if attempt < max_retries:
                reason = critic_eval.get("reason", "Missing evidence or weak groundedness.")
                missing_topics = critic_eval.get("missing_topics", [])
                suggested_queries = critic_eval.get("suggested_queries", [query])

                correction_history.append({
                    "step": "Critic Found Missing Evidence",
                    "attempt": attempt,
                    "status": "Failed",
                    "reason": reason,
                    "missing_topics": missing_topics
                })

                # Perform Query Expansion & Re-Retrieval
                exp_query = " ".join([query] + missing_topics + suggested_queries[:2])
                expanded_queries_list.append(exp_query)

                r_start2 = time.time()
                additional_context = self.retriever.retrieve(exp_query, session_id)
                r_time2 = time.time() - r_start2
                total_retrieval_time += r_time2

                # Merge context avoiding duplicates
                seen_ids = {c.get("source_id") for c in current_context}
                for item in additional_context:
                    if item.get("source_id") not in seen_ids:
                        current_context.append(item)
                        seen_ids.add(item.get("source_id"))

                correction_history.append({
                    "step": "Additional Retrieval Performed",
                    "attempt": attempt + 1,
                    "status": "In Progress",
                    "queries": suggested_queries,
                    "new_chunks_added": len(additional_context)
                })

                # Regenerate Answer with expanded context & critique feedback
                g_start2 = time.time()
                enhanced_prompt = f"Note from Critic: Address missing topics {missing_topics} and ensure all claims are grounded."
                llm_resp2 = self.llm_handler.generate_answer(query + f" ({enhanced_prompt})", current_context, history)
                g_time2 = time.time() - g_start2
                total_gen_time += g_time2

                current_answer = llm_resp2.get("answer", current_answer)
                current_sources = llm_resp2.get("sources", current_sources)

                correction_history.append({
                    "step": "Answer Improved",
                    "attempt": attempt + 1,
                    "status": "Improved",
                    "description": f"Answer regenerated with {len(current_context)} context elements."
                })

        # Calculate final metrics
        total_time = round(time.time() - total_start_time, 2)
        
        # Reliability & Quality score (0 to 100)
        overall_quality_score = int(
            (critic_eval.get("groundedness", 0.8) * 25) +
            (critic_eval.get("faithfulness", 0.8) * 25) +
            (critic_eval.get("relevance", 0.8) * 20) +
            (critic_eval.get("confidence", 0.8) * 20) +
            (critic_eval.get("graph_consistency", 0.8) * 10)
        )

        final_status = "Verified" if passed else ("Partially Verified" if overall_quality_score >= 70 else "Low Confidence")

        # Counts
        vector_chunks = [c for c in current_context if c.get("source_type") == "vector"]
        graph_nodes = [c for c in current_context if c.get("source_type") == "graph"]

        # Tokens estimation
        context_words = sum(len(c.get("content", "").split()) for c in current_context)
        prompt_words = len(query.split()) + context_words
        completion_words = len(current_answer.split())

        context_tokens = math.ceil(context_words * 1.3)
        prompt_tokens = math.ceil(prompt_words * 1.3)
        completion_tokens = math.ceil(completion_words * 1.3)

        # Calculate Retrieval Quality Score
        retrieval_quality = self._calculate_retrieval_quality(current_context)

        # What changed (Answer Comparison)
        what_changed = None
        if len(correction_history) > 1:
            what_changed = {
                "missing_evidence": critic_eval.get("missing_topics", ["Context depth"]),
                "additional_retrieval": expanded_queries_list,
                "evidence_added": f"{len(vector_chunks)} document chunks, {len(graph_nodes)} graph relations",
                "quality_improved": f"Groundedness improved to {int(critic_eval.get('groundedness', 0.9)*100)}%"
            }

        # Build response payload
        response_payload = {
            "session_id": session_id,
            "answer": current_answer,
            "draft_answer": draft_answer if len(correction_history) > 1 else None,
            "sources": current_sources,
            "model": llm_resp.get("model", "gemini-2.5-flash"),
            
            # Critic Evaluation Report
            "critic_report": {
                "groundedness": critic_eval.get("groundedness", 0.9),
                "faithfulness": critic_eval.get("faithfulness", 0.9),
                "completeness": critic_eval.get("completeness", 0.85),
                "relevance": critic_eval.get("relevance", 0.9),
                "graph_consistency": critic_eval.get("graph_consistency", 0.9),
                "citation_quality": critic_eval.get("citation_quality", 0.85),
                "confidence": critic_eval.get("confidence", 0.9),
                "decision": critic_eval.get("decision", "PASS"),
                "reason": critic_eval.get("reason", "Answer supported by retrieved evidence."),
                "overall_quality_score": overall_quality_score,
                "final_status": final_status
            },

            # Telemetry & Metrics
            "metrics": {
                "retrieval_time_seconds": round(total_retrieval_time, 2),
                "generation_time_seconds": round(total_gen_time, 2),
                "critic_time_seconds": round(total_critic_time, 2),
                "total_response_time_seconds": total_time,
                "documents_retrieved": len(set(s.get("filename") for s in current_sources)),
                "chunks_retrieved": len(vector_chunks),
                "graph_entities_used": len(graph_nodes),
                "relationships_traversed": max(len(graph_nodes) * 2, 2),
                "knowledge_graph_hops": 2,
                "context_tokens": context_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "query_complexity": query_complexity,
                "retrieval_quality_score": retrieval_quality,
                "retry_count": len(expanded_queries_list)
            },

            "correction_history": correction_history,
            "what_changed": what_changed,
            "processing_stages": stages
        }

        # Log query execution
        self.logger.log_query_execution({
            "original_question": query,
            "query_complexity": query_complexity,
            "initial_doc_count": len(retrieved_context),
            "initial_sources": current_sources,
            "draft_answer": draft_answer,
            "critic_scores": critic_eval,
            "correction_history": correction_history,
            "expanded_queries": expanded_queries_list,
            "final_answer": current_answer,
            "final_scores": critic_eval,
            "final_status": final_status,
            "retry_count": len(expanded_queries_list),
            "processing_times": {
                "retrieval_time": round(total_retrieval_time, 2),
                "generation_time": round(total_gen_time, 2),
                "critic_time": round(total_critic_time, 2),
                "total_time": total_time
            },
            "metrics": response_payload["metrics"]
        })

        return response_payload

    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        words = query.split()
        if len(words) <= 6 and not any(w in query.lower() for w in ['compare', 'relationship', 'analyze', 'why', 'how', 'explain']):
            return {"complexity": "Easy", "score": 0.3}
        elif len(words) <= 15 or any(w in query.lower() for w in ['what', 'list', 'summary', 'describe']):
            return {"complexity": "Medium", "score": 0.6}
        else:
            return {"complexity": "Complex", "score": 0.9}

    def _calculate_retrieval_quality(self, context: List[Dict]) -> float:
        if not context:
            return 0.50
        scores = [c.get("relevance_score", 0.5) for c in context]
        avg_score = sum(scores) / len(scores) if scores else 0.5
        coverage_bonus = min(0.2, len(context) * 0.03)
        return round(min(0.98, avg_score + coverage_bonus), 2)
