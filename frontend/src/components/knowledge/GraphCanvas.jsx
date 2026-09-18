import React, { useEffect, useRef, useState } from 'react';
import { Box, alpha, CircularProgress } from '@mui/material';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';

cytoscape.use(dagre);

// ─── Entity Type → Colour Mapping ──────────────────────────────────────
export const ENTITY_COLORS = {
  Technology: '#0EA5E9', Database: '#8B5CF6', Framework: '#F59E0B',
  Model: '#10B981', Concept: '#EC4899', Organization: '#6366F1',
  Metric: '#14B8A6', Algorithm: '#F97316', Tool: '#06B6D4',
  Dataset: '#A855F7', 'Research Topic': '#EF4444', Person: '#22D3EE',
  Location: '#34D399', Event: '#FB923C', Product: '#E879F9',
  SYSTEM: '#0EA5E9', MODEL: '#10B981', FRAMEWORK: '#F59E0B',
  DATABASE: '#8B5CF6', COMPONENT: '#6366F1', CONCEPT: '#EC4899',
  ORGANIZATION: '#6366F1', PERSON: '#22D3EE', GPE: '#F59E0B',
  LOC: '#34D399', ORG: '#6366F1', TECHNOLOGY: '#0EA5E9',
  ALGORITHM: '#F97316', TOOL: '#06B6D4', METHOD: '#A855F7',
  LANGUAGE: '#14B8A6', PROTOCOL: '#06B6D4', PLATFORM: '#0EA5E9',
  STANDARD: '#8B5CF6', ENTITY: '#6B7280', DEFAULT: '#6B7280'
};

export const getEntityColor = (type) => ENTITY_COLORS[type] || ENTITY_COLORS.DEFAULT;

export const getPredicateColor = (predicate) => {
  const PREDICATE_COLORS = {
    USES: '#0EA5E9', IMPLEMENTS: '#10B981', DEPENDS_ON: '#F59E0B',
    RELATED_TO: '#94A3B8', PART_OF: '#8B5CF6', CREATED_BY: '#EC4899',
    DEVELOPS: '#F97316', INTEGRATES: '#06B6D4', EXTENDS: '#A855F7',
    TRAINS: '#14B8A6', OPTIMIZES: '#EF4444', ANALYZES: '#6366F1',
    CONTAINS: '#10B981', LEADS_TO: '#F59E0B', CONTRIBUTES: '#0EA5E9',
    ENABLES: '#06B6D4', GENERATES: '#EC4899', REQUIRES: '#F97316'
  };
  if (!predicate) return '#94A3B8';
  const key = predicate.toUpperCase().replace(/\s+/g, '_');
  return PREDICATE_COLORS[key] || '#94A3B8';
};

// ─── Layout Options ────────────────────────────────────────────────────
export const LAYOUTS = {
  'Force Directed': { name: 'cose', animate: true, animationDuration: 500, gravity: 0.25, idealEdgeLength: 100, nodeRepulsion: 4000, nodeOverlap: 20 },
  Hierarchical: { name: 'dagre', animate: true, animationDuration: 500, rankDir: 'TB', spacingFactor: 1.5, nodeSep: 60, rankSep: 100 },
  Circular: { name: 'circle', animate: true, animationDuration: 500, spacingFactor: 1.5 },
  Concentric: { name: 'concentric', animate: true, animationDuration: 500, concentric: node => node.data('frequency') || 1, levelWidth: () => 2, minNodeSpacing: 60 },
  Grid: { name: 'grid', animate: true, animationDuration: 500, cols: undefined },
  Radial: { name: 'breadthfirst', animate: true, animationDuration: 500, directed: true, spacingFactor: 1.5 }
};

