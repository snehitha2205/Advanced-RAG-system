"""
Enterprise Hybrid Extraction Pipeline — 14-Stage Modular Architecture
=======================================================================

ARCHITECTURE OVERVIEW:
    Raw Document
        ↓
    [Stage 1]  TextCleaner           — Remove headers, footers, page numbers, ToC, OCR artifacts
        ↓
    [Stage 2]  SentenceSegmenter     — Split into sentences with provenance tracking
        ↓
    [Stage 3]  CorefResolver         — Resolve pronouns (OpenAI → ChatGPT example)
        ↓
    [Stage 4]  HybridNER             — Ensemble: spaCy lg + optional transformer + rules
        ↓
    [Stage 5]  TechnicalEntityDetector— Rule-based detection of AI/technical terms
        ↓
    [Stage 6]  EntityFusion          — Merge predictions from all NER sources
        ↓
    [Stage 7]  EntityValidator       — Reject headings, boilerplate, long phrases, pronouns
        ↓
    [Stage 8]  EntityNormalizer      — Canonical names, entity_id generation
        ↓
    [Stage 9]  AliasResolver         — Resolve aliases (Open AI → OpenAI, AI → Artificial Intelligence)
        ↓
    [Stage 10] Deduplicator          — Aggressive fuzzy dedup of entities
        ↓
    [Stage 11] DependencyParser      — Dependency tree SPO extraction
        ↓
    [Stage 12] RelationshipExtractor — Full relationship extraction (dep path + entity pairs)
        ↓
    [Stage 13] RelationshipValidator — Confidence scoring, supporting sentences, rejection
        ↓
    [Stage 14] PredicateNormalizer   — Semantic predicate normalization
        ↓
    Neo4j Aura (Permanent Knowledge Graph)

DESIGN PRINCIPLES:
    - Every stage is independently testable and replaceable
    - All stages preserve provenance (source document, sentence, chunk_id)
    - No in-memory fallback for graph storage
    - Pure Cypher for Neo4j (no APOC dependencies)
    - CPU-optimized with configurable transformer usage
"""

from extraction.text_cleaner import TextCleaner
from extraction.sentence_segmenter import SentenceSegmenter
from extraction.coref_resolver import CoreferenceResolver
from extraction.hybrid_ner import HybridNER
from extraction.technical_entity_detector import TechnicalEntityDetector
from extraction.entity_fusion import EntityFusion
from extraction.entity_validator import EntityValidator
from extraction.entity_normalizer import EntityNormalizer
from extraction.alias_resolver import AliasResolver
from extraction.deduplicator import Deduplicator
from extraction.dependency_parser import DependencyParser
from extraction.relationship_extractor import RelationshipExtractor
from extraction.relationship_validator import RelationshipValidator
from extraction.predicate_normalizer import PredicateNormalizer
from extraction.extraction_metrics import ExtractionMetrics
from extraction.debug_manager import DebugManager

__all__ = [
    "TextCleaner",
    "SentenceSegmenter",
    "CoreferenceResolver",
    "HybridNER",
    "TechnicalEntityDetector",
    "EntityFusion",
    "EntityValidator",
    "EntityNormalizer",
    "AliasResolver",
    "Deduplicator",
    "DependencyParser",
    "RelationshipExtractor",
    "RelationshipValidator",
    "PredicateNormalizer",
    "ExtractionMetrics",
    "DebugManager",
]

