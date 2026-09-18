import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class CriticLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Could not create log directory {log_dir}: {e}")

    def log_query_execution(self, log_payload: Dict[str, Any]) -> str:
        """
        Saves a query evaluation log to `backend/logs/query_XXX.json`.
        Returns the filename created.
        """
        try:
            # Count existing query_XXX.json files to generate sequential ID
            existing_files = list(self.log_dir.glob("query_*.json"))
            next_idx = len(existing_files) + 1
            filename = f"query_{next_idx:03d}.json"
            file_path = self.log_dir / filename

            # Structured payload schema matching requirements
            structured_log = {
                "log_id": f"query_{next_idx:03d}",
                "timestamp": datetime.now().isoformat(),
                "original_question": log_payload.get("original_question", ""),
                "query_complexity": log_payload.get("query_complexity", "Medium"),
                "initial_retrieval": {
                    "document_count": log_payload.get("initial_doc_count", 0),
                    "sources": log_payload.get("initial_sources", [])
                },
                "draft_answer": log_payload.get("draft_answer", ""),
                "critic_scores": log_payload.get("critic_scores", {}),
                "correction_history": log_payload.get("correction_history", []),
                "expanded_queries": log_payload.get("expanded_queries", []),
                "final_answer": log_payload.get("final_answer", ""),
                "final_scores": log_payload.get("final_scores", {}),
                "final_status": log_payload.get("final_status", "Verified"),
                "retry_count": log_payload.get("retry_count", 0),
                "processing_times": log_payload.get("processing_times", {}),
                "metrics": log_payload.get("metrics", {})
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(structured_log, f, indent=2, ensure_ascii=False)

            print(f"💾 Critic log saved to {filename}")
            return filename
        except Exception as e:
            print(f"⚠️ Error writing critic log: {e}")
            return ""

    def get_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent query logs for inspection/debugging"""
        logs = []
        try:
            files = sorted(self.log_dir.glob("query_*.json"), key=os.path.getmtime, reverse=True)
            for fpath in files[:limit]:
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        logs.append(json.load(f))
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ Error reading critic logs: {e}")
        return logs
