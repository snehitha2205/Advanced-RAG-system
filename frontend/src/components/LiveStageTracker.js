import React, { useEffect, useState } from 'react';
import { Box, Typography, Card, LinearProgress, useTheme, alpha } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';

// Icons
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import HourglassTopRoundedIcon from '@mui/icons-material/HourglassTopRounded';
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded';
import AnalyticsRoundedIcon from '@mui/icons-material/AnalyticsRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import FormatListNumberedRoundedIcon from '@mui/icons-material/FormatListNumberedRounded';
import SmartToyRoundedIcon from '@mui/icons-material/SmartToyRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import AutoFixHighRoundedIcon from '@mui/icons-material/AutoFixHighRounded';
import FindInPageRoundedIcon from '@mui/icons-material/FindInPageRounded';
import VerifiedRoundedIcon from '@mui/icons-material/VerifiedRounded';
import TaskAltRoundedIcon from '@mui/icons-material/TaskAltRounded';

const STAGES = [
  { id: 'understand', label: 'Understanding Question', icon: PsychologyRoundedIcon },
  { id: 'analysis', label: 'Query Analysis', icon: AnalyticsRoundedIcon },
  { id: 'retrieval', label: 'Retrieving Documents', icon: DescriptionRoundedIcon },
  { id: 'graph_search', label: 'Searching Knowledge Graph', icon: HubRoundedIcon },
  { id: 'rank', label: 'Ranking Evidence', icon: FormatListNumberedRoundedIcon },
  { id: 'generate_draft', label: 'Generating Draft Answer', icon: SmartToyRoundedIcon },
  { id: 'critic', label: 'Critic Evaluation', icon: SearchRoundedIcon },
  { id: 'correction', label: 'Self Correction', icon: AutoFixHighRoundedIcon },
  { id: 're_retrieval', label: 'Additional Retrieval', icon: FindInPageRoundedIcon },
  { id: 'verify', label: 'Final Verification', icon: VerifiedRoundedIcon },
  { id: 'ready', label: 'Response Ready', icon: TaskAltRoundedIcon }
];

const LiveStageTracker = ({ activeIndex = 0, isComplete = false, retryCount = 0 }) => {
  const theme = useTheme();
  const [visibleStageIdx, setVisibleStageIdx] = useState(0);

  useEffect(() => {
    if (isComplete) {
      setVisibleStageIdx(STAGES.length - 1);
      return;
    }

    const interval = setInterval(() => {
      setVisibleStageIdx(prev => {
        if (prev < activeIndex) return prev + 1;
        return prev;
      });
    }, 300);

    return () => clearInterval(interval);
  }, [activeIndex, isComplete]);

  // Filter out correction stages if no retries occurred
  const displayStages = STAGES.filter(s => {
    if ((s.id === 'correction' || s.id === 're_retrieval') && retryCount === 0 && !isComplete) {
      return false;
    }
    return true;
  });

  const progressPercent = Math.min(100, Math.round(((visibleStageIdx + 1) / displayStages.length) * 100));

  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      sx={{
        p: 2.5,
        mb: 3,
        borderRadius: 3,
        bgcolor: alpha(theme.palette.background.paper, 0.8),
        backdropFilter: 'blur(12px)',
        border: `1px solid ${alpha(theme.palette.info.main, 0.25)}`,
        boxShadow: `0 8px 32px ${alpha(theme.palette.info.main, 0.08)}`
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1, color: theme.palette.info.main }}>
          <PsychologyRoundedIcon sx={{ fontSize: 20 }} />
          Agentic Execution Pipeline
        </Typography>
        <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.text.secondary }}>
          {progressPercent}% Complete
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={progressPercent}
        sx={{
          height: 6,
          borderRadius: 3,
          mb: 2.5,
          bgcolor: alpha(theme.palette.info.main, 0.1),
          '& .MuiLinearProgress-bar': {
            borderRadius: 3,
            background: `linear-gradient(90deg, ${theme.palette.info.main}, ${theme.palette.success.main})`
          }
        }}
      />

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1 }}>
        <AnimatePresence>
          {displayStages.map((stage, idx) => {
            const Icon = stage.icon;
            const isDone = idx < visibleStageIdx || isComplete;
            const isCurrent = idx === visibleStageIdx && !isComplete;

            return (
              <Box
                key={stage.id}
                component={motion.div}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.03 }}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  p: 1,
                  borderRadius: 2,
                  bgcolor: isCurrent ? alpha(theme.palette.info.main, 0.12) : isDone ? alpha(theme.palette.success.main, 0.05) : 'transparent',
                  border: `1px solid ${isCurrent ? alpha(theme.palette.info.main, 0.4) : isDone ? alpha(theme.palette.success.main, 0.2) : alpha(theme.palette.divider, 0.4)}`,
                  transition: 'all 0.2s'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', color: isDone ? theme.palette.success.main : isCurrent ? theme.palette.info.main : theme.palette.text.disabled }}>
                  {isDone ? (
                    <CheckCircleRoundedIcon sx={{ fontSize: 18 }} />
                  ) : isCurrent ? (
                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}>
                      <HourglassTopRoundedIcon sx={{ fontSize: 18 }} />
                    </motion.div>
                  ) : (
                    <Icon sx={{ fontSize: 18 }} />
                  )}
                </Box>

                <Typography
                  variant="body2"
                  sx={{
                    fontSize: 13,
                    fontWeight: isCurrent ? 700 : isDone ? 600 : 400,
                    color: isDone ? theme.palette.text.primary : isCurrent ? theme.palette.info.main : theme.palette.text.secondary
                  }}
                >
                  {stage.label}
                </Typography>
              </Box>
            );
          })}
        </AnimatePresence>
      </Box>
    </Card>
  );
};

export default LiveStageTracker;
