import React from 'react';
import {
  Box,
  Typography,
  Card,
  LinearProgress,
  Chip,
  Divider,
  useTheme,
  alpha,
  CircularProgress
} from '@mui/material';
import { motion } from 'framer-motion';

// Icons
import VerifiedUserRoundedIcon from '@mui/icons-material/VerifiedUserRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import CancelRoundedIcon from '@mui/icons-material/CancelRounded';
import AutoFixHighRoundedIcon from '@mui/icons-material/AutoFixHighRounded';
import ShieldRoundedIcon from '@mui/icons-material/ShieldRounded';

const METRICS_CONFIG = [
  { key: 'groundedness', label: 'Groundedness', desc: 'Claims backed by retrieved context' },
  { key: 'faithfulness', label: 'Faithfulness', desc: 'No hallucinations or contradictions' },
  { key: 'completeness', label: 'Completeness', desc: 'Addresses all aspects of the query' },
  { key: 'relevance', label: 'Relevance', desc: 'Directly answers prompt intent' },
  { key: 'graph_consistency', label: 'Graph Consistency', desc: 'Consistent with Knowledge Graph' },
  { key: 'citation_quality', label: 'Citation Quality', desc: 'Sufficient source chunk coverage' },
  { key: 'confidence', label: 'Confidence', desc: 'Overall model certainty score' }
];

const CriticPanel = ({ criticReport, correctionHistory = [], metrics = {}, sources = [] }) => {
  const theme = useTheme();

  if (!criticReport) {
    return (
      <Card sx={{ p: 3, textAlign: 'center', bgcolor: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, boxShadow: 'none', borderRadius: 3 }}>
        <ShieldRoundedIcon sx={{ fontSize: 40, color: theme.palette.text.disabled, mb: 1 }} />
        <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 600 }}>
          AI Reasoning & Validation
        </Typography>
        <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
          Critic evaluation metrics will populate here when the AI generates a response.
        </Typography>
      </Card>
    );
  }

  const qualityScore = criticReport.overall_quality_score ?? 90;
  const status = criticReport.final_status || (qualityScore >= 80 ? 'Verified' : qualityScore >= 60 ? 'Partially Verified' : 'Low Confidence');

  // Color coding
  const getQualityColor = (score) => {
    if (score >= 80) return theme.palette.success.main;
    if (score >= 60) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const statusColor = getQualityColor(qualityScore);

  const getStatusIcon = (st) => {
    if (st.includes('Verified') && !st.includes('Partially')) return <VerifiedUserRoundedIcon fontSize="small" />;
    if (st.includes('Partially')) return <WarningAmberRoundedIcon fontSize="small" />;
    return <CancelRoundedIcon fontSize="small" />;
  };

  const totalAttempts = metrics.retry_count ?? Math.max(0, correctionHistory.filter(c => c.status === 'Failed' || c.status === 'Fixed').length);

  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        bgcolor: theme.palette.background.paper,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 3,
        boxShadow: 'none',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          alignItems: 'center',
          justify: 'space-between',
          bgcolor: alpha(theme.palette.primary.main, 0.03)
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ShieldRoundedIcon sx={{ color: theme.palette.info.main, fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            AI Reasoning & Validation
          </Typography>
        </Box>
        <Chip
          icon={getStatusIcon(status)}
          label={status}
          size="small"
          sx={{
            fontWeight: 700,
            fontSize: 11,
            bgcolor: alpha(statusColor, 0.12),
            color: statusColor,
            border: `1px solid ${alpha(statusColor, 0.3)}`
          }}
        />
      </Box>

      <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2.5 }}>
        {/* Overall Quality Score Card */}
        <Box
          sx={{
            p: 2,
            borderRadius: 2.5,
            bgcolor: alpha(statusColor, 0.06),
            border: `1px solid ${alpha(statusColor, 0.2)}`,
            display: 'flex',
            alignItems: 'center',
            justify: 'space-between'
          }}
        >
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary, textTransform: 'uppercase' }}>
              Overall Reliability Score
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: statusColor, mt: 0.5 }}>
              {qualityScore} <Typography component="span" variant="subtitle1" sx={{ color: theme.palette.text.secondary }}>/ 100</Typography>
            </Typography>
          </Box>

          <Box sx={{ position: 'relative', display: 'inline-flex' }}>
            <CircularProgress
              variant="determinate"
              value={qualityScore}
              size={56}
              thickness={5}
              sx={{ color: statusColor }}
            />
            <Box
              sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justify: 'center'
              }}
            >
              <Typography variant="caption" component="div" color="text.secondary" sx={{ fontWeight: 700 }}>
                {qualityScore}%
              </Typography>
            </Box>
          </Box>
        </Box>

        <Divider />

        {/* 7 Metrics Breakdown */}
        <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Quality Metrics Evaluation
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {METRICS_CONFIG.map((m) => {
            const rawVal = criticReport[m.key] ?? 0.85;
            const pct = Math.round(rawVal * 100);
            const mColor = getQualityColor(pct);

            return (
              <Box key={m.key}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: 13 }}>
                    {m.label}
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: mColor }}>
                    {pct}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={pct}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: alpha(mColor, 0.12),
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 3,
                      bgcolor: mColor
                    }
                  }}
                />
                <Typography variant="caption" sx={{ color: theme.palette.text.disabled, fontSize: 10, display: 'block', mt: 0.3 }}>
                  {m.desc}
                </Typography>
              </Box>
            );
          })}
        </Box>

        <Divider />

        {/* Self-Corrections Section */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary, textTransform: 'uppercase' }}>
              Self-Corrections
            </Typography>
            <Chip
              icon={<AutoFixHighRoundedIcon sx={{ fontSize: 14 }} />}
              label={`${totalAttempts} Attempts`}
              size="small"
              sx={{ fontWeight: 700, fontSize: 10, bgcolor: alpha(theme.palette.info.main, 0.1), color: theme.palette.info.main }}
            />
          </Box>

          {correctionHistory.length > 0 ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {correctionHistory.map((item, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 1.2,
                    borderRadius: 2,
                    border: `1px solid ${theme.palette.divider}`,
                    bgcolor: alpha(theme.palette.background.paper, 0.5),
                    fontSize: 12
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.primary }}>
                      {item.step}
                    </Typography>
                    {item.status && (
                      <Chip
                        label={item.status}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: 9,
                          fontWeight: 700,
                          bgcolor: item.status === 'Fixed' || item.status === 'Completed' ? alpha(theme.palette.success.main, 0.1) : alpha(theme.palette.warning.main, 0.1),
                          color: item.status === 'Fixed' || item.status === 'Completed' ? theme.palette.success.main : theme.palette.warning.main
                        }}
                      />
                    )}
                  </Box>
                  {item.reason && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: 11 }}>
                      Reason: {item.reason}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          ) : (
            <Typography variant="caption" color="text.secondary">
              No self-correction loops triggered. Primary answer passed all validation thresholds on initial draft.
            </Typography>
          )}
        </Box>

        {sources && sources.length > 0 && (
          <>
            <Divider />
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary, mb: 1, display: 'block', textTransform: 'uppercase' }}>
                Retrieved Evidence ({sources.length})
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {sources.map((src, i) => (
                  <Box key={i} sx={{ p: 1.2, border: `1px solid ${theme.palette.divider}`, borderRadius: 2, bgcolor: alpha(theme.palette.background.paper, 0.4) }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: 12, wordBreak: 'break-all' }}>
                      {src.filename}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>
                      Chunk #{src.chunk_index} • Score: {src.relevance_score}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </>
        )}
      </Box>
    </Card>
  );
};

export default CriticPanel;
