import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Slider,
  Divider,
  IconButton,
  Alert,
  useTheme,
  alpha
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';

const SettingsDialog = ({ open, onClose, onSaveSettings }) => {
  const theme = useTheme();

  const [groundednessThresh, setGroundednessThresh] = useState(0.75);
  const [faithfulnessThresh, setFaithfulnessThresh] = useState(0.75);
  const [confidenceThresh, setConfidenceThresh] = useState(0.75);
  const [maxRetries, setMaxRetries] = useState(3);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (open) {
      fetchSettings();
    }
  }, [open]);

  const fetchSettings = async () => {
    try {
      const response = await fetch('http://localhost:5000/critic/settings');
      if (response.ok) {
        const data = await response.json();
        setGroundednessThresh(data.groundedness_threshold ?? 0.75);
        setFaithfulnessThresh(data.faithfulness_threshold ?? 0.75);
        setConfidenceThresh(data.confidence_threshold ?? 0.75);
        setMaxRetries(data.max_retries ?? 3);
      }
    } catch (e) {
      console.error('Error loading settings:', e);
    }
  };

  const handleSave = async () => {
    const payload = {
      groundedness_threshold: groundednessThresh,
      faithfulness_threshold: faithfulnessThresh,
      confidence_threshold: confidenceThresh,
      max_retries: maxRetries
    };

    try {
      const response = await fetch('http://localhost:5000/critic/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        setSavedSuccess(true);
        if (onSaveSettings) onSaveSettings(payload);
        setTimeout(() => {
          setSavedSuccess(false);
          onClose();
        }, 1000);
      }
    } catch (e) {
      console.error('Error saving critic settings:', e);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          p: 1
        }
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TuneRoundedIcon sx={{ color: theme.palette.info.main }} />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Critic Agent Threshold Settings
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseRoundedIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 3, py: 3 }}>
        {savedSuccess && (
          <Alert severity="success" sx={{ borderRadius: 2 }}>
            Settings updated successfully!
          </Alert>
        )}

        <Typography variant="body2" color="text.secondary">
          Configure the evaluation thresholds for answer verification. If generated scores fall below these thresholds, the Decision Engine will trigger query expansion and re-retrieval.
        </Typography>

        {/* Groundedness Slider */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Groundedness Threshold</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: theme.palette.info.main }}>{Math.round(groundednessThresh * 100)}%</Typography>
          </Box>
          <Slider
            value={groundednessThresh}
            min={0.5}
            max={0.95}
            step={0.05}
            onChange={(e, v) => setGroundednessThresh(v)}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${Math.round(v * 100)}%`}
          />
        </Box>

        {/* Faithfulness Slider */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Faithfulness Threshold</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: theme.palette.info.main }}>{Math.round(faithfulnessThresh * 100)}%</Typography>
          </Box>
          <Slider
            value={faithfulnessThresh}
            min={0.5}
            max={0.95}
            step={0.05}
            onChange={(e, v) => setFaithfulnessThresh(v)}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${Math.round(v * 100)}%`}
          />
        </Box>

        {/* Confidence Slider */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Confidence Threshold</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: theme.palette.info.main }}>{Math.round(confidenceThresh * 100)}%</Typography>
          </Box>
          <Slider
            value={confidenceThresh}
            min={0.5}
            max={0.95}
            step={0.05}
            onChange={(e, v) => setConfidenceThresh(v)}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${Math.round(v * 100)}%`}
          />
        </Box>

        {/* Max Retries Slider */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Maximum Self-Correction Retries</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: theme.palette.info.main }}>{maxRetries} Retries</Typography>
          </Box>
          <Slider
            value={maxRetries}
            min={1}
            max={5}
            step={1}
            marks
            onChange={(e, v) => setMaxRetries(v)}
            valueLabelDisplay="auto"
          />
        </Box>
      </DialogContent>

      <Divider />

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="outlined" sx={{ borderRadius: 2 }}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" sx={{ borderRadius: 2 }}>
          Save Configuration
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SettingsDialog;
