import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip, Divider, alpha, useTheme, CircularProgress, Grid, Paper } from '@mui/material';
import { motion } from 'framer-motion';
import AlertCircleIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import BubbleChartIcon from '@mui/icons-material/BubbleChart';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { getEntityColor } from './GraphCanvas';

const API_BASE = 'http://localhost:5000';

const CHART_COLORS = ['#0EA5E9', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#F97316', '#06B6D4', '#EF4444', '#14B8A6', '#6366F1'];

const StatCard = ({ label, value, color, icon }) => (
  <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(color || '#0EA5E9', 0.04), border: `1px solid ${alpha(color || '#0EA5E9', 0.12)}` }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
      {icon}
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, fontSize: 10 }}>{label}</Typography>
    </Box>
    <Typography variant="body1" sx={{ fontWeight: 700, fontSize: 18, color }}>{value ?? '-'}</Typography>
  </Box>
);

const BottomAnalytics = ({ graphStats, traversalPath, onClose }) => {
  const theme = useTheme();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/graph/analytics`);
      if (resp.ok) {
        const data = await resp.json();
        setAnalytics(data);
      }
    } catch (e) { 
      console.error('Analytics error', e);
    } finally { 
      setLoading(false); 
    }
  };

  if (loading || !analytics) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress size={24} sx={{ color: theme.palette.info.main }} />
      </Box>
    );
  }

  const entityDist = (analytics.entity_type_distribution || []).slice(0, 8);
  const relDist = (analytics.relationship_type_distribution || []).slice(0, 8);
  const degreeDist = (analytics.degree_distribution || []).slice(0, 10);
  const healthScore = analytics.graph_health_score || 0;

  return (
    <Box sx={{ p: 2, bgcolor: 'background.paper', borderTop: `1px solid ${theme.palette.divider}` }}>
      {/* Graph Health */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <BubbleChartIcon sx={{ fontSize: 18, color: theme.palette.info.main }} />
          Graph Intelligence
        </Typography>
        <Chip
          icon={healthScore >= 70 ? <CheckCircleIcon sx={{ fontSize: 14 }} /> : <AlertCircleIcon sx={{ fontSize: 14 }} />}
          label={`Graph Health: ${healthScore}/100`}
          size="small"
          sx={{ fontWeight: 700, fontSize: 10, bgcolor: alpha(healthScore >= 70 ? '#10B981' : '#F59E0B', 0.12), color: healthScore >= 70 ? '#10B981' : '#F59E0B', borderRadius: 1 }}
        />
      </Box>

      <Grid container spacing={2}>
        {/* Basic Stats */}
        <Grid item xs={12} md={3}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>GRAPH OVERVIEW</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
            <StatCard label="Nodes" value={analytics.node_count} color="#0EA5E9" icon={<AccountTreeIcon sx={{ fontSize: 14, color: '#0EA5E9' }} />} />
            <StatCard label="Edges" value={analytics.edge_count} color="#10B981" icon={<AccountTreeIcon sx={{ fontSize: 14, color: '#10B981' }} />} />
            <StatCard label="Avg Degree" value={analytics.average_degree} color="#8B5CF6" />
            <StatCard label="Density" value={analytics.graph_density?.toFixed(4)} color="#F59E0B" />
            <StatCard label="Components" value={analytics.connected_components} color="#EC4899" />
            <StatCard label="Isolated" value={analytics.isolated_nodes} color="#EF4444" />
            <StatCard label="Duplicates" value={analytics.duplicate_entities || 0} color="#F97316" />
            <StatCard label="Avg Confidence" value={`${((analytics.average_confidence || 0) * 100).toFixed(0)}%`} color="#14B8A6" />
          </Box>
        </Grid>

        {/* Entity Type Distribution */}
        <Grid item xs={12} md={3}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>ENTITY TYPE DISTRIBUTION</Typography>
          <Box sx={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={entityDist} cx="50%" cy="50%" innerRadius={30} outerRadius={65} paddingAngle={2} dataKey="count" nameKey="entity_type">
                  {entityDist.map((entry, i) => (
                    <Cell key={i} fill={getEntityColor(entry.entity_type) || CHART_COLORS[i % CHART_COLORS.length]} stroke="transparent" />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
            {entityDist.slice(0, 5).map((e, i) => (
              <Chip key={i} label={`${e.entity_type}: ${e.count}`} size="small" sx={{ fontSize: 9, height: 20, bgcolor: alpha(getEntityColor(e.entity_type), 0.1), color: getEntityColor(e.entity_type), fontWeight: 600 }} />
            ))}
          </Box>
        </Grid>

        {/* Relationship Distribution */}
        <Grid item xs={12} md={3}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>RELATIONSHIP TYPES</Typography>
          <Box sx={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={relDist} margin={{ top: 5, right: 5, left: -15, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.3)} vertical={false} />
                <XAxis dataKey="predicate" tick={{ fontSize: 8, fontWeight: 600 }} interval={0} angle={-20} textAnchor="end" height={40} />
                <YAxis tick={{ fontSize: 9 }} />
                <RechartsTooltip contentStyle={{ borderRadius: 8, fontSize: 11 }} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {relDist.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Grid>

        {/* Degree Distribution */}
        <Grid item xs={12} md={3}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>TOP DEGREE NODES</Typography>
          <Box sx={{ maxHeight: 230, overflowY: 'auto' }}>
            {degreeDist.map((d, i) => (
              <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5, px: 1, borderRadius: 1, '&:hover': { bgcolor: alpha(theme.palette.info.main, 0.04) } }}>
                <Typography variant="caption" sx={{ fontWeight: 700, fontSize: 10, color: 'text.secondary', minWidth: 18 }}>{i + 1}</Typography>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" sx={{ fontSize: 10, fontWeight: 600, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.entity}</Typography>
                  <Typography variant="caption" sx={{ fontSize: 9, color: 'text.secondary' }}>{d.entity_type}</Typography>
                </Box>
                <Chip label={d.degree} size="small" sx={{ fontSize: 9, height: 18, fontWeight: 700, bgcolor: alpha('#0EA5E9', 0.1), color: '#0EA5E9' }} />
              </Box>
            ))}
          </Box>
        </Grid>
      </Grid>

      {/* Traversal Explorer */}
      {traversalPath && traversalPath.length > 0 && (
        <Box sx={{ mt: 2, p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.info.main, 0.04), border: `1px solid ${alpha(theme.palette.info.main, 0.15)}` }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.info.main, display: 'block', mb: 0.5 }}>TRAVERSAL PATH</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
            {traversalPath.map((node, i) => (
              <React.Fragment key={i}>
                <Chip label={node.canonical_name || node.label || node.id} size="small" sx={{ fontSize: 10, fontWeight: 600, height: 22, bgcolor: alpha(getEntityColor(node.entity_type), 0.1), color: getEntityColor(node.entity_type) }} />
                {i < traversalPath.length - 1 && <Typography variant="caption" color="text.secondary">→</Typography>}
              </React.Fragment>
            ))}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            {traversalPath.length - 1} hops · {traversalPath.length} nodes visited
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default BottomAnalytics;