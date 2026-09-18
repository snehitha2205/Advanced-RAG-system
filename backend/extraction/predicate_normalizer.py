"""
Stage 14: Predicate Normalizer
================================

PURPOSE:
    Normalize relationship predicates to semantic categories.

    Instead of storing raw verb lemmas (which may have many variants),
    map predicates to a canonical set of semantic relationship types.

    SEMANTIC CATEGORIES:
        USES          — uses, employs, utilizes, leverages, applies, runs
        RETRIEVES     — retrieves, queries, fetches, searches, looks up, gets
        STORES        — stores, saves, persists, caches, holds, keeps
        SUPPORTS      — supports, enables, allows, facilitates, permits
        IMPLEMENTS    — implements, realizes, builds, creates, constructs
        EVALUATES     — evaluates, assesses, measures, tests, validates, verifies
        GENERATES     — generates, produces, creates, yields, outputs, returns
        DEPENDS_ON    — depends on, relies on, requires, needs, uses
        CONTAINS      — contains, includes, comprises, consists of, holds
        HAS_COMPONENT — has component, part of, belongs to, member of
        DEVELOPS      — develops, builds, designs, architects, engineers
        PROCESSES     — processes, analyzes, transforms, converts, parses
        ENHANCES      — enhances, improves, optimizes, boosts, strengthens
        INTEGRATES    — integrates, combines, merges, fuses, joins
        TRAINS        — trains, fine-tunes, learns, fits, adapts
        COMMUNICATES  — communicates, connects, links, bridges, interfaces
        EXTENDS       — extends, expands, broadens, generalizes, specializes
        PROPOSES      — proposes, introduces, presents, outlines, defines
        ADDRESSES     — addresses, solves, resolves, tackles, handles
        ACHIEVES      — achieves, demonstrates, shows, proves, illustrates

    Each normalized predicate maps to a canonical display form and
    preserves the original verb for the relationship property.

    EXAMPLE:
        "OpenAI developed ChatGPT"
        → predicate: "developed"
        → normalized_predicate: "DEVELOPS"
        → relationship: (OpenAI) -[:RELATED_TO {predicate: "DEVELOPS"}]-> (ChatGPT)
"""

import re
from typing import Any, Dict, List, Set


