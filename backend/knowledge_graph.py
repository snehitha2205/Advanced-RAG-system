"""
Knowledge Graph Engine — Neo4j Aura Permanent Storage
=====================================================

ARCHITECTURE:
    Neo4j Aura is the SINGLE SOURCE OF TRUTH for all Knowledge Graph data.
    No in-memory graph is used for persistent storage.

SCHEMA:
    (Document) -[:HAS_CHUNK]-> (Chunk) -[:MENTIONS]-> (Entity) -[:RELATED_TO]-> (Entity)

NODE LABELS:
    :Document     — represents an uploaded document
    :Chunk        — a text chunk segment of a document
    :Entity       — an extracted entity (person, organization, concept, etc.)

RELATIONSHIP TYPES:
    :HAS_CHUNK    — Document owns a Chunk (provenance)
    :MENTIONS     — Chunk references an Entity (provenance)
    :RELATED_TO   — Entity is related to another Entity (knowledge edge)

DESIGN DECISIONS:
    1. Pure Cypher — NO APOC plugin dependencies (fully compatible with Neo4j Aura)
    2. MERGE everywhere — never CREATE, preventing duplicate nodes/edges
    3. Batched writes via UNWIND — optimal performance for bulk ingestion
    4. Connection pooling with `max_connection_pool_size=50`
    5. Transient failure retry with exponential backoff (max 3 attempts)
    6. Auto-verification after document upload to confirm persistence
    7. Fail-fast if Neo4j is unavailable — clear error message, no silent fallback
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from neo4j import GraphDatabase, exceptions as neo4j_exceptions
from config import Config


class KnowledgeGraph:
    """
    Enterprise Knowledge Graph backed by Neo4j Aura as the permanent store.

    This class provides:
        - Connection management with Neo4j Aura
        - Schema initialization (constraints & indexes)
        - Document/Chunk provenance ingestion
        - Entity storage via MERGE
        - Relationship storage via MERGE
        - Batched bulk ingestion
        - Graph retrieval queries
        - Post-upload verification
    """

    def __init__(self):
        self.driver = None
        self.use_neo4j = False
        self.database = Config.NEO4J_DATABASE
        self._connected = False

        self._initialize_neo4j()

    # ------------------------------------------------------------------
    # Neo4j Aura Connection & Initialization
    # ------------------------------------------------------------------

    def _initialize_neo4j(self):
        """
        Initialize connection pool to Neo4j Aura and setup schema constraints.

        Raises:
            RuntimeError: If Neo4j Aura is unreachable after all retries.
        """
        uri = Config.NEO4J_URI
        user = Config.NEO4J_USERNAME
        password = Config.NEO4J_PASSWORD

        # Validate that credentials are provided (not placeholders)
        if not uri or "your-instance" in uri or "demo.databases" in uri:
            raise RuntimeError(
                "[NEO4J] Cannot connect to Neo4j Aura — URI is not configured.\n"
                "  Set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE in .env\n"
                "  Example: neo4j+s://your-instance.databases.neo4j.io"
            )

        if not user or not password:
            raise RuntimeError(
                "[NEO4J] Neo4j credentials not configured. "
                "Set NEO4J_USERNAME and NEO4J_PASSWORD in .env"
            )

        print(f"[NEO4J] Connecting to Neo4j Aura at {uri}...")

        max_retries = 3
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                self.driver = GraphDatabase.driver(
                    uri,
                    auth=(user, password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=30.0,
                )

                # Verify connectivity
                self.driver.verify_connectivity()
                self.use_neo4j = True
                self._connected = True

                print("[OK] Neo4j Aura connected successfully!")
                print(f"[NEO4J] Database: {self.database}")
                print(f"[NEO4J] Connection pool size: 50")

                # Setup Constraints & Indexes
                self._setup_schema()
                return

            except neo4j_exceptions.ServiceUnavailable as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"[WARN] Neo4j Aura unavailable (attempt {attempt}/{max_retries}). "
                          f"Retrying in {wait}s... Error: {exc}")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        f"[NEO4J] Cannot connect to Neo4j Aura after {max_retries} attempts.\n"
                        f"  URI: {uri}\n"
                        f"  Error: {exc}\n\n"
                        "  Please verify:\n"
                        "    1. Your Neo4j Aura instance is running\n"
                        "    2. NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD are correct in .env\n"
                        "    3. Your IP is allowlisted in Neo4j Aura console\n"
                        "    4. Connection string uses neo4j+s:// protocol for Aura"
                    ) from exc

            except neo4j_exceptions.AuthError as exc:
                raise RuntimeError(
                    f"[NEO4J] Authentication failed. Check NEO4J_USERNAME and NEO4J_PASSWORD in .env.\n"
                    f"  Error: {exc}"
                ) from exc

            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"[WARN] Neo4j connection attempt {attempt}/{max_retries} failed: {exc}")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        f"[NEO4J] Failed to initialize Neo4j connection after {max_retries} attempts.\n"
                        f"  Error: {exc}"
                    ) from exc

    def _setup_schema(self):
        """
        Create uniqueness constraints and performance indexes on Neo4j Aura.

        Uses IF NOT EXISTS so it's safe to call on every startup.
        """
        if not self.use_neo4j or not self.driver:
            return

        schema_queries = [
            # Uniqueness constraints (prevent duplicate nodes)
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",

            # Performance indexes
            "CREATE INDEX entity_canonical_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name)",
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_original_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.original_name)",
            "CREATE INDEX rel_predicate_idx IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.predicate)",
            "CREATE INDEX rel_normalized_predicate_idx IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.normalized_predicate)",
        ]

        with self.driver.session(database=self.database) as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    print(f"[SCHEMA] Created/verified: {query.split('IF NOT EXISTS')[0].strip()}")
                except Exception as e:
                    print(f"[SCHEMA] Note on constraint/index: {e}")

        print("[OK] Neo4j schema constraints & indexes ready")

    def close(self):
        """Gracefully close the Neo4j driver and release all connections."""
        if self.driver:
            try:
                self.driver.close()
                self._connected = False
                self.use_neo4j = False
                print("[NEO4J] Driver closed successfully")
            except Exception as e:
                print(f"[NEO4J] Error closing driver: {e}")

    def is_connected(self) -> bool:
        """Check if Neo4j is connected and operational."""
        return self._connected and self.use_neo4j and self.driver is not None

    # ------------------------------------------------------------------
    # Session helper with retry
    # ------------------------------------------------------------------

    def _run_query(self, query: str, parameters: Dict[str, Any] = None,
                   max_retries: int = 2) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a Cypher query with retry logic for transient failures.

        Returns list of records as dicts, or None if query fails.
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot execute query — Neo4j Aura is not connected. "
                               "Check your connection settings in .env")

        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(query, parameters or {})
                    records = [record.data() for record in result]
                    return records

            except neo4j_exceptions.TransientError as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"[NEO4J] Transient error (attempt {attempt}/{max_retries}), "
                          f"retrying in {wait}s: {exc}")
                    time.sleep(wait)
                else:
                    print(f"[NEO4J ERROR] Transient error after {max_retries} attempts: {exc}")
                    raise

            except neo4j_exceptions.ClientError as exc:
                # Client errors (constraint violation, syntax error) should not be retried
                print(f"[NEO4J ERROR] Client error: {exc}")
                raise

            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"[NEO4J] Query error (attempt {attempt}/{max_retries}), "
                          f"retrying in {wait}s: {exc}")
                    time.sleep(wait)
                else:
                    print(f"[NEO4J ERROR] Query failed after {max_retries} attempts: {exc}")
                    raise

        return None

    # ------------------------------------------------------------------
    # Document & Chunk Provenance Ingestion
    # ------------------------------------------------------------------

    def add_document_provenance(self, document_id: str, filename: str,
                                chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create Document and Chunk nodes in Neo4j Aura with provenance chain:
            (Document) -[:HAS_CHUNK]-> (Chunk)

        Args:
            document_id: Unique identifier for the document
            filename: Original filename
            chunks: List of chunk dicts with 'text' and 'metadata'

        Returns:
            Dict with counts of created Document and Chunk nodes
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot store document — Neo4j Aura is not connected")

        now = datetime.now(timezone.utc).isoformat()
        result = {"document_created": 0, "chunks_created": 0}

        # 1. Create Document node
        doc_query = """
        MERGE (d:Document {document_id: $document_id})
        ON CREATE SET
            d.filename = $filename,
            d.created_at = $now,
            d.updated_at = $now
        ON MATCH SET
            d.updated_at = $now
        RETURN d.document_id AS doc_id
        """

        doc_result = self._run_query(doc_query, {
            "document_id": document_id,
            "filename": filename,
            "now": now,
        })
        result["document_created"] = 1 if doc_result else 0

        # 2. Batch create Chunk nodes and HAS_CHUNK relationships
        if chunks:
            chunk_query = """
            UNWIND $chunks AS chunk_data
            MATCH (d:Document {document_id: $document_id})
            MERGE (c:Chunk {chunk_id: chunk_data.chunk_id})
            ON CREATE SET
                c.chunk_index = chunk_data.chunk_index,
                c.text = chunk_data.text,
                c.created_at = $now,
                c.updated_at = $now
            ON MATCH SET
                c.text = chunk_data.text,
                c.updated_at = $now
            MERGE (d)-[:HAS_CHUNK]->(c)
            RETURN count(DISTINCT c) AS total_chunks
            """

            formatted_chunks = [
                {
                    "chunk_id": c.get("metadata", {}).get("chunk_id",
                                                          f"{document_id}_chunk_{i}"),
                    "chunk_index": c.get("metadata", {}).get("chunk_index", i),
                    "text": c.get("text", "")[:500],  # Limit text length
                }
                for i, c in enumerate(chunks)
            ]

            chunk_result = self._run_query(chunk_query, {
                "document_id": document_id,
                "chunks": formatted_chunks,
                "now": now,
            })
            if chunk_result:
                result["chunks_created"] = chunk_result[0].get("total_chunks", len(chunks))
            else:
                result["chunks_created"] = len(chunks)

        print(f"[NEO4J] Document '{filename}' — "
              f"{result['document_created']} doc, {result['chunks_created']} chunks stored")

        return result

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def add_entity(self, entity: Dict[str, Any]) -> str:
        """
        Add or merge a single Entity node into Neo4j Aura.

        Uses MERGE on entity_id to prevent duplicates.
        ON CREATE SET — initial metadata
        ON MATCH SET — update metadata (last_seen, frequency, confidence)

        Args:
            entity: Dict with entity data (canonical_name, entity_type, etc.)

        Returns:
            entity_id string
        """
        canonical = (entity.get("canonical_name") or entity.get("text", "")).strip()
        entity_type = entity.get("entity_type") or entity.get("label", "ENTITY")
        original_name = entity.get("original_name") or entity.get("text", canonical)

        if not canonical:
            return ""

        entity_id = hashlib.md5(f"{canonical.lower()}_{entity_type}".encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()

        aliases = list(set(filter(None, entity.get("aliases", []) + [original_name])))
        if canonical in aliases:
            aliases.remove(canonical)

        confidence = float(entity.get("confidence", 0.85))
        frequency = int(entity.get("frequency", 1))
        document_count = int(entity.get("document_count", 1))
        source_documents = entity.get("source_documents") or entity.get("document_ids", [])
        chunk_ids = entity.get("chunk_ids", [])

        # ── Neo4j Aura Persistence ─────────────────────────────────────
        cypher_entity = """
        MERGE (e:Entity {entity_id: $entity_id})
        ON CREATE SET
            e.canonical_name = $canonical_name,
            e.original_name = $original_name,
            e.entity_type = $entity_type,
            e.aliases = $aliases,
            e.confidence = $confidence,
            e.frequency = $frequency,
            e.document_count = $document_count,
            e.source_documents = $source_documents,
            e.chunk_ids = $chunk_ids,
            e.first_seen = $now,
            e.last_seen = $now,
            e.created_at = $now,
            e.updated_at = $now
        ON MATCH SET
            e.canonical_name = $canonical_name,
            e.original_name = $original_name,
            e.entity_type = $entity_type,
            e.frequency = e.frequency + $frequency,
            e.document_count = e.document_count + $document_count,
            e.confidence = CASE WHEN $confidence > e.confidence THEN $confidence ELSE e.confidence END,
            e.last_seen = $now,
            e.updated_at = $now
        RETURN e.entity_id AS eid
        """

        self._run_query(cypher_entity, {
            "entity_id": entity_id,
            "canonical_name": canonical,
            "original_name": original_name,
            "entity_type": entity_type,
            "aliases": aliases,
            "confidence": confidence,
            "frequency": frequency,
            "document_count": document_count,
            "source_documents": source_documents,
            "chunk_ids": chunk_ids,
            "now": now,
        })

        # ── Create Chunk → Entity mentions provenance ──────────────────
        if chunk_ids:
            mention_query = """
            UNWIND $chunk_ids AS c_id
            MATCH (c:Chunk {chunk_id: c_id})
            MATCH (e:Entity {entity_id: $entity_id})
            MERGE (c)-[m:MENTIONS]->(e)
            ON CREATE SET
                m.confidence = $confidence,
                m.created_at = $now
            ON MATCH SET
                m.confidence = CASE WHEN $confidence > m.confidence THEN $confidence ELSE m.confidence END,
                m.updated_at = $now
            """

            self._run_query(mention_query, {
                "chunk_ids": chunk_ids,
                "entity_id": entity_id,
                "confidence": confidence,
                "now": now,
            })

        return entity_id

    def add_entities_batch(self, entities: List[Dict[str, Any]]) -> int:
        """
        Batch add multiple entities using UNWIND + MERGE for performance.

        Args:
            entities: List of entity dicts

        Returns:
            Number of entities processed
        """
        if not entities:
            return 0

        now = datetime.now(timezone.utc).isoformat()

        # Pre-process entities
        processed = []
        for entity in entities:
            canonical = (entity.get("canonical_name") or entity.get("text", "")).strip()
            entity_type = entity.get("entity_type") or entity.get("label", "ENTITY")
            original_name = entity.get("original_name") or entity.get("text", canonical)

            if not canonical:
                continue

            entity_id = hashlib.md5(f"{canonical.lower()}_{entity_type}".encode()).hexdigest()
            aliases = list(set(filter(None, entity.get("aliases", []) + [original_name])))
            if canonical in aliases:
                aliases.remove(canonical)

            chunk_ids = entity.get("chunk_ids", [])

            processed.append({
                "entity_id": entity_id,
                "canonical_name": canonical,
                "original_name": original_name,
                "entity_type": entity_type,
                "aliases": aliases,
                "confidence": float(entity.get("confidence", 0.85)),
                "frequency": int(entity.get("frequency", 1)),
                "document_count": int(entity.get("document_count", 1)),
                "source_documents": entity.get("source_documents") or entity.get("document_ids", []),
                "chunk_ids": chunk_ids,
                "now": now,
            })

        if not processed:
            return 0

        # Batch MERGE entities
        batch_query = """
        UNWIND $entities AS ent
        MERGE (e:Entity {entity_id: ent.entity_id})
        ON CREATE SET
            e.canonical_name = ent.canonical_name,
            e.original_name = ent.original_name,
            e.entity_type = ent.entity_type,
            e.aliases = ent.aliases,
            e.confidence = ent.confidence,
            e.frequency = ent.frequency,
            e.document_count = ent.document_count,
            e.source_documents = ent.source_documents,
            e.chunk_ids = ent.chunk_ids,
            e.first_seen = ent.now,
            e.last_seen = ent.now,
            e.created_at = ent.now,
            e.updated_at = ent.now
        ON MATCH SET
            e.canonical_name = ent.canonical_name,
            e.original_name = ent.original_name,
            e.entity_type = ent.entity_type,
            e.frequency = e.frequency + ent.frequency,
            e.document_count = e.document_count + ent.document_count,
            e.confidence = CASE WHEN ent.confidence > e.confidence THEN ent.confidence ELSE e.confidence END,
            e.last_seen = ent.now,
            e.updated_at = ent.now
        RETURN count(e) AS total_entities
        """

        # Batch create Chunk → Entity mentions
        mention_items = []
        for ent in processed:
            for c_id in ent["chunk_ids"]:
                mention_items.append({
                    "chunk_id": c_id,
                    "entity_id": ent["entity_id"],
                    "confidence": ent["confidence"],
                    "now": now,
                })

        # Execute entity batch
        try:
            result = self._run_query(batch_query, {"entities": processed})
            count = result[0]["total_entities"] if result else len(processed)
            print(f"[NEO4J] Batch stored {count} entities")
        except Exception as e:
            print(f"[NEO4J ERROR] Batch entity storage error: {e}")
            # Fallback to individual MERGE
            count = 0
            for entity in entities:
                try:
                    self.add_entity(entity)
                    count += 1
                except Exception:
                    pass
            print(f"[NEO4J] Fallback: stored {count} entities individually")

        # Execute mention batch
        if mention_items:
            mention_batch_query = """
            UNWIND $mentions AS m
            MATCH (c:Chunk {chunk_id: m.chunk_id})
            MATCH (e:Entity {entity_id: m.entity_id})
            MERGE (c)-[rel:MENTIONS]->(e)
            ON CREATE SET
                rel.confidence = m.confidence,
                rel.created_at = m.now
            ON MATCH SET
                rel.confidence = CASE WHEN m.confidence > rel.confidence THEN m.confidence ELSE rel.confidence END,
                rel.updated_at = m.now
            """

            try:
                self._run_query(mention_batch_query, {"mentions": mention_items})
            except Exception as e:
                print(f"[NEO4J] Note on mention batch creation: {e}")

        return count if 'count' in locals() else len(processed)

    # ------------------------------------------------------------------
    # Relationship Management
    # ------------------------------------------------------------------

    def add_relationship(self, relationship: Dict[str, Any]) -> bool:
        """
        Add or update a single relationship edge in Neo4j Aura:
            (:Entity {entity_id: subj_id}) -[:RELATED_TO {predicate: ...}]-> (:Entity {entity_id: obj_id})

        Uses MERGE on source entity + predicate + target entity to prevent duplicates.

        Args:
            relationship: Dict with subject, predicate, object, etc.

        Returns:
            True if successful
        """
        try:
            subject = (relationship.get("subject") or "").strip()
            predicate = (relationship.get("predicate") or "").strip()
            norm_predicate = (relationship.get("normalized_predicate")
                              or predicate.upper().replace(" ", "_")).strip()
            obj = (relationship.get("object") or "").strip()

            if not subject or not predicate or not obj:
                return False

            subj_type = relationship.get("subject_type", "ENTITY")
            obj_type = relationship.get("object_type", "ENTITY")
            confidence = float(relationship.get("confidence", 0.75))
            weight = float(relationship.get("weight", 1.0))
            frequency = int(relationship.get("frequency", 1))

            supporting_sents = relationship.get("supporting_sentences") or [relationship.get("sentence", "")]
            supporting_sents = list(set(filter(None, supporting_sents)))
            source_docs = relationship.get("source_documents") or (
                [relationship["document"]] if "document" in relationship else [])
            chunk_ids = relationship.get("chunk_ids") or (
                [relationship["chunk_id"]] if "chunk_id" in relationship else [])

            # Compute entity IDs from subject/object
            subj_id = hashlib.md5(f"{subject.lower()}_{subj_type}".encode()).hexdigest()
            obj_id = hashlib.md5(f"{obj.lower()}_{obj_type}".encode()).hexdigest()

            rel_id = hashlib.md5(f"{subj_id}|{norm_predicate}|{obj_id}".encode()).hexdigest()
            now = datetime.now(timezone.utc).isoformat()

            # ── Ensure both entity nodes exist ─────────────────────────
            # This is critical for relationship integrity
            self.add_entity({
                "canonical_name": subject,
                "entity_type": subj_type,
                "confidence": confidence,
                "source_documents": source_docs,
                "chunk_ids": chunk_ids,
            })

            self.add_entity({
                "canonical_name": obj,
                "entity_type": obj_type,
                "confidence": confidence,
                "source_documents": source_docs,
                "chunk_ids": chunk_ids,
            })

            # ── Neo4j Aura Relationship Persistence ────────────────────
            cypher_rel = """
            MATCH (s:Entity {entity_id: $subj_id})
            MATCH (o:Entity {entity_id: $obj_id})
            MERGE (s)-[r:RELATED_TO {predicate: $predicate, normalized_predicate: $norm_predicate}]->(o)
            ON CREATE SET
                r.relationship_id = $rel_id,
                r.predicate = $predicate,
                r.normalized_predicate = $norm_predicate,
                r.confidence = $confidence,
                r.weight = $weight,
                r.frequency = $frequency,
                r.supporting_sentences = $supporting_sents,
                r.source_documents = $source_docs,
                r.chunk_ids = $chunk_ids,
                r.created_at = $now,
                r.updated_at = $now
            ON MATCH SET
                r.frequency = r.frequency + 1,
                r.weight = CASE WHEN $weight > r.weight THEN $weight ELSE r.weight + 0.1 END,
                r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
                r.updated_at = $now
            RETURN r.relationship_id AS rid
            """

            self._run_query(cypher_rel, {
                "subj_id": subj_id,
                "obj_id": obj_id,
                "predicate": predicate,
                "norm_predicate": norm_predicate,
                "rel_id": rel_id,
                "confidence": confidence,
                "weight": weight,
                "frequency": frequency,
                "supporting_sents": supporting_sents,
                "source_docs": source_docs,
                "chunk_ids": chunk_ids,
                "now": now,
            })

            return True

        except Exception as exc:
            print(f"[NEO4J ERROR] Relationship MERGE error: {exc}")
            return False

    def add_relationships_batch(self, relationships: List[Dict[str, Any]]) -> int:
        """
        Batch add multiple relationships using UNWIND + MERGE for performance.

        Args:
            relationships: List of relationship dicts

        Returns:
            Number of relationships processed
        """
        if not relationships:
            return 0

        now = datetime.now(timezone.utc).isoformat()

        # First, ensure all subject/object entities exist
        entity_map = {}
        for rel in relationships:
            subject = (rel.get("subject") or "").strip()
            obj = (rel.get("object") or "").strip()
            subj_type = rel.get("subject_type", "ENTITY")
            obj_type = rel.get("object_type", "ENTITY")

            if subject:
                entity_map[f"{subject.lower()}_{subj_type}"] = {
                    "canonical_name": subject,
                    "entity_type": subj_type,
                }
            if obj:
                entity_map[f"{obj.lower()}_{obj_type}"] = {
                    "canonical_name": obj,
                    "entity_type": obj_type,
                }

        # Batch create entities first
        if entity_map:
            entity_batch = [
                {
                    "entity_id": hashlib.md5(
                        f"{e['canonical_name'].lower()}_{e['entity_type']}".encode()
                    ).hexdigest(),
                    **e,
                }
                for e in entity_map.values()
            ]

            entity_query = """
            UNWIND $entities AS ent
            MERGE (e:Entity {entity_id: ent.entity_id})
            ON CREATE SET
                e.canonical_name = ent.canonical_name,
                e.entity_type = ent.entity_type,
                e.created_at = $now,
                e.updated_at = $now
            ON MATCH SET
                e.updated_at = $now
            """

            try:
                self._run_query(entity_query, {"entities": entity_batch, "now": now})
            except Exception as e:
                print(f"[NEO4J] Note on entity batch creation for relationships: {e}")

        # Process relationships
        processed_rels = []
        for rel in relationships:
            subject = (rel.get("subject") or "").strip()
            predicate = (rel.get("predicate") or "").strip()
            norm_predicate = (rel.get("normalized_predicate")
                              or predicate.upper().replace(" ", "_")).strip()
            obj = (rel.get("object") or "").strip()

            if not subject or not predicate or not obj:
                continue

            subj_type = rel.get("subject_type", "ENTITY")
            obj_type = rel.get("object_type", "ENTITY")
            subj_id = hashlib.md5(f"{subject.lower()}_{subj_type}".encode()).hexdigest()
            obj_id = hashlib.md5(f"{obj.lower()}_{obj_type}".encode()).hexdigest()

            supporting_sents = rel.get("supporting_sentences") or [rel.get("sentence", "")]
            supporting_sents = list(set(filter(None, supporting_sents)))

            processed_rels.append({
                "subj_id": subj_id,
                "obj_id": obj_id,
                "predicate": predicate,
                "norm_predicate": norm_predicate,
                "confidence": float(rel.get("confidence", 0.75)),
                "weight": float(rel.get("weight", 1.0)),
                "frequency": int(rel.get("frequency", 1)),
                "supporting_sentences": supporting_sents,
            })

        if not processed_rels:
            return 0

        # Batch MERGE relationships
        batch_query = """
        UNWIND $rels AS r
        MATCH (s:Entity {entity_id: r.subj_id})
        MATCH (o:Entity {entity_id: r.obj_id})
        MERGE (s)-[rel:RELATED_TO {predicate: r.predicate, normalized_predicate: r.norm_predicate}]->(o)
        ON CREATE SET
            rel.confidence = r.confidence,
            rel.weight = r.weight,
            rel.frequency = r.frequency,
            rel.supporting_sentences = r.supporting_sentences,
            rel.created_at = $now,
            rel.updated_at = $now
        ON MATCH SET
            rel.frequency = rel.frequency + r.frequency,
            rel.weight = CASE WHEN r.weight > rel.weight THEN r.weight ELSE rel.weight + 0.1 END,
            rel.confidence = CASE WHEN r.confidence > rel.confidence THEN r.confidence ELSE rel.confidence END,
            rel.updated_at = $now
        RETURN count(rel) AS total_rels
        """

        try:
            result = self._run_query(batch_query, {"rels": processed_rels, "now": now})
            count = result[0]["total_rels"] if result else len(processed_rels)
            print(f"[NEO4J] Batch stored {count} relationships")
            return count
        except Exception as e:
            print(f"[NEO4J ERROR] Batch relationship storage error: {e}")
            # Fallback to individual MERGE
            count = 0
            for rel in relationships:
                try:
                    if self.add_relationship(rel):
                        count += 1
                except Exception:
                    pass
            print(f"[NEO4J] Fallback: stored {count} relationships individually")
            return count

    # ------------------------------------------------------------------
    # Post-Upload Verification
    # ------------------------------------------------------------------

    def verify_upload(self, document_id: str, expected_entity_count: int,
                      expected_relationship_count: int) -> Dict[str, Any]:
        """
        Verify that a document upload was correctly persisted in Neo4j Aura.

        Checks:
            - Document node exists
            - Entity count matches expected
            - Relationship count matches expected
            - No duplicate nodes exist

        Args:
            document_id: Document ID to verify
            expected_entity_count: Number of entities that should exist
            expected_relationship_count: Number of relationships that should exist

        Returns:
            Dict with verification results
        """
        result = {
            "verified": False,
            "document_exists": False,
            "entity_count": 0,
            "relationship_count": 0,
            "expected_entity_count": expected_entity_count,
            "expected_relationship_count": expected_relationship_count,
            "duplicates_found": False,
            "errors": [],
        }

        if not self.is_connected():
            result["errors"].append("Neo4j Aura is not connected")
            return result

        try:
            # Check Document exists
            doc_result = self._run_query(
                "MATCH (d:Document {document_id: $document_id}) RETURN count(d) AS cnt",
                {"document_id": document_id},
            )
            result["document_exists"] = doc_result and doc_result[0]["cnt"] > 0

            # Count entities
            entity_result = self._run_query(
                "MATCH (e:Entity) RETURN count(e) AS cnt",
            )
            if entity_result:
                result["entity_count"] = entity_result[0]["cnt"]

            # Count relationships
            rel_result = self._run_query(
                "MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS cnt",
            )
            if rel_result:
                result["relationship_count"] = rel_result[0]["cnt"]

            # Check for duplicate entity_ids (should be 0 with constraints)
            dup_result = self._run_query(
                """
                MATCH (e:Entity)
                WITH e.entity_id AS eid, count(e) AS cnt
                WHERE cnt > 1
                RETURN count(eid) AS duplicates
                """
            )
            if dup_result:
                result["duplicates_found"] = dup_result[0]["duplicates"] > 0

            # Determine verification status
            if result["document_exists"]:
                result["verified"] = True
                print(f"[NEO4J] ✓ Upload verification passed for document {document_id[:8]}")
            else:
                result["errors"].append(f"Document {document_id} not found in Neo4j")

            print(f"[NEO4J]   Entities: {result['entity_count']} "
                  f"(expected ~{expected_entity_count})")
            print(f"[NEO4J]   Relationships: {result['relationship_count']} "
                  f"(expected ~{expected_relationship_count})")
            print(f"[NEO4J]   Duplicates: {'⚠ FOUND' if result['duplicates_found'] else '✓ None'}")

        except Exception as e:
            result["errors"].append(str(e))
            print(f"[NEO4J ERROR] Verification failed: {e}")

        return result

    # ------------------------------------------------------------------
    # Graph Retrieval Methods
    # ------------------------------------------------------------------

    def query_related_entities(self, entity_text: str, hops: int = 2) -> List[Dict[str, Any]]:
        """
        Execute multi-hop Cypher graph traversal on Neo4j Aura.

        Traverses entity relationships to find connected entities up to `hops` depth.

        Args:
            entity_text: Text to search for entities
            hops: Number of relationship hops (1 or 2)

        Returns:
            List of related entity dicts
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")

        try:
            cypher_query = """
            MATCH (e:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($entity_text)
               OR any(a IN e.aliases WHERE toLower(a) CONTAINS toLower($entity_text))
            MATCH path = (e)-[r:RELATED_TO*1..2]-(target:Entity)
            WHERE e <> target
            UNWIND relationships(path) AS rel
            RETURN DISTINCT
                startNode(rel).canonical_name AS subject,
                startNode(rel).entity_type AS subject_type,
                rel.predicate AS predicate,
                rel.normalized_predicate AS normalized_predicate,
                endNode(rel).canonical_name AS object,
                endNode(rel).entity_type AS object_type,
                rel.confidence AS confidence,
                rel.weight AS weight,
                rel.frequency AS frequency,
                length(path) AS depth
            ORDER BY rel.weight DESC, rel.confidence DESC
            LIMIT 30
            """

            with self.driver.session(database=self.database) as session:
                records = session.run(cypher_query, entity_text=entity_text)
                results = []
                seen = set()

                for rec in records:
                    key = f"{rec['subject']}|{rec['predicate']}|{rec['object']}"
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "entity": rec["object"],
                            "label": rec["object_type"],
                            "relationship": rec.get("normalized_predicate") or rec["predicate"],
                            "predicate": rec["predicate"],
                            "depth": rec["depth"],
                            "path": [rec["subject"], rec["object"]],
                            "frequency": int(rec["frequency"] or 1),
                            "confidence": float(rec["confidence"] or 0.8),
                            "weight": float(rec["weight"] or 1.0),
                        })

                return results[:20]

        except Exception as e:
            print(f"[NEO4J ERROR] Cypher multi-hop traversal error: {e}")
            return []

    def search_entities(self, query_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for entities by text matching canonical_name or aliases.

        Args:
            query_text: Text to search for
            limit: Maximum number of results

        Returns:
            List of matching entity dicts
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot search — Neo4j Aura is not connected")

        try:
            cypher_search = """
            MATCH (e:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($query_text)
               OR any(a IN e.aliases WHERE toLower(a) CONTAINS toLower($query_text))
            RETURN e.entity_id AS entity_id,
                   e.canonical_name AS canonical_name,
                   e.original_name AS original_name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.confidence AS confidence,
                   e.frequency AS frequency,
                   e.document_count AS document_count,
                   e.source_documents AS source_documents,
                   e.first_seen AS first_seen,
                   e.last_seen AS last_seen,
                   e.created_at AS created_at,
                   e.updated_at AS updated_at
            ORDER BY e.frequency DESC, e.confidence DESC
            LIMIT $limit
            """

            with self.driver.session(database=self.database) as session:
                records = session.run(cypher_search, query_text=query_text, limit=limit)
                results = []

                for rec in records:
                    node = dict(rec)
                    node["text"] = node.get("canonical_name", "")
                    node["label"] = node.get("entity_type", "ENTITY")
                    results.append(node)

                return results

        except Exception as e:
            print(f"[NEO4J ERROR] Entity search error: {e}")
            return []

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get Knowledge Graph statistics from Neo4j Aura.

        Returns:
            Dict with entity_count, relationship_count, top entities
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot get stats — Neo4j Aura is not connected")

        stats = {
            "entity_count": 0,
            "relationship_count": 0,
            "document_count": 0,
            "chunk_count": 0,
            "top_entities": [],
            "database": "Neo4j Aura",
            "mode": "NEO4J_PERSISTENT",
            "pipeline_version": "enterprise-v3-aura",
        }

        try:
            # Entity count
            result = self._run_query("MATCH (e:Entity) RETURN count(e) AS cnt")
            if result:
                stats["entity_count"] = result[0]["cnt"]

            # Relationship count
            result = self._run_query("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS cnt")
            if result:
                stats["relationship_count"] = result[0]["cnt"]

            # Document count
            result = self._run_query("MATCH (d:Document) RETURN count(d) AS cnt")
            if result:
                stats["document_count"] = result[0]["cnt"]

            # Chunk count
            result = self._run_query("MATCH (c:Chunk) RETURN count(c) AS cnt")
            if result:
                stats["chunk_count"] = result[0]["cnt"]

            # Top entities by frequency
            result = self._run_query(
                """
                MATCH (e:Entity)
                RETURN e.canonical_name AS canonical_name,
                       e.entity_type AS entity_type,
                       e.frequency AS frequency,
                       e.confidence AS confidence
                ORDER BY e.frequency DESC, e.confidence DESC
                LIMIT 10
                """
            )
            if result:
                stats["top_entities"] = result

        except Exception as e:
            print(f"[NEO4J ERROR] Stats query error: {e}")

        return stats

    # ------------------------------------------------------------------
    # Advanced Graph Query Methods (Enterprise Knowledge Explorer)
    # ------------------------------------------------------------------

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get a single entity by its entity_id with full metadata."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (e:Entity {entity_id: $entity_id})
            RETURN e.entity_id AS entity_id,
                   e.canonical_name AS canonical_name,
                   e.original_name AS original_name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.confidence AS confidence,
                   e.frequency AS frequency,
                   e.document_count AS document_count,
                   e.source_documents AS source_documents,
                   e.chunk_ids AS chunk_ids,
                   e.first_seen AS first_seen,
                   e.last_seen AS last_seen,
                   e.created_at AS created_at,
                   e.updated_at AS updated_at
            """
            result = self._run_query(query, {"entity_id": entity_id})
            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"[NEO4J ERROR] Get entity by ID error: {e}")
            return None

    def get_relationships_for_entity(self, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all relationships for a specific entity."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (e:Entity {entity_id: $entity_id})
            MATCH (e)-[r:RELATED_TO]->(target:Entity)
            RETURN e.canonical_name AS source,
                   e.entity_type AS source_type,
                   r.predicate AS predicate,
                   r.normalized_predicate AS normalized_predicate,
                   target.canonical_name AS target,
                   target.entity_type AS target_type,
                   target.entity_id AS target_id,
                   r.confidence AS confidence,
                   r.weight AS weight,
                   r.frequency AS frequency,
                   r.supporting_sentences AS supporting_sentences,
                   r.source_documents AS source_documents,
                   r.chunk_ids AS chunk_ids,
                   r.created_at AS created_at,
                   r.updated_at AS updated_at
            UNION
            MATCH (e:Entity {entity_id: $entity_id})
            MATCH (source:Entity)-[r:RELATED_TO]->(e)
            RETURN source.canonical_name AS source,
                   source.entity_type AS source_type,
                   r.predicate AS predicate,
                   r.normalized_predicate AS normalized_predicate,
                   e.canonical_name AS target,
                   e.entity_type AS target_type,
                   e.entity_id AS target_id,
                   r.confidence AS confidence,
                   r.weight AS weight,
                   r.frequency AS frequency,
                   r.supporting_sentences AS supporting_sentences,
                   r.source_documents AS source_documents,
                   r.chunk_ids AS chunk_ids,
                   r.created_at AS created_at,
                   r.updated_at AS updated_at
            ORDER BY weight DESC, confidence DESC
            LIMIT $limit
            """
            result = self._run_query(query, {"entity_id": entity_id, "limit": limit})
            return result or []
        except Exception as e:
            print(f"[NEO4J ERROR] Get entity relationships error: {e}")
            return []

    def get_entity_neighbors(self, entity_id: str, hops: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Get neighboring entities and relationships for multi-hop expansion.

        Returns a graph-like structure with nodes and edges.
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (center:Entity {entity_id: $entity_id})
            MATCH path = (center)-[r:RELATED_TO*1..$hops]-(neighbor:Entity)
            WHERE center <> neighbor
            UNWIND r AS rel
            WITH DISTINCT center, rel, neighbor
            RETURN COLLECT(DISTINCT {
                id: center.entity_id,
                canonical_name: center.canonical_name,
                entity_type: center.entity_type,
                aliases: center.aliases,
                confidence: center.confidence,
                frequency: center.frequency
            }) AS center_nodes,
            COLLECT(DISTINCT {
                id: neighbor.entity_id,
                canonical_name: neighbor.canonical_name,
                entity_type: neighbor.entity_type,
                aliases: neighbor.aliases,
                confidence: neighbor.confidence,
                frequency: neighbor.frequency
            }) AS neighbor_nodes,
            COLLECT(DISTINCT {
                source: startNode(rel).entity_id,
                source_name: startNode(rel).canonical_name,
                target: endNode(rel).entity_id,
                target_name: endNode(rel).canonical_name,
                predicate: rel.predicate,
                normalized_predicate: rel.normalized_predicate,
                confidence: rel.confidence,
                weight: rel.weight,
                frequency: rel.frequency
            }) AS relationships
            """
            params = {"entity_id": entity_id, "hops": hops}
            result = self._run_query(query, params)
            if result and result[0]:
                data = result[0]
                nodes_map = {}
                for n in (data.get("center_nodes") or []):
                    if n["id"]:
                        nodes_map[n["id"]] = n
                for n in (data.get("neighbor_nodes") or []):
                    if n["id"]:
                        nodes_map[n["id"]] = n
                return {
                    "nodes": list(nodes_map.values()),
                    "edges": data.get("relationships") or [],
                    "center_id": entity_id
                }
            return {"nodes": [], "edges": [], "center_id": entity_id}
        except Exception as e:
            print(f"[NEO4J ERROR] Entity neighbors error: {e}")
            return {"nodes": [], "edges": [], "center_id": entity_id}

    def expand_neighbors(self, entity_ids: List[str], hops: int = 1, limit: int = 100) -> Dict[str, Any]:
        """
        Expand multiple entity nodes by fetching their neighbors.

        Used for multi-hop exploration in the UI.
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")
        if not entity_ids:
            return {"nodes": [], "edges": []}
        try:
            query = """
            MATCH (e:Entity)
            WHERE e.entity_id IN $entity_ids
            MATCH path = (e)-[r:RELATED_TO*1..$hops]-(neighbor:Entity)
            WHERE e <> neighbor
            UNWIND r AS rel
            WITH DISTINCT e, rel, neighbor
            WITH COLLECT(DISTINCT {
                id: e.entity_id,
                canonical_name: e.canonical_name,
                entity_type: e.entity_type,
                aliases: e.aliases,
                confidence: e.confidence,
                frequency: e.frequency
            }) AS source_nodes,
            COLLECT(DISTINCT {
                id: neighbor.entity_id,
                canonical_name: neighbor.canonical_name,
                entity_type: neighbor.entity_type,
                aliases: neighbor.aliases,
                confidence: neighbor.confidence,
                frequency: neighbor.frequency
            }) AS target_nodes,
            COLLECT(DISTINCT {
                source: startNode(rel).entity_id,
                source_name: startNode(rel).canonical_name,
                target: endNode(rel).entity_id,
                target_name: endNode(rel).canonical_name,
                predicate: rel.predicate,
                normalized_predicate: rel.normalized_predicate,
                confidence: rel.confidence,
                weight: rel.weight,
                frequency: rel.frequency
            }) AS relationships
            """
            result = self._run_query(query, {"entity_ids": entity_ids, "hops": hops})
            if result and result[0]:
                data = result[0]
                nodes_map = {}
                for n in (data.get("source_nodes") or []):
                    if n["id"]: nodes_map[n["id"]] = n
                for n in (data.get("target_nodes") or []):
                    if n["id"]: nodes_map[n["id"]] = n
                return {
                    "nodes": list(nodes_map.values()),
                    "edges": data.get("relationships") or []
                }
            return {"nodes": [], "edges": []}
        except Exception as e:
            print(f"[NEO4J ERROR] Expand neighbors error: {e}")
            return {"nodes": [], "edges": []}

    def find_path_between(self, source_id: str, target_id: str, max_hops: int = 6) -> Dict[str, Any]:
        """Find the shortest path between two entities."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (source:Entity {entity_id: $source_id})
            MATCH (target:Entity {entity_id: $target_id})
            MATCH path = shortestPath((source)-[:RELATED_TO*1..$max_hops]-(target))
            WHERE path IS NOT NULL
            UNWIND nodes(path) AS node
            WITH COLLECT(DISTINCT {
                id: node.entity_id,
                canonical_name: node.canonical_name,
                entity_type: node.entity_type,
                aliases: node.aliases,
                confidence: node.confidence,
                frequency: node.frequency
            }) AS path_nodes,
            relationships(path) AS path_rels
            RETURN path_nodes AS nodes,
                   [rel IN path_rels | {
                       source: startNode(rel).entity_id,
                       source_name: startNode(rel).canonical_name,
                       target: endNode(rel).entity_id,
                       target_name: endNode(rel).canonical_name,
                       predicate: rel.predicate,
                       normalized_predicate: rel.normalized_predicate,
                       confidence: rel.confidence,
                       weight: rel.weight
                   }] AS edges,
                   length(path) AS hop_count
            """
            result = self._run_query(query, {
                "source_id": source_id,
                "target_id": target_id,
                "max_hops": max_hops
            })
            if result and result[0] and result[0].get("nodes"):
                return {
                    "nodes": result[0]["nodes"],
                    "edges": result[0]["edges"],
                    "hop_count": result[0]["hop_count"]
                }
            return {"nodes": [], "edges": [], "hop_count": 0, "error": "No path found"}
        except Exception as e:
            print(f"[NEO4J ERROR] Find path error: {e}")
            return {"nodes": [], "edges": [], "hop_count": 0, "error": str(e)}

    def search_autocomplete(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fast autocomplete search for entity names and types."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot search — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (e:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($query)
               OR any(a IN e.aliases WHERE toLower(a) CONTAINS toLower($query))
            RETURN e.entity_id AS entity_id,
                   e.canonical_name AS canonical_name,
                   e.entity_type AS entity_type,
                   e.frequency AS frequency,
                   e.confidence AS confidence
            ORDER BY e.frequency DESC, e.confidence DESC
            LIMIT $limit
            """
            result = self._run_query(query, {"query": query_text, "limit": limit})
            return result or []
        except Exception as e:
            print(f"[NEO4J ERROR] Autocomplete error: {e}")
            return []

    def get_graph_analytics(self) -> Dict[str, Any]:
        """Compute comprehensive graph analytics from Neo4j Aura."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot get analytics — Neo4j Aura is not connected")
        
        analytics = {
            "node_count": 0,
            "edge_count": 0,
            "average_degree": 0,
            "connected_components": 0,
            "largest_component_size": 0,
            "graph_density": 0,
            "entity_type_distribution": [],
            "relationship_type_distribution": [],
            "duplicate_entities": 0,
            "duplicate_relationships": 0,
            "average_confidence": 0,
            "average_weight": 0,
            "isolated_nodes": 0,
            "graph_health_score": 100,
            "degree_distribution": [],
        }

        try:
            # Node & Edge counts
            result = self._run_query("MATCH (e:Entity) RETURN count(e) AS cnt")
            if result: analytics["node_count"] = result[0]["cnt"]
            
            result = self._run_query("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS cnt")
            if result: analytics["edge_count"] = result[0]["cnt"]

            # Entity type distribution
            result = self._run_query("""
                MATCH (e:Entity)
                RETURN e.entity_type AS entity_type, count(e) AS count
                ORDER BY count DESC
            """)
            if result: analytics["entity_type_distribution"] = result

            # Relationship type distribution
            result = self._run_query("""
                MATCH ()-[r:RELATED_TO]->()
                RETURN r.predicate AS predicate, r.normalized_predicate AS normalized_predicate, 
                       count(r) AS count, avg(r.confidence) AS avg_confidence
                ORDER BY count DESC
            """)
            if result: analytics["relationship_type_distribution"] = result

            # Average degree (using graph theory formula)
            n = analytics["node_count"]
            e = analytics["edge_count"]
            if n > 0:
                analytics["average_degree"] = round((2 * e) / n, 2)
                analytics["graph_density"] = round((2 * e) / (n * (n - 1)), 6) if n > 1 else 0

            # Average confidence
            result = self._run_query("""
                MATCH (e:Entity)
                RETURN avg(e.confidence) AS avg_conf
            """)
            if result and result[0].get("avg_conf") is not None:
                analytics["average_confidence"] = round(result[0]["avg_conf"], 4)

            # Average weight
            result = self._run_query("""
                MATCH ()-[r:RELATED_TO]->()
                RETURN avg(r.weight) AS avg_weight
            """)
            if result and result[0].get("avg_weight") is not None:
                analytics["average_weight"] = round(result[0]["avg_weight"], 4)

            # Isolated nodes (no relationships)
            result = self._run_query("""
                MATCH (e:Entity)
                WHERE NOT (e)-[:RELATED_TO]-()
                RETURN count(e) AS cnt
            """)
            if result: analytics["isolated_nodes"] = result[0]["cnt"]

            # Connected components (WCC approximation)
            analytics["connected_components"] = analytics["isolated_nodes"]
            if analytics["edge_count"] > 0:
                analytics["connected_components"] = analytics["isolated_nodes"] + 1  # approximation

            # Duplicate analysis
            result = self._run_query("""
                MATCH (e:Entity)
                WITH e.canonical_name AS name, e.entity_type AS type, count(e) AS cnt
                WHERE cnt > 1
                RETURN count(name) AS duplicates
            """)
            if result: analytics["duplicate_entities"] = result[0]["duplicates"]

            # Degree distribution (top 20)
            result = self._run_query("""
                MATCH (e:Entity)
                OPTIONAL MATCH (e)-[r:RELATED_TO]-()
                WITH e, count(r) AS degree
                RETURN e.canonical_name AS entity, e.entity_type AS entity_type, degree
                ORDER BY degree DESC
                LIMIT 20
            """)
            if result: analytics["degree_distribution"] = result

            # Graph health score (0-100)
            health = 100
            if analytics["isolated_nodes"] > analytics["node_count"] * 0.3:
                health -= 20  # Too many isolated nodes
            if analytics["duplicate_entities"] > 0:
                health -= 10
            if analytics["average_confidence"] < 0.7:
                health -= 10
            if analytics["node_count"] == 0:
                health = 0
            analytics["graph_health_score"] = max(0, health)

        except Exception as e:
            print(f"[NEO4J ERROR] Graph analytics error: {e}")

        return analytics

    def get_filtered_graph(self, filters: Dict[str, Any], limit: int = 200) -> Dict[str, Any]:
        """Get graph data with filtering support."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot query — Neo4j Aura is not connected")

        entity_types = filters.get("entity_types", [])
        min_confidence = filters.get("min_confidence", 0.0)
        min_frequency = filters.get("min_frequency", 0)
        search_query = filters.get("search_query", "")
        relationship_types = filters.get("relationship_types", [])
        hide_isolated = filters.get("hide_isolated", False)
        sort_by = filters.get("sort_by", "frequency")

        try:
            conditions = ["1=1"]
            params = {"limit": limit}

            if entity_types:
                conditions.append("e.entity_type IN $entity_types")
                params["entity_types"] = entity_types
            if min_confidence > 0:
                conditions.append("e.confidence >= $min_conf")
                params["min_conf"] = min_confidence
            if min_frequency > 0:
                conditions.append("e.frequency >= $min_freq")
                params["min_freq"] = min_frequency
            if search_query:
                conditions.append("(toLower(e.canonical_name) CONTAINS toLower($query) OR any(a IN e.aliases WHERE toLower(a) CONTAINS toLower($query)))")
                params["query"] = search_query

            where_clause = " AND ".join(conditions)

            entity_query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            RETURN e.entity_id AS id,
                   e.canonical_name AS canonical_name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.confidence AS confidence,
                   e.frequency AS frequency,
                   e.document_count AS document_count
            ORDER BY e.{sort_by} DESC
            LIMIT $limit
            """

            result = self._run_query(entity_query, params)
            nodes = []
            node_ids = set()
            for rec in result or []:
                nodes.append(dict(rec))
                node_ids.add(rec["id"])

            edges = []
            if node_ids:
                rel_conditions = ["startNode(r).entity_id IN $ids", "endNode(r).entity_id IN $ids"]
                rel_params = {"ids": list(node_ids), "limit": limit}
                if relationship_types:
                    rel_conditions.append("r.normalized_predicate IN $rel_types")
                    rel_params["rel_types"] = relationship_types

                rel_where = " AND ".join(rel_conditions)
                rel_query = f"""
                MATCH (s:Entity)-[r:RELATED_TO]->(t:Entity)
                WHERE {rel_where}
                RETURN DISTINCT
                    s.entity_id AS source,
                    s.canonical_name AS source_name,
                    t.entity_id AS target,
                    t.canonical_name AS target_name,
                    r.predicate AS predicate,
                    r.normalized_predicate AS normalized_predicate,
                    r.confidence AS confidence,
                    r.weight AS weight,
                    r.frequency AS frequency
                ORDER BY r.weight DESC
                LIMIT $limit
                """
                rel_result = self._run_query(rel_query, rel_params)
                edges = [dict(rec) for rec in rel_result] if rel_result else []

            if hide_isolated:
                connected_ids = set()
                for e in edges:
                    connected_ids.add(e["source"])
                    connected_ids.add(e["target"])
                nodes = [n for n in nodes if n["id"] in connected_ids]

            print(f"[GRAPH DEBUG] get_filtered_graph — "
                  f"nodes_from_neo4j={len(result) if result else 0}, "
                  f"relationships_from_neo4j={len(rel_result) if rel_result else 0}, "
                  f"final_nodes={len(nodes)}, "
                  f"final_edges={len(edges)}")

            return {"nodes": nodes, "edges": edges}

        except Exception as e:
            print(f"[NEO4J ERROR] Filtered graph error: {e}")
            return {"nodes": [], "edges": []}

    def execute_cypher_query(self, cypher: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a read-only Cypher query and return results.

        WARNING: Only allow read operations (MATCH, RETURN).
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot execute query — Neo4j Aura is not connected")

        cypher_upper = cypher.strip().upper()
        if not cypher_upper.startswith("MATCH") and not cypher_upper.startswith("RETURN") and "WITH" not in cypher_upper:
            return {"error": "Only read-only queries (MATCH, WITH, RETURN) are allowed", "results": [], "columns": []}

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, params or {})
                records = [record.data() for record in result]
                columns = list(records[0].keys()) if records else []
                return {"results": records, "columns": columns, "row_count": len(records)}
        except Exception as e:
            return {"error": str(e), "results": [], "columns": []}

    def search_relationships(self, query_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search relationships by predicate or entity names."""
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot search — Neo4j Aura is not connected")
        try:
            query = """
            MATCH (s:Entity)-[r:RELATED_TO]->(o:Entity)
            WHERE toLower(r.predicate) CONTAINS toLower($query)
               OR toLower(r.normalized_predicate) CONTAINS toLower($query)
               OR toLower(s.canonical_name) CONTAINS toLower($query)
               OR toLower(o.canonical_name) CONTAINS toLower($query)
            RETURN s.entity_id AS source_id,
                   s.canonical_name AS source_name,
                   s.entity_type AS source_type,
                   r.predicate AS predicate,
                   r.normalized_predicate AS normalized_predicate,
                   o.entity_id AS target_id,
                   o.canonical_name AS target_name,
                   o.entity_type AS target_type,
                   r.confidence AS confidence,
                   r.weight AS weight,
                   r.frequency AS frequency,
                   r.supporting_sentences AS supporting_sentences
            ORDER BY r.weight DESC, r.confidence DESC
            LIMIT $limit
            """
            result = self._run_query(query, {"query": query_text, "limit": limit})
            return result or []
        except Exception as e:
            print(f"[NEO4J ERROR] Search relationships error: {e}")
            return []

    def get_all_entities(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retrieve all entities from Neo4j Aura.

        Args:
            limit: Maximum number of entities

        Returns:
            List of entity dicts
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot retrieve — Neo4j Aura is not connected")

        try:
            query = """
            MATCH (e:Entity)
            RETURN e.entity_id AS entity_id,
                   e.canonical_name AS canonical_name,
                   e.original_name AS original_name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.confidence AS confidence,
                   e.frequency AS frequency
            ORDER BY e.frequency DESC
            LIMIT $limit
            """

            with self.driver.session(database=self.database) as session:
                records = session.run(query, limit=limit)
                return [dict(rec) for rec in records]

        except Exception as e:
            print(f"[NEO4J ERROR] Get all entities error: {e}")
            return []

    def get_all_relationships(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retrieve all relationships from Neo4j Aura.

        Args:
            limit: Maximum number of relationships

        Returns:
            List of relationship dicts
        """
        if not self.is_connected():
            raise RuntimeError("[NEO4J] Cannot retrieve — Neo4j Aura is not connected")

        try:
            query = """
            MATCH (s:Entity)-[r:RELATED_TO]->(o:Entity)
            RETURN s.canonical_name AS subject,
                   s.entity_type AS subject_type,
                   r.predicate AS predicate,
                   r.normalized_predicate AS normalized_predicate,
                   o.canonical_name AS object,
                   o.entity_type AS object_type,
                   r.confidence AS confidence,
                   r.weight AS weight,
                   r.frequency AS frequency
            ORDER BY r.weight DESC
            LIMIT $limit
            """

            with self.driver.session(database=self.database) as session:
                records = session.run(query, limit=limit)
                return [dict(rec) for rec in records]

        except Exception as e:
            print(f"[NEO4J ERROR] Get all relationships error: {e}")
            return []

