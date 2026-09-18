import sys
sys.path.insert(0, '.')

print("--- Testing Preprocessor ---")
from extraction.preprocessor import DocumentPreprocessor
pp = DocumentPreprocessor()
text = ("OpenAI Inc. was founded by Sam Altman and Elon Musk in 2015.\n\n"
        "Microsoft Corporation invested heavily in OpenAI. "
        "The company is based in San Francisco.")
clean, sents, paras = pp.process(text)
print(f"  Sentences: {len(sents)}, Paragraphs: {len(paras)}")

print("--- Testing NER Pipeline ---")
from extraction.ner_pipeline import NERPipeline
ner = NERPipeline(use_huggingface=False)
ents = ner.extract(clean)
print(f"  Raw entities: {len(ents)}")
for e in ents:
    print(f"    {e['text']:30s} [{e['label']:10s}] conf={e['confidence']}")

print("--- Testing Entity Filter ---")
from extraction.entity_filter import EntityFilter
ef = EntityFilter()
filtered = ef.filter(ents)
print(f"  After filtering: {len(filtered)}")

print("--- Testing Entity Normalizer ---")
from extraction.entity_normalizer import EntityNormalizer
en = EntityNormalizer()
normalized = en.normalize(filtered)
print(f"  After normalization: {len(normalized)}")
for e in normalized:
    print(f"    canonical={e['canonical_name']:30s} aliases={e['aliases']}")

print("--- Testing Entity Enricher ---")
from extraction.entity_enricher import EntityEnricher
ee = EntityEnricher()
enriched = ee.enrich(normalized, clean, "test_doc_001")
print(f"  Enriched: {len(enriched)}")
for e in enriched:
    print(f"    {e['canonical_name']:30s} freq={e['frequency']} importance={e['importance_score']}")

print("--- Testing Relationship Extractor ---")
from extraction.relationship_extractor import RelationshipExtractor
re_ = RelationshipExtractor(ner)
rels = re_.extract(clean, enriched, sents)
print(f"  Raw relationships: {len(rels)}")
for r in rels:
    print(f"    {r['subject']:20s} --[{r['predicate']}]--> {r['object']:20s} conf={r['confidence']} method={r['extraction_method']}")

print("--- Testing Relationship Filter ---")
from extraction.relationship_filter import RelationshipFilter
rf = RelationshipFilter()
final_rels = rf.filter(rels)
print(f"  Final relationships: {len(final_rels)}")
for r in final_rels:
    print(f"    {r['subject']:20s} --[{r['predicate']}]--> {r['object']:20s} conf={r['confidence']}")

print("\n=== ALL STAGES PASSED ===")