const GraphCanvas = ({ nodes = [], edges = [], onNodeClick, onEdgeClick, onGraphReady, layout = 'Force Directed', selectedNodeId, highlightedNodeIds = [], expandedNodeIds = [], traversalPathIds = [], loading = false }) => {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [graphReady, setGraphReady] = useState(false);

  // ─── Initialize Cytoscape ──────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      style: [
        { selector: 'node', style: { 'background-color': '#0EA5E9', label: 'data(label)', color: '#1e293b', 'font-size': '11px', 'font-weight': 600, 'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 8, width: 60, height: 40, 'border-width': 2, 'border-color': '#fff', 'border-opacity': 0.8, 'shadow-blur': 8, 'shadow-color': 'rgba(0,0,0,0.15)', 'shadow-opacity': 0.3, 'transition-property': 'background-color, border-color, width, height', 'transition-duration': 300 } },
        { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#0EA5E9', 'shadow-blur': 16, 'shadow-color': '#0EA5E9', 'shadow-opacity': 0.4 } },
        { selector: 'node.highlighted', style: { 'border-width': 3, 'border-color': '#F59E0B', 'shadow-blur': 12, 'shadow-color': '#F59E0B', 'shadow-opacity': 0.3 } },
        { selector: 'node.expanded', style: { 'border-width': 3, 'border-color': '#10B981' } },
        { selector: 'edge', style: { width: 2, 'line-color': '#94A3B8', 'target-arrow-color': '#94A3B8', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': '8px', color: '#64748B', 'text-rotation': 'autorotate', 'text-margin-x': 4, 'text-margin-y': -4, 'transition-property': 'width, line-color', 'transition-duration': 200 } },
        { selector: 'edge:selected', style: { width: 4, 'line-color': '#0EA5E9', 'target-arrow-color': '#0EA5E9' } },
        { selector: 'edge.highlighted', style: { width: 4, 'line-color': '#F59E0B', 'target-arrow-color': '#F59E0B' } }
      ],
      wheelSensitivity: 0.4,
      minZoom: 0.1,
      maxZoom: 5
    });
    cyRef.current = cy;
    setGraphReady(true);
    cy.on('tap', 'node', (evt) => { onNodeClick?.(evt.target.data()); });
    cy.on('tap', 'edge', (evt) => { onEdgeClick?.(evt.target.data()); });
    cy.on('tap', (evt) => { if (evt.target === cy) { onNodeClick?.(null); onEdgeClick?.(null); } });
    return () => { cy.destroy(); cyRef.current = null; };
  }, []);

  // ─── Update Graph Data ─────────────────────────────────────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().remove();
    if (nodes.length === 0) return;

    nodes.forEach(n => {
      const id = n.id || n.entity_id || n.canonical_name;
      if (!id) return;
      cy.add({ group: 'nodes', data: { id, label: n.canonical_name || n.label || id, entity_type: n.entity_type || 'ENTITY', frequency: n.frequency || 1, confidence: n.confidence || 0.8, aliases: n.aliases || [], original_name: n.original_name || '', first_seen: n.first_seen, last_seen: n.last_seen, created_at: n.created_at, updated_at: n.updated_at, degree: n.degree || 0 } });
    });

    edges.forEach(e => {
      const src = e.source || e.source_id;
      const tgt = e.target || e.target_id;
      if (!src || !tgt) return;
      cy.add({ group: 'edges', data: { id: `${src}-${e.predicate || 'rel'}-${tgt}`, source: src, target: tgt, label: e.normalized_predicate || e.predicate || 'RELATED_TO', predicate: e.predicate || e.normalized_predicate || 'RELATED_TO', weight: e.weight || 1, confidence: e.confidence || 0.5, supporting_sentences: e.supporting_sentences || [], source_documents: e.source_documents || [], source_name: e.source_name, target_name: e.target_name } });
    });

    cy.nodes().forEach(n => {
      const type = n.data('entity_type') || 'ENTITY';
      const freq = n.data('frequency') || 1;
      const color = getEntityColor(type);
      n.style({ 'background-color': color, width: Math.min(80, 30 + freq * 2), height: Math.min(80, 30 + freq * 2) });
    });

    cy.edges().forEach(e => {
      const w = e.data('weight') || 1;
      const pred = e.data('predicate') || '';
      const pColor = getPredicateColor(pred);
      e.style({ width: Math.min(6, Math.max(1, w * 2)), 'line-color': pColor, 'target-arrow-color': pColor });
    });

    const layoutOpts = LAYOUTS[layout] || LAYOUTS['Force Directed'];
    const ly = cy.layout(layoutOpts);
    ly.run();
    ly.one('layoutstop', () => { onGraphReady?.(cy); });
  }, [nodes, edges, layout]);

  // ─── Handle Selected / Highlighted / Expanded / Traversal ──────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedNodeId) { const n = cy.getElementById(selectedNodeId); if (n.length) n.select(); }
  }, [selectedNodeId]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('highlighted');
    highlightedNodeIds.forEach(id => cy.getElementById(id)?.addClass('highlighted'));
  }, [highlightedNodeIds]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('expanded');
    expandedNodeIds.forEach(id => cy.getElementById(id)?.addClass('expanded'));
  }, [expandedNodeIds]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('traversal');
    cy.edges().removeClass('traversal');
    traversalPathIds.forEach(id => cy.getElementById(id)?.addClass('traversal'));
  }, [traversalPathIds]);

  // ─── Expose global API ─────────────────────────────────────────────────
  useEffect(() => {
    if (graphReady && cyRef.current) {
      const cy = cyRef.current;
      window.__knowledgeCy = cy;
      window.__knowledgeGraph = {
        getCy: () => cy,
        fitToScreen: () => cy.fit(undefined, 50),
        zoomIn: () => cy.zoom(cy.zoom() * 1.3),
        zoomOut: () => cy.zoom(cy.zoom() / 1.3),
        centerGraph: () => cy.center(),
        resetLayout: (name) => { const opts = LAYOUTS[name] || LAYOUTS['Force Directed']; cy.layout(opts).run(); },
        exportPng: () => { const canvas = containerRef.current?.querySelector('canvas'); if (canvas) { const link = document.createElement('a'); link.download = 'knowledge-graph.png'; link.href = canvas.toDataURL(); link.click(); } },
        exportJson: () => { const json = cy.json(); const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.download = 'knowledge-graph.json'; link.href = URL.createObjectURL(blob); link.click(); }
      };
    }
  }, [graphReady]);

  return (
    <Box ref={containerRef} data-graph-container sx={{ width: '100%', height: '100%', position: 'relative', bgcolor: 'background.default', overflow: 'hidden' }}>
      {loading && (
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: alpha('#000', 0.3), zIndex: 10 }}>
          <CircularProgress size={40} sx={{ color: '#0EA5E9' }} />
        </Box>
      )}
    </Box>
  );
};

export default GraphCanvas;
