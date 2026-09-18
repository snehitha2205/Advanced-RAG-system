import React from 'react';
import { Box, Typography, Card, Chip, useTheme, alpha } from '@mui/material';
import { motion } from 'framer-motion';

// Icons
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded';
import AutoFixHighRoundedIcon from '@mui/icons-material/AutoFixHighRounded';
import FindInPageRoundedIcon from '@mui/icons-material/FindInPageRounded';
import SmartToyRoundedIcon from '@mui/icons-material/SmartToyRounded';
import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded';

const getStepIcon = (step) => {
  if (step.includes('Draft Generated')) return <SmartToyRoundedIcon fontSize="small" />;
  if (step.includes('Missing Evidence') || step.includes('Failed')) return <ErrorOutlineRoundedIcon fontSize="small" />;
  if (step.includes('Additional Retrieval')) return <FindInPageRoundedIcon fontSize="small" />;
  if (step.includes('Answer Improved')) return <AutoFixHighRoundedIcon fontSize="small" />;
  if (step.includes('Passed') || step.includes('Fixed')) return <CheckCircleRoundedIcon fontSize="small" />;
  return <CheckCircleRoundedIcon fontSize="small" />;
};

const CorrectionTimeline = ({ history = [], retryCount = 0 }) => {
  const theme = useTheme();

  if (!history || history.length <= 1) return null;

  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      sx={{
        p: 2.5,
        mt: 2,
        mb: 2,
        borderRadius: 3,
        bgcolor: alpha(theme.palette.background.paper, 0.9),
        border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
        boxShadow: 'none'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1, color: theme.palette.warning.main }}>
          <AutoFixHighRoundedIcon sx={{ fontSize: 20 }} />
          Self-Correction Workflow Timeline
        </Typography>
        <Chip
          label={`${retryCount} Correction ${retryCount === 1 ? 'Attempt' : 'Attempts'}`}
          size="small"
          sx={{ fontWeight: 700, bgcolor: alpha(theme.palette.warning.main, 0.12), color: theme.palette.warning.main }}
        />
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5, position: 'relative' }}>
        {history.map((item, idx) => {
          const isFail = item.step.includes('Missing Evidence') || item.status === 'Failed';
          const isPass = item.step.includes('Passed') || item.status === 'Fixed';
          const stepColor = isPass ? theme.palette.success.main : isFail ? theme.palette.error.main : theme.palette.info.main;

          return (
            <React.Fragment key={idx}>
              <Box
                component={motion.div}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.1 }}
                sx={{
                  width: '100%',
                  p: 1.5,
                  borderRadius: 2.5,
                  bgcolor: alpha(stepColor, 0.05),
                  border: `1px solid ${alpha(stepColor, 0.25)}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5
                }}
              >
                <Box sx={{ color: stepColor, display: 'flex', alignItems: 'center' }}>
                  {getStepIcon(item.step)}
                </Box>

                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: theme.palette.text.primary }}>
                      {item.step}
                    </Typography>
                    {item.attempt && (
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 600 }}>
                        Attempt {item.attempt}
                      </Typography>
                    )}
                  </Box>

                  {item.reason && (
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mt: 0.3 }}>
                      Reason: {item.reason}
                    </Typography>
                  )}

                  {item.missing_topics && item.missing_topics.length > 0 && (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                      {item.missing_topics.map((topic, i) => (
                        <Chip key={i} label={topic} size="small" sx={{ height: 18, fontSize: 10, bgcolor: alpha(theme.palette.error.main, 0.1), color: theme.palette.error.main }} />
                      ))}
                    </Box>
                  )}
                </Box>
              </Box>

              {idx < history.length - 1 && (
                <ArrowDownwardRoundedIcon sx={{ color: theme.palette.text.disabled, fontSize: 16, my: 0.2 }} />
              )}
            </React.Fragment>
          );
        })}
      </Box>
    </Card>
  );
};

export default CorrectionTimeline;
