"""
Stage 5: Technical Entity Detector
====================================

PURPOSE:
    General-purpose NER models miss domain-specific technical terms
    common in AI/ML research papers and documentation.

    This detector uses rule-based patterns and dictionaries to recognize:

    TECHNICAL TERMS:
        GraphRAG, Neo4j Aura, Knowledge Graph, Vector Database,
        Embedding Model, Hybrid Retrieval, Multi-hop Reasoning,
        Retriever, Critic Agent, Groundedness, Faithfulness,
        Chunk, Prompt, LLM, Gemini, Claude, GPT, LangChain,
        LlamaIndex, Cypher, FAISS, ChromaDB, RAG,
        Dynamic GraphRAG, Multimodal GraphRAG, Agentic AI,
        Evaluation Metrics

    COMPOUND ENTITIES:
        Knowledge Graph, Large Language Model, Vector Database,
        Critic Agent, Multi-hop Reasoning, etc. — always preserved
        as single entities.

    RESEARCH PAPERS:
        Patterns like "Attention Is All You Need", "BERT: Pre-training..."
    
    API/FRAMEWORK NAMES:
        LangChain, LlamaIndex, spaCy, HuggingFace, etc.

    VERSION NUMBERS:
        Python 3.9, v2.0, API v3, etc.

    All detected entities receive high confidence scores (0.90-0.95)
    since they are deterministic rule matches.
"""

import re
from typing import Any, Dict, List


class TechnicalEntityDetector:
    """
    Stage 5 of the extraction pipeline.

    Rule-based detection of technical AI/ML entities.
    Always runs (no configuration needed).
    """

    # ------------------------------------------------------------------
    # Technical term dictionary with categories
    # ------------------------------------------------------------------

    TECHNICAL_TERMS = {
        # GraphRAG ecosystem
        "GraphRAG": "SYSTEM",
        "Dynamic GraphRAG": "SYSTEM",
        "Multimodal GraphRAG": "SYSTEM",
        "Knowledge Graph": "CONCEPT",
        "Vector Database": "CONCEPT",
        "Embedding Model": "CONCEPT",
        "Hybrid Retrieval": "CONCEPT",
        "Multi-hop Reasoning": "CONCEPT",
        "Multi-Hop Reasoning": "CONCEPT",
        "Graph Query": "CONCEPT",
        "Graph Traversal": "CONCEPT",

        # System components
        "Retriever": "COMPONENT",
        "Critic Agent": "COMPONENT",
        "Dependency Parser": "COMPONENT",
        "Entity Resolver": "COMPONENT",
        "Predicate Normalizer": "COMPONENT",
        "Text Cleaner": "COMPONENT",

        # Evaluation
        "Groundedness": "METRIC",
        "Faithfulness": "METRIC",
        "Completeness": "METRIC",
        "Relevance": "METRIC",
        "Confidence Score": "METRIC",
        "Precision": "METRIC",
        "Recall": "METRIC",

        # AI/ML Models
        "LLM": "MODEL",
        "Large Language Model": "MODEL",
        "Gemini": "MODEL",
        "Claude": "MODEL",
        "GPT": "MODEL",
        "GPT-3": "MODEL",
        "GPT-4": "MODEL",
        "BERT": "MODEL",
        "RoBERTa": "MODEL",
        "Transformer": "MODEL",
        "Neural Network": "MODEL",

        # Frameworks & Tools
        "LangChain": "FRAMEWORK",
        "LlamaIndex": "FRAMEWORK",
        "spaCy": "FRAMEWORK",
        "HuggingFace": "FRAMEWORK",
        "Hugging Face": "FRAMEWORK",
        "PyTorch": "FRAMEWORK",
        "TensorFlow": "FRAMEWORK",
        "ChromaDB": "DATABASE",
        "FAISS": "DATABASE",
        "Neo4j": "DATABASE",
        "Neo4j Aura": "DATABASE",
        "Cypher": "LANGUAGE",

        # RAG concepts
        "RAG": "CONCEPT",
        "Retrieval-Augmented Generation": "CONCEPT",
        "Agentic AI": "CONCEPT",
        "Agentic RAG": "CONCEPT",
        "Chunk": "CONCEPT",
        "Chunking": "CONCEPT",
        "Prompt": "CONCEPT",
        "Prompt Engineering": "CONCEPT",
        "Token": "CONCEPT",
        "Embedding": "CONCEPT",
        "Vector Search": "CONCEPT",
        "Similarity Search": "CONCEPT",
        "Semantic Search": "CONCEPT",
        "Dense Retrieval": "CONCEPT",
        "Sparse Retrieval": "CONCEPT",

        # Evaluation concepts
        "Evaluation Metrics": "CONCEPT",
        "Answer Relevance": "METRIC",
        "Context Relevance": "METRIC",
        "Groundedness Score": "METRIC",
        "Faithfulness Score": "METRIC",

        # File formats
        "PDF": "FORMAT",
        "TXT": "FORMAT",
        "JSON": "FORMAT",
        "CSV": "FORMAT",
        "Markdown": "FORMAT",

        # Architecture
        "Pipeline": "CONCEPT",
        "Extraction Pipeline": "CONCEPT",
        "Ingestion Pipeline": "CONCEPT",
        "Query Pipeline": "CONCEPT",
        "Neural Coreference": "CONCEPT",
        "Entity Resolution": "CONCEPT",
        "Relationship Extraction": "CONCEPT",
    }

    # ------------------------------------------------------------------
    # Patterns for dynamic detection
    # ------------------------------------------------------------------

    # CamelCase terms: "MyCustomComponent", "GraphRAGSystem"
    _CAMEL_CASE = re.compile(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b")

    # Research paper titles in quotes: "Attention Is All You Need"
    _PAPER_TITLE = re.compile(r'"([A-Z][^"]{10,120})"')

    # Version numbers: v2.0, version 3.1, Python 3.9, API v2
    _VERSION = re.compile(
        r"\b(?:version\s+)?v?(\d+\.\d+(?:\.\d+)?)\b",
        re.IGNORECASE,
    )

    # Programming languages and technologies
    _TECH_WORD = re.compile(
        r"\b(Python|JavaScript|TypeScript|Java|C\+\+|Rust|Go|SQL|"
        r"NoSQL|GraphQL|Docker|Kubernetes|AWS|GCP|Azure|"
        r"REST|GraphQL|gRPC|API)\b",
    )

    # File extensions as technology references
    _FILE_TYPE = re.compile(r"\b(\.[a-zA-Z]{2,4})\b")

    def detect(self, text: str, existing_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect technical entities in text.

        Args:
            text: Preprocessed text
            existing_entities: Entities already found by HybridNER

        Returns:
            List of new entity dicts (not yet merged with existing)
        """
        entities = []

        # 1. Dictionary-based exact match
        entities.extend(self._detect_dictionary_terms(text))

        # 2. Research paper titles
        entities.extend(self._detect_paper_titles(text))

        # 3. Version numbers
        entities.extend(self._detect_versions(text))

        # 4. Tech words
        entities.extend(self._detect_tech_words(text))

        # 5. CamelCase terms (potential components/systems)
        entities.extend(self._detect_camelcase(text))

        # 6. Entity normalization for compound terms
        entities = self._normalize_compound_entities(entities)

        return entities

    def _detect_dictionary_terms(self, text: str) -> List[Dict[str, Any]]:
        """Match known technical terms using word-boundary patterns."""
        entities = []
        text_lower = text.lower()

        for term, category in sorted(
            self.TECHNICAL_TERMS.items(), key=lambda x: -len(x[0])
        ):
            # Case-insensitive search with word boundaries
            pattern = re.compile(
                r"\b" + re.escape(term) + r"\b", re.IGNORECASE
            )
            for match in pattern.finditer(text):
                entities.append({
                    "text": match.group(),
                    "label": category,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "source": "technical_dictionary",
                })

        return entities

    def _detect_paper_titles(self, text: str) -> List[Dict[str, Any]]:
        """Detect research paper titles in quotes."""
        entities = []
        for match in self._PAPER_TITLE.finditer(text):
            title = match.group(1).strip()
            if 15 <= len(title) <= 120:
                entities.append({
                    "text": title,
                    "label": "PUBLICATION",
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.90,
                    "source": "paper_title",
                })
        return entities

    def _detect_versions(self, text: str) -> List[Dict[str, Any]]:
        """Detect version numbers."""
        entities = []
        for match in self._VERSION.finditer(text):
            version = match.group(0)
            entities.append({
                "text": version.strip(),
                "label": "VERSION",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.90,
                "source": "version_detector",
            })
        return entities

    def _detect_tech_words(self, text: str) -> List[Dict[str, Any]]:
        """Detect technology names."""
        entities = []
        for match in self._TECH_WORD.finditer(text):
            entities.append({
                "text": match.group(1),
                "label": "TECHNOLOGY",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.92,
                "source": "tech_word",
            })
        return entities

    def _detect_camelcase(self, text: str) -> List[Dict[str, Any]]:
        """Detect CamelCase terms as potential entities."""
        entities = []
        seen = set()

        for match in self._CAMEL_CASE.finditer(text):
            term = match.group()
            # Skip if starts with lowercase or is a known word
            if term[0].islower() or len(term) < 6:
                continue
            # Skip common English words
            if term.lower() in {
                "therefore", "however", "moreover", "furthermore",
                "although", "although", "including", "because",
            }:
                continue
            # Skip if already in dictionary
            if term in self.TECHNICAL_TERMS:
                continue
            if term in seen:
                continue
            seen.add(term)

            entities.append({
                "text": term,
                "label": "SYSTEM",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.80,
                "source": "camelcase",
            })

        return entities

    def _normalize_compound_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Normalize compound entity detection.

        If a shorter entity is contained within a longer one,
        prefer the longer (more specific) entity.
        """
        # Sort by length descending so longer spans are preferred
        sorted_ents = sorted(
            entities, key=lambda e: e["end"] - e["start"], reverse=True
        )

        filtered = []
        covered = set()

        for ent in sorted_ents:
            span = (ent["start"], ent["end"])
            # Check if this span overlaps with an already-accepted longer span
            is_covered = any(
                cs[0] <= ent["start"] < cs[1]
                or cs[0] < ent["end"] <= cs[1]
                for cs in covered
            )
            if not is_covered:
                filtered.append(ent)
                covered.add(span)

        return filtered

