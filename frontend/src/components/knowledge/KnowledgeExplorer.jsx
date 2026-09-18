import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, IconButton, Tooltip, alpha, useTheme, useMediaQuery, Chip, CircularProgress, Alert, Drawer } from '@mui/material';
import GraphCanvas from './GraphCanvas';
import GraphToolbar from './GraphToolbar';
import LeftSidebar from './LeftSidebar';
import RightInspector from './RightInspector';
import BottomAnalytics from './BottomAnalytics';
import HubIcon from '@mui/icons-material/Hub';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SearchIcon from '@mui/icons-material/Search';
import InfoIcon from '@mui/icons-material/Info';
import TimelineIcon from '@mui/icons-material/Timeline';
import WarningIcon from '@mui/icons-material/Warning';
import StorageIcon from '@mui/icons-material/Storage';

const API_BASE = 'http://localhost:5000';

const KnowledgeExplorer = ({ darkMode }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isTablet = useMediaQuery(theme.breakpoints.down('lg'));

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [graphLoading, setGraphLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [layout, setLayout] = useState('Force Directed');
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showAnalytics, setShowAnalytics] = useState(true);
  const [expandedNodeIds, setExpandedNodeIds] = useState([]);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState([]);
  const [traversalPath, setTraversalPath] = useState([]);
  const [filters, setFilters] = useState({});
  const [searchResults, setSearchResults] = useState(null);
  const [storageMode, setStorageMode] = useState('neo4j');
  const [graphKey, setGraphKey] = useState(0);

  useEffect(() => {
    fetchStats();
    loadInitialGraph();
  }, []);

  const fetchStats = async () => {
    try {
      const resp = await fetch(`${API_BASE}/graph/stats`);
      if (resp.ok) {
        const data = await resp.json();
        setStats(data);
        setStorageMode(data.database ? 'neo4j' : 'memory');
      }
    } catch (e) { console.error('Stats error', e); }
  };

  const loadInitialGraph = async (filtersOverride) => {
    setGraphLoading(true);
    setError(null);
    try {
      const filterParams = filtersOverride || filters;
      const resp = await fetch(`${API_BASE}/api/graph/network`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: filterParams, limit: 200 })
      });
      if (resp.ok) {
        const data = await resp.json();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        if ((data.nodes || []).length === 0) {
          setError('No graph data found. Upload and process documents first.');
        } else {
          setError(null);
        }
      }
    } catch (e) {
      console.error('Graph load error', e);
      setError('Failed to load graph. Make sure the backend is running.');
    } finally {
      setGraphLoading(false);
      setLoading(false);
    }
  };

  const handleSearchResult = useCallback((results) => {
    setSearchResults(results);
    if (results && results.length > 0) {
      const searchNodes = results.map(r => ({
        id: r.entity_id || r.canonical_name || r.text,
        label: r.canonical_name || r.text,
        canonical_name: r.canonical_name || r.text,
        entity_type: r.entity_type || r.label || 'ENTITY',
        confidence: r.confidence || 0.8,
        frequency: r.frequency || 1,
        aliases: r.aliases || [],
        original_name: r.original_name || ''
      }));
      setNodes(searchNodes);
      setEdges([]);
      setHighlightedNodeIds(searchNodes.map(n => n.id));
    } else if (results === null) {
      loadInitialGraph();
      setHighlightedNodeIds([]);
    }
  }, []);

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    loadInitialGraph(newFilters);
  }, []);

  const handleNodeClick = useCallback((nodeData) => {
    if (!nodeData) { setSelectedNode(null); setSelectedEdge(null); return; }
    setSelectedNode(nodeData);
    setSelectedEdge(null);
  }, []);

  const handleEdgeClick = useCallback((edgeData) => {
    if (!edgeData) { setSelectedEdge(null); return; }
    setSelectedEdge(edgeData);
    setSelectedNode(null);
  }, []);

  const handleExpandNode = useCallback(async (nodeId, hops = 1) => {
    try {
      const resp = await fetch(`${API_BASE}/api/graph/expand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_ids: [nodeId], hops })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.nodes && data.nodes.length > 0) {
          const existingIds = new Set(nodes.map(n => n.id));
          const newNodes = data.nodes.filter(n => !existingIds.has(n.id));
          const existingEdgeKeys = new Set(edges.map(e => `${e.source}-${e.predicate}-${e.target}`));
          const newEdges = data.edges.filter(e => !existingEdgeKeys.has(`${e.source}-${e.predicate}-${e.target}`));
          setNodes(prev => [...prev, ...newNodes]);
          setEdges(prev => [...prev, ...newEdges]);
          setExpandedNodeIds(prev => [...new Set([...prev, nodeId, ...data.nodes.map(n => n.id)])]);
        }
      }
    } catch (e) { console.error('Expand error', e); }
  }, [nodes, edges]);

  const handleFindPath = useCallback(async (nodeId) => {
    if (!selectedNode && !nodeId) return;
    const sourceId = nodeId || selectedNode?.id;
    const targetId = selectedNode?.id;
    if (!sourceId || !targetId || sourceId === targetId) return;
    try {
      const resp = await fetch(`${API_BASE}/api/graph/path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: sourceId, target_id: targetId, max_hops: 6 })
      });
      if (resp.ok) { const data = await resp.json(); setTraversalPath(data.nodes || []); }
    } catch (e) { console.error('Path error', e); }
  }, [selectedNode]);

  const handleCloseInspector = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const handleGraphReady = useCallback((cy) => {
    window.__knowledgeCy = cy;
  }, []);

  const getGraphActions = () => ({
    zoomIn: () => { const c = window.__knowledgeCy; if (c) { c.zoom(c.zoom() * 1.3); } },
    zoomOut: () => { const c = window.__knowledgeCy; if (c) { c.zoom(c.zoom() / 1.3); } },
    fitScreen: () => { if (window.__knowledgeCy) { window.__knowledgeCy.fit(undefined, 50); } },
    centerGraph: () => { if (window.__knowledgeCy) { window.__knowledgeCy.center(); } },
    resetLayout: (l) => { setLayout(l); setGraphKey(k => k + 1); },
    toggleFullscreen: () => {
      const el = document.querySelector('[data-graph-container]');
      if (!el) return;
      if (!document.fullscreenElement) { el.requestFullscreen(); } else { document.exitFullscreen(); }
    },
    exportPng: () => {
      const canvas = document.querySelector('[data-graph-container] canvas');
      if (canvas) { const link = document.createElement('a'); link.download = 'knowledge-graph.png'; link.href = canvas.toDataURL(); link.click(); }
    },
    exportJson: () => {
      if (!window.__knowledgeCy) return;
      const json = window.__knowledgeCy.json();
      const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
      const link = document.createElement('a'); link.download = 'knowledge-graph.json'; link.href = URL.createObjectURL(blob); link.click();
    }
  });

  const ga = getGraphActions();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', flexDirection: 'column', gap: 2 }}>
        <CircularProgress size={48} thickness={4} sx={{ color: theme.palette.info.main }} />
        <Typography variant="body2" color="text.secondary">Initializing Knowledge Explorer...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 72px)', bgcolor: 'background.default', position: 'relative' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2.5, py: 1, borderBottom: '1px solid ' + theme.palette.divider, bgcolor: alpha(theme.palette.background.paper, 0.8), backdropFilter: 'blur(8px)', flexShrink: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <HubIcon sx={{ color: theme.palette.info.main, fontSize: 24 }} />
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: 18 }}>Enterprise Knowledge Explorer</Typography>
          <Chip size="small" icon={<StorageIcon sx={{ fontSize: 14 }} />} label={storageMode === 'neo4j' ? 'Neo4j Aura' : 'In-Memory'} color={storageMode === 'neo4j' ? 'success' : 'warning'} sx={{ height: 24, fontWeight: 600, fontSize: 10 }} />
          <Chip size="small" label={nodes.length + ' nodes / ' + edges.length + ' edges'} variant="outlined" sx={{ height: 24, fontWeight: 500, fontSize: 10 }} />
        </Box>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <Tooltip title="Toggle Left Panel"><IconButton size="small" onClick={() => setShowLeftPanel(!showLeftPanel)} color={showLeftPanel ? 'primary' : 'default'}><SearchIcon fontSize="small" /></IconButton></Tooltip>
          <Tooltip title="Toggle Right Panel"><IconButton size="small" onClick={() => setShowRightPanel(!showRightPanel)} color={showRightPanel ? 'primary' : 'default'}><InfoIcon fontSize="small" /></IconButton></Tooltip>
          <Tooltip title="Toggle Analytics"><IconButton size="small" onClick={() => setShowAnalytics(!showAnalytics)} color={showAnalytics ? 'primary' : 'default'}><TimelineIcon fontSize="small" /></IconButton></Tooltip>
          <Tooltip title="Refresh Graph"><IconButton size="small" onClick={() => loadInitialGraph()}><AutoAwesomeIcon fontSize="small" /></IconButton></Tooltip>
        </Box>
      </Box>

      {error && (
        <Alert severity="warning" onClose={() => setError(null)} icon={<WarningIcon sx={{ fontSize: 16 }} />} sx={{ borderRadius: 0, fontSize: 12 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {showLeftPanel && (
          <Box sx={{ width: 280, flexShrink: 0, display: { xs: 'none', md: 'block' }, borderRight: '1px solid ' + theme.palette.divider, overflowY: 'auto' }}>
            <LeftSidebar stats={stats} onSearchResult={handleSearchResult} onFilterChange={handleFilterChange} />
          </Box>
        )}

        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <GraphToolbar
            onZoomIn={ga.zoomIn}
            onZoomOut={ga.zoomOut}
            onFitScreen={ga.fitScreen}
            onCenterGraph={ga.centerGraph}
            onResetLayout={() => ga.resetLayout(layout)}
            onToggleFullscreen={ga.toggleFullscreen}
            onExportPng={ga.exportPng}
            onExportJson={ga.exportJson}
            layout={layout}
            onLayoutChange={(l) => { setLayout(l); setGraphKey(k => k + 1); }}
            showMinimap={true}
            onToggleMinimap={() => {}}
          />
          <Box sx={{ flex: 1, position: 'relative', minHeight: 0 }}>
            {graphLoading && (
              <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: alpha('#000', 0.2), zIndex: 10 }}>
                <CircularProgress size={32} sx={{ color: theme.palette.info.main }} />
              </Box>
            )}
            <GraphCanvas
              key={graphKey}
              nodes={nodes}
              edges={edges}
              onNodeClick={handleNodeClick}
              onEdgeClick={handleEdgeClick}
              onGraphReady={handleGraphReady}
              layout={layout}
              selectedNodeId={selectedNode ? selectedNode.id : null}
              highlightedNodeIds={highlightedNodeIds}
              expandedNodeIds={expandedNodeIds}
              traversalPathIds={traversalPath.map(function(n) { return n.id; })}
              loading={graphLoading}
            />
          </Box>
        </Box>

        {showRightPanel && (
          <Box sx={{ width: 300, flexShrink: 0, display: { xs: 'none', lg: 'block' }, borderLeft: '1px solid ' + theme.palette.divider, overflowY: 'auto' }}>
            <RightInspector
              selectedNode={selectedNode}
              selectedEdge={selectedEdge}
              onClose={handleCloseInspector}
              onExpandNode={function(id) { handleExpandNode(id, 1); }}
              onFindPath={handleFindPath}
            />
          </Box>
        )}
      </Box>

      {showAnalytics && (
        <Box sx={{ maxHeight: 300, overflow: 'auto', borderTop: '1px solid ' + theme.palette.divider, flexShrink: 0 }}>
          <BottomAnalytics graphStats={stats} traversalPath={traversalPath} />
        </Box>
      )}

      <Drawer anchor="left" open={showLeftPanel && isMobile} onClose={() => setShowLeftPanel(false)}>
        <Box sx={{ width: 280 }}><LeftSidebar stats={stats} onSearchResult={handleSearchResult} onFilterChange={handleFilterChange} /></Box>
      </Drawer>
      <Drawer anchor="right" open={showRightPanel && isTablet} onClose={() => setShowRightPanel(false)}>
        <Box sx={{ width: 300, height: '100%' }}>
          <RightInspector selectedNode={selectedNode} selectedEdge={selectedEdge} onClose={handleCloseInspector} onExpandNode={function(id) { handleExpandNode(id, 1); }} onFindPath={handleFindPath} />
        </Box>
      </Drawer>
    </Box>
  );
};

export default KnowledgeExplorer;
