"""
Extraction Metrics
====================

PURPOSE:
    Track real extraction statistics for every document processing run.

    Tracks (without ground-truth comparison):
    - Raw Entities detected (before any filtering)
    - Filtered Entities (after EntityValidator)
    - Canonical Entities (after normalization)
    - Stored Entities (after dedup, ready for Neo4j)
    - Rejected Entities (count by rejection reason)
    - Duplicate Merge Rate
    - Average Entity Confidence
    - Average Relationship Confidence
    - Average Relationship Score
    - Relationship Count by Extraction Method
    - Pipeline stage timings
"""

import time
from typing import Any, Dict, List


class ExtractionMetrics:
    """
    Tracks extraction statistics across pipeline stages.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics for a new processing run."""
        self._start_time = time.time()
        self._stage_times: Dict[str, float] = {}
        self._current_stage: str = ""

        self.metrics: Dict[str, Any] = {
            # Pipeline stages
            "stages": [],

            # Entity pipeline
            "raw_entities": 0,
            "filtered_entities": 0,
            "canonical_entities": 0,
            "stored_entities": 0,
            "rejected_entities": 0,
            "rejection_breakdown": {},
            "duplicate_merge_rate": 0.0,
            "average_entity_confidence": 0.0,

            # Relationship pipeline
            "raw_relationships": 0,
            "validated_relationships": 0,
            "stored_relationships": 0,
            "average_relationship_confidence": 0.0,
            "relationship_by_method": {},

            # Timing
            "total_processing_time_seconds": 0.0,
            "stage_times": {},
        }

    def start_stage(self, stage_name: str):
        """Mark the start of a pipeline stage."""
        self._current_stage = stage_name
        self._stage_start = time.time()

    def end_stage(self, stage_name: str, info: str = ""):
        """Mark the end of a pipeline stage and record timing."""
        elapsed = time.time() - self._stage_start
        self._stage_times[stage_name] = elapsed
        self.metrics["stage_times"][stage_name] = round(elapsed, 3)
        self.metrics["stages"].append({
            "name": stage_name,
            "time_seconds": round(elapsed, 3),
            "info": info,
        })

    def record_entity_metrics(
        self,
        raw_count: int,
        filtered_count: int,
        rejected_count: int,
        rejection_breakdown: Dict[str, int],
        canonical_count: int,
        stored_count: int,
        duplicate_merge_rate: float,
        average_confidence: float,
    ):
        """Record entity pipeline metrics."""
        self.metrics["raw_entities"] = raw_count
        self.metrics["filtered_entities"] = filtered_count
        self.metrics["rejected_entities"] = rejected_count
        self.metrics["rejection_breakdown"] = rejection_breakdown
        self.metrics["canonical_entities"] = canonical_count
        self.metrics["stored_entities"] = stored_count
        self.metrics["duplicate_merge_rate"] = duplicate_merge_rate
        self.metrics["average_entity_confidence"] = average_confidence

    def record_relationship_metrics(
        self,
        raw_count: int,
        validated_count: int,
        stored_count: int,
        average_confidence: float,
        by_method: Dict[str, int],
    ):
        """Record relationship pipeline metrics."""
        self.metrics["raw_relationships"] = raw_count
        self.metrics["validated_relationships"] = validated_count
        self.metrics["stored_relationships"] = stored_count
        self.metrics["average_relationship_confidence"] = average_confidence
        self.metrics["relationship_by_method"] = by_method

    def finalize(self):
        """Finalize metrics after all pipeline stages complete."""
        self.metrics["total_processing_time_seconds"] = round(
            time.time() - self._start_time, 3
        )

    def get_report(self) -> Dict[str, Any]:
        """Get the full metrics report."""
        self.finalize()
        return dict(self.metrics)
