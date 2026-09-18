import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('GEMINI_API_KEY', 'test')

print("--- Testing DocumentProcessor init ---")
from document_processor import DocumentProcessor
dp = DocumentProcessor()
print("[OK] DocumentProcessor initialized")

print("--- Testing KnowledgeGraph init ---")
from knowledge_graph import KnowledgeGraph
kg = KnowledgeGraph()

eid = kg.add_entity({
    "canonical_name": "OpenAI",
    "text": "OpenAI Inc.",
    "label": "ORG",
    "aliases": ["openai", "open ai"],
    "confidence": 0.90,
    "frequency": 3,
    "document_count": 1,
    "document_ids": ["doc1"],
    "first_occurrence": 0,
    "last_occurrence": 100,
    "importance_score": 1.2,
    "context_sentences": ["OpenAI was founded in 2015."],
})
print(f"[OK] add_entity returned id: {eid[:8]}...")

kg.add_relationship({
    "subject": "Microsoft",
    "subject_type": "ORG",
    "predicate": "INVESTED_IN",
    "predicate_raw": "invest",
    "object": "OpenAI",
    "object_type": "ORG",
    "confidence": 0.85,
    "sentence": "Microsoft invested in OpenAI.",
    "extraction_method": "dependency_svo",
    "multi_hop": False,
})
print("[OK] add_relationship done")

stats = kg.get_graph_stats()
ec = stats["entity_count"]
rc = stats["relationship_count"]
ld = stats["label_distribution"]
print(f"[OK] Graph stats: {ec} entities, {rc} relationships")
print(f"     Label distribution: {ld}")

# Verify no UNKNOWN labels
for edge in kg.relationships.values():
    assert edge["subject_type"] != "UNKNOWN", f"UNKNOWN subject_type found: {edge}"
    assert edge["object_type"]  != "UNKNOWN", f"UNKNOWN object_type found: {edge}"
print("[OK] No UNKNOWN entity labels in relationships")

print("\n=== ALL INTEGRATION TESTS PASSED ===")
