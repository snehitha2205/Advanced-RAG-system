import React from 'react';
import { Box, Typography, Card, Grid, Chip, Divider, useTheme, alpha } from '@mui/material';
import { motion } from 'framer-motion';

// Icons
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import TimerRoundedIcon from '@mui/icons-material/TimerRounded';
import DataObjectRoundedIcon from '@mui/icons-material/DataObjectRounded';
import AnalyticsRoundedIcon from '@mui/icons-material/AnalyticsRounded';
import NetworkCheckRoundedIcon from '@mui/icons-material/NetworkCheckRounded';

const MetricsPanel = ({ metrics = {} }) => {
  const theme = useTheme();

  const docCount = metrics.documents_retrieved ?? 0;
  const chunkCount = metrics.chunks_retrieved ?? 0;
  const entityCount = metrics.graph_entities_used ?? 0;
  const relCount = metrics.relationships_traversed ?? 0;
  const graphHops = metrics.knowledge_graph_hops ?? 2;

  const rTime = metrics.retrieval_time_seconds ?? 0.0;
  const gTime = metrics.generation_time_seconds ?? 0.0;
  const cTime = metrics.critic_time_seconds ?? 0.0;
  const totalTime = metrics.total_response_time_seconds ?? 0.0;

  const promptTokens = metrics.prompt_tokens ?? 0;
  const completionTokens = metrics.completion_tokens ?? 0;
  const complexity = metrics.query_complexity ?? 'Medium';
  const retrievalQuality = Math.round((metrics.retrieval_quality_score ?? 0.88) * 100);

  const getComplexityColor = (c) => {
    if (c === 'Easy') return theme.palette.success.main;
    if (c === 'Medium') return theme.palette.info.main;
    return theme.palette.warning.main;
  };

  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      sx={{
        p: 2.5,
        mt: 2,
        borderRadius: 3,
        bgcolor: theme.palette.background.paper,
        border: `1px solid ${theme.palette.divider}`,
        boxShadow: 'none'
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
          <AnalyticsRoundedIcon sx={{ color: theme.palette.info.main, fontSize: 20 }} />
          Retrieval & GraphRAG Telemetry
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            label={`Complexity: ${complexity}`}
            size="small"
            sx={{ fontWeight: 700, bgcolor: alpha(getComplexityColor(complexity), 0.12), color: getComplexityColor(complexity) }}
          />
          <Chip
            icon={<NetworkCheckRoundedIcon sx={{ fontSize: 14 }} />}
            label={`Retrieval Quality: ${retrievalQuality}%`}
            size="small"
            sx={{ fontWeight: 700, bgcolor: alpha(theme.palette.success.main, 0.12), color: theme.palette.success.main }}
          />
        </Box>
      </Box>

      {/* Grid of Key Telemetry */}
      <Grid container spacing={2}>
        {/* Document Metrics */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.info.main, 0.05), border: `1px solid ${alpha(theme.palette.info.main, 0.15)}` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <DescriptionRoundedIcon sx={{ fontSize: 16, color: theme.palette.info.main }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary }}>Vector Corpus</Typography>
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>{docCount} <Typography component="span" variant="caption">Docs</Typography> / {chunkCount} <Typography component="span" variant="caption">Chunks</Typography></Typography>
          </Box>
        </Grid>

        {/* GraphRAG Metrics */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.success.main, 0.05), border: `1px solid ${alpha(theme.palette.success.main, 0.15)}` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <HubRoundedIcon sx={{ fontSize: 16, color: theme.palette.success.main }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary }}>Knowledge Graph</Typography>
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>{entityCount} <Typography component="span" variant="caption">Entities</Typography> / {relCount} <Typography component="span" variant="caption">Rels ({graphHops} Hops)</Typography></Typography>
          </Box>
        </Grid>

        {/* Latency Breakdown */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.warning.main, 0.05), border: `1px solid ${alpha(theme.palette.warning.main, 0.15)}` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <TimerRoundedIcon sx={{ fontSize: 16, color: theme.palette.warning.main }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary }}>Latency Breakdown</Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700, fontSize: 12 }}>
              Ret: {rTime}s | Gen: {gTime}s | Crit: {cTime}s
            </Typography>
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 700 }}>
              Total: {totalTime}s
            </Typography>
          </Box>
        </Grid>

        {/* Token Telemetry */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.primary.main, 0.05), border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <DataObjectRoundedIcon sx={{ fontSize: 16, color: theme.palette.primary.main }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary }}>Token Consumption</Typography>
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700, fontSize: 12 }}>
              Prompt: ~{promptTokens} tokens
            </Typography>
            <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 700 }}>
              Completion: ~{completionTokens} tokens
            </Typography>
          </Box>
        </Grid>
      </Grid>
    </Card>
  );
};

export default MetricsPanel;