class PredicateNormalizer:
    """
    Stage 14 of the extraction pipeline.

    Normalizes predicates to semantic categories.
    """

    # Verb → Normalized predicate mappings
    VERB_TO_NORM: Dict[str, str] = {
        # USES
        "use": "USES",
        "uses": "USES",
        "using": "USES",
        "used": "USES",
        "employ": "USES",
        "employs": "USES",
        "utilize": "USES",
        "utilizes": "USES",
        "leverage": "USES",
        "leverages": "USES",
        "apply": "USES",
        "applies": "USES",
        "run": "USES",
        "runs": "USES",
        "running": "USES",

        # RETRIEVES
        "retrieve": "RETRIEVES",
        "retrieves": "RETRIEVES",
        "query": "RETRIEVES",
        "queries": "RETRIEVES",
        "fetch": "RETRIEVES",
        "fetches": "RETRIEVES",
        "search": "RETRIEVES",
        "searches": "RETRIEVES",
        "lookup": "RETRIEVES",
        "looks up": "RETRIEVES",

        # STORES
        "store": "STORES",
        "stores": "STORES",
        "storing": "STORES",
        "stored": "STORES",
        "save": "STORES",
        "saves": "STORES",
        "persist": "STORES",
        "persists": "STORES",
        "cache": "STORES",
        "caches": "STORES",
        "hold": "STORES",
        "holds": "STORES",
        "keep": "STORES",
        "keeps": "STORES",

        # SUPPORTS
        "support": "SUPPORTS",
        "supports": "SUPPORTS",
        "supporting": "SUPPORTS",
        "supported": "SUPPORTS",
        "enable": "SUPPORTS",
        "enables": "SUPPORTS",
        "allow": "SUPPORTS",
        "allows": "SUPPORTS",
        "facilitate": "SUPPORTS",
        "facilitates": "SUPPORTS",
        "permit": "SUPPORTS",
        "permits": "SUPPORTS",

        # IMPLEMENTS
        "implement": "IMPLEMENTS",
        "implements": "IMPLEMENTS",
        "implemented": "IMPLEMENTS",
        "realize": "IMPLEMENTS",
        "realizes": "IMPLEMENTS",

        # EVALUATES
        "evaluate": "EVALUATES",
        "evaluates": "EVALUATES",
        "evaluated": "EVALUATES",
        "assess": "EVALUATES",
        "assesses": "EVALUATES",
        "measure": "EVALUATES",
        "measures": "EVALUATES",
        "test": "EVALUATES",
        "tests": "EVALUATES",
        "testing": "EVALUATES",
        "tested": "EVALUATES",
        "validate": "EVALUATES",
        "validates": "EVALUATES",
        "verify": "EVALUATES",
        "verifies": "EVALUATES",
        "benchmark": "EVALUATES",
        "benchmarks": "EVALUATES",

        # GENERATES
        "generate": "GENERATES",
        "generates": "GENERATES",
        "generated": "GENERATES",
        "produce": "GENERATES",
        "produces": "GENERATES",
        "produced": "GENERATES",
        "yield": "GENERATES",
        "yields": "GENERATES",
        "output": "GENERATES",
        "outputs": "GENERATES",
        "return": "GENERATES",
        "returns": "GENERATES",

        # DEPENDS_ON
        "depend on": "DEPENDS_ON",
        "depends on": "DEPENDS_ON",
        "depended on": "DEPENDS_ON",
        "rely on": "DEPENDS_ON",
        "relies on": "DEPENDS_ON",
        "relied on": "DEPENDS_ON",
        "require": "DEPENDS_ON",
        "requires": "DEPENDS_ON",
        "required": "DEPENDS_ON",
        "need": "DEPENDS_ON",
        "needs": "DEPENDS_ON",
        "based on": "DEPENDS_ON",
        "based upon": "DEPENDS_ON",

        # CONTAINS
        "contain": "CONTAINS",
        "contains": "CONTAINS",
        "containing": "CONTAINS",
        "include": "CONTAINS",
        "includes": "CONTAINS",
        "including": "CONTAINS",
        "comprise": "CONTAINS",
        "comprises": "CONTAINS",
        "comprised of": "CONTAINS",
        "consist of": "CONTAINS",
        "consists of": "CONTAINS",

        # HAS_COMPONENT
        "part of": "HAS_COMPONENT",
        "belong to": "HAS_COMPONENT",
        "belongs to": "HAS_COMPONENT",
        "member of": "HAS_COMPONENT",

        # DEVELOPS
        "develop": "DEVELOPS",
        "develops": "DEVELOPS",
        "developed": "DEVELOPS",
        "developing": "DEVELOPS",
        "build": "DEVELOPS",
        "builds": "DEVELOPS",
        "built": "DEVELOPS",
        "design": "DEVELOPS",
        "designs": "DEVELOPS",
        "designed": "DEVELOPS",
        "architect": "DEVELOPS",
        "architects": "DEVELOPS",
        "architected": "DEVELOPS",
        "engineer": "DEVELOPS",
        "engineers": "DEVELOPS",
        "engineered": "DEVELOPS",

        # PROCESSES
        "process": "PROCESSES",
        "processes": "PROCESSES",
        "processed": "PROCESSES",
        "processing": "PROCESSES",
        "analyze": "PROCESSES",
        "analyzes": "PROCESSES",
        "analyzed": "PROCESSES",
        "transform": "PROCESSES",
        "transforms": "PROCESSES",
        "transformed": "PROCESSES",
        "convert": "PROCESSES",
        "converts": "PROCESSES",
        "converted": "PROCESSES",
        "parse": "PROCESSES",
        "parses": "PROCESSES",
        "parsed": "PROCESSES",
        "extract": "PROCESSES",
        "extracts": "PROCESSES",
        "extracted": "PROCESSES",

        # ENHANCES
        "enhance": "ENHANCES",
        "enhances": "ENHANCES",
        "enhanced": "ENHANCES",
        "improve": "ENHANCES",
        "improves": "ENHANCES",
        "improved": "ENHANCES",
        "optimize": "ENHANCES",
        "optimizes": "ENHANCES",
        "optimized": "ENHANCES",
        "boost": "ENHANCES",
        "boosts": "ENHANCES",
        "strengthen": "ENHANCES",
        "strengthens": "ENHANCES",

        # INTEGRATES
        "integrate": "INTEGRATES",
        "integrates": "INTEGRATES",
        "integrated": "INTEGRATES",
        "combine": "INTEGRATES",
        "combines": "INTEGRATES",
        "combined": "INTEGRATES",
        "merge": "INTEGRATES",
        "merges": "INTEGRATES",
        "merged": "INTEGRATES",
        "fuse": "INTEGRATES",
        "fuses": "INTEGRATES",
        "join": "INTEGRATES",
        "joins": "INTEGRATES",

        # TRAINS
        "train": "TRAINS",
        "trains": "TRAINS",
        "trained": "TRAINS",
        "training": "TRAINS",
        "fine-tune": "TRAINS",
        "fine-tunes": "TRAINS",
        "fine-tuned": "TRAINS",
        "learn": "TRAINS",
        "learns": "TRAINS",
        "learned": "TRAINS",
        "fit": "TRAINS",
        "fits": "TRAINS",
        "adapt": "TRAINS",
        "adapts": "TRAINS",
        "adapted": "TRAINS",

        # COMMUNICATES
        "communicate": "COMMUNICATES",
        "communicates": "COMMUNICATES",
        "connect": "COMMUNICATES",
        "connects": "COMMUNICATES",
        "connected": "COMMUNICATES",
        "link": "COMMUNICATES",
        "links": "COMMUNICATES",
        "linked": "COMMUNICATES",
        "bridge": "COMMUNICATES",
        "bridges": "COMMUNICATES",
        "interface": "COMMUNICATES",
        "interfaces": "COMMUNICATES",

        # EXTENDS
        "extend": "EXTENDS",
        "extends": "EXTENDS",
        "extended": "EXTENDS",
        "expand": "EXTENDS",
        "expands": "EXTENDS",
        "expanded": "EXTENDS",
        "broaden": "EXTENDS",
        "broadens": "EXTENDS",
        "generalize": "EXTENDS",
        "generalizes": "EXTENDS",
        "specialize": "EXTENDS",
        "specializes": "EXTENDS",

        # PROPOSES
        "propose": "PROPOSES",
        "proposes": "PROPOSES",
        "proposed": "PROPOSES",
        "introduce": "PROPOSES",
        "introduces": "PROPOSES",
        "introduced": "PROPOSES",
        "present": "PROPOSES",
        "presents": "PROPOSES",
        "presented": "PROPOSES",
        "outline": "PROPOSES",
        "outlines": "PROPOSES",
        "outlined": "PROPOSES",
        "define": "PROPOSES",
        "defines": "PROPOSES",
        "defined": "PROPOSES",

        # ADDRESSES
        "address": "ADDRESSES",
        "addresses": "ADDRESSES",
        "addressed": "ADDRESSES",
        "solve": "ADDRESSES",
        "solves": "ADDRESSES",
        "solved": "ADDRESSES",
        "resolve": "ADDRESSES",
        "resolves": "ADDRESSES",
        "resolved": "ADDRESSES",
        "tackle": "ADDRESSES",
        "tackles": "ADDRESSES",
        "handle": "ADDRESSES",
        "handles": "ADDRESSES",
        "handled": "ADDRESSES",

        # ACHIEVES
        "achieve": "ACHIEVES",
        "achieves": "ACHIEVES",
        "achieved": "ACHIEVES",
        "demonstrate": "ACHIEVES",
        "demonstrates": "ACHIEVES",
        "demonstrated": "ACHIEVES",
        "show": "ACHIEVES",
        "shows": "ACHIEVES",
        "showed": "ACHIEVES",
        "shown": "ACHIEVES",
        "prove": "ACHIEVES",
        "proves": "ACHIEVES",
        "proved": "ACHIEVES",
        "illustrate": "ACHIEVES",
        "illustrates": "ACHIEVES",
        "illustrated": "ACHIEVES",
    }

    def normalize(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Normalize predicates for all relationships.

        Args:
            relationships: Validated relationships from RelationshipValidator.

        Returns:
            Relationships with 'normalized_predicate' added.
        """
        for rel in relationships:
            rel = self._normalize_one(rel)
        return relationships

    def _normalize_one(self, rel: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single relationship's predicate.
        """
        predicate = rel.get("predicate", "").strip().lower()

        # Direct lookup
        norm = self.VERB_TO_NORM.get(predicate)

        if not norm:
            # Try to handle multi-word predicates
            # "based on" → DEPENDS_ON
            for phrase, category in self.VERB_TO_NORM.items():
                if " " in phrase and phrase in predicate:
                    norm = category
                    break

        if not norm:
            # Try fuzzy matching: check if predicate is a substring of any key
            for key, category in self.VERB_TO_NORM.items():
                if predicate in key or key in predicate:
                    norm = category
                    break

        if not norm:
            # Default to uppercase version of the predicate
            norm = predicate.upper().replace(" ", "_")

        # Handle known edge cases
        if norm == "BASED":
            norm = "DEPENDS_ON"

        # Store normalized predicate
        rel["normalized_predicate"] = norm
        rel["predicate"] = norm  # Update predicate to normalized form

        return rel

    def normalize_predicate(self, predicate: str) -> str:
        """
        Public helper to normalize a single predicate string.
        """
        predicate = predicate.strip().lower()
        norm = self.VERB_TO_NORM.get(predicate)
        if not norm:
            norm = predicate.upper().replace(" ", "_")
        return norm

    def get_semantic_categories(self) -> List[Dict[str, Any]]:
        """Return all semantic categories for documentation."""
        categories = []
        seen = set()
        for verb, norm in self.VERB_TO_NORM.items():
            if norm not in seen:
                seen.add(norm)
                categories.append({
                    "category": norm,
                    "example_verbs": [v for v, n in self.VERB_TO_NORM.items() if n == norm][:5],
                    "verb_count": sum(1 for n in self.VERB_TO_NORM.values() if n == norm),
                })
        return categories
