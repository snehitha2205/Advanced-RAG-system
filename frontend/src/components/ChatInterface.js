import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Button,
  Avatar,
  Divider,
  IconButton,
  InputBase,
  useTheme,
  alpha,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Paper,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

// Icons
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import AttachFileRoundedIcon from '@mui/icons-material/AttachFileRounded';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import PushPinRoundedIcon from '@mui/icons-material/PushPinRounded';
import DataObjectRoundedIcon from '@mui/icons-material/DataObjectRounded';
import VerifiedUserRoundedIcon from '@mui/icons-material/VerifiedUserRounded';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import CompareArrowsRoundedIcon from '@mui/icons-material/CompareArrowsRounded';
import TimerRoundedIcon from '@mui/icons-material/TimerRounded';
import AutoFixHighRoundedIcon from '@mui/icons-material/AutoFixHighRounded';

// Agentic Components
import LiveStageTracker from './LiveStageTracker';
import CriticPanel from './CriticPanel';
import CorrectionTimeline from './CorrectionTimeline';
import MetricsPanel from './MetricsPanel';
import SettingsDialog from './SettingsDialog';

const ChatInterface = ({ sessionId, setSessionId, onCreateNewSession }) => {
  const theme = useTheme();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionList, setSessionList] = useState([]);
  const [activeStageIdx, setActiveStageIdx] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showImprovementsIdx, setShowImprovementsIdx] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (sessionId) {
      loadConversationHistory();
    }
  }, [sessionId]);

  const fetchSessions = async () => {
    try {
      const response = await fetch('http://localhost:5000/sessions');
      const data = await response.json();
      setSessionList(data.sessions || []);
    } catch (error) {
      console.error('Error fetching sessions', error);
    }
  };

  const loadConversationHistory = async () => {
    try {
      const response = await fetch(`http://localhost:5000/session/${sessionId}`);
      const data = await response.json();
      if (data.messages) {
        setMessages(data.messages);
      }
    } catch (error) {
      console.error('Error loading history:', error);
    }
  };

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return;

    const userMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setActiveStageIdx(0);

    // Simulate progressive stages timing while waiting for backend
    const stageTimer = setInterval(() => {
      setActiveStageIdx(prev => (prev < 9 ? prev + 1 : prev));
    }, 1200);

    try {
      const response = await fetch('http://localhost:5000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          session_id: sessionId
        })
      });

      const data = await response.json();
      clearInterval(stageTimer);
      setActiveStageIdx(10); // Complete

      if (response.ok) {
        const assistantMessage = {
          role: 'assistant',
          content: data.answer,
          metadata: {
            sources: data.sources,
            draft_answer: data.draft_answer,
            critic_report: data.critic_report,
            metrics: data.metrics,
            correction_history: data.correction_history,
            what_changed: data.what_changed
          }
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      clearInterval(stageTimer);
      console.error('Error sending query:', error);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
      fetchSessions();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Get active assistant context from the last assistant message
  const lastAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');
  const activeSources = lastAssistantMessage?.metadata?.sources || [];
  const activeCriticReport = lastAssistantMessage?.metadata?.critic_report || null;
  const activeCorrectionHistory = lastAssistantMessage?.metadata?.correction_history || [];
  const activeMetrics = lastAssistantMessage?.metadata?.metrics || {};

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 120px)', width: '100%', gap: 2 }}>
      
      {/* LEFT PANEL: History & Controls */}
      <Card sx={{ width: 280, display: { xs: 'none', lg: 'flex' }, flexDirection: 'column', bgcolor: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, boxShadow: 'none' }}>
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, display: 'flex', gap: 1 }}>
          <Button 
            fullWidth 
            variant="contained" 
            startIcon={<AddRoundedIcon />}
            onClick={() => { onCreateNewSession(); setMessages([]); }}
            sx={{ borderRadius: 2 }}
          >
            New Workspace
          </Button>
          <Tooltip title="Critic Settings">
            <IconButton onClick={() => setSettingsOpen(true)} sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 2 }}>
              <TuneRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Box sx={{ flex: 1, overflowY: 'auto', p: 1 }}>
          <Typography variant="caption" sx={{ ml: 1, mb: 1, display: 'block', fontWeight: 600, color: theme.palette.text.secondary }}>
            RECENT AGENTIC THREADS
          </Typography>
          <List disablePadding>
            {sessionList.map((s) => (
              <ListItem key={s.id} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton 
                  selected={s.id === sessionId}
                  onClick={() => setSessionId(s.id)}
                  sx={{ 
                    borderRadius: 2, 
                    px: 1.5, py: 1,
                    '&.Mui-selected': { bgcolor: alpha(theme.palette.info.main, 0.1) }
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <ChatBubbleOutlineRoundedIcon sx={{ fontSize: 18, color: s.id === sessionId ? theme.palette.info.main : theme.palette.text.secondary }} />
                  </ListItemIcon>
                  <ListItemText 
                    primary={s.id ? `Thread ${s.id.substring(0,6)}` : 'Active'} 
                    secondary={s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Just now'}
                    primaryTypographyProps={{ variant: 'body2', fontWeight: s.id === sessionId ? 600 : 500 }}
                    secondaryTypographyProps={{ variant: 'caption', fontSize: 10 }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Card>

      {/* CENTER PANEL: Workspace Chat & Live Agentic Pipeline */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        
        {/* Header Bar */}
        <Box sx={{ px: 3, py: 1.5, borderBottom: `1px solid ${theme.palette.divider}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: alpha(theme.palette.background.paper, 0.8), backdropFilter: 'blur(8px)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AutoAwesomeRoundedIcon sx={{ color: theme.palette.info.main, fontSize: 20 }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Enterprise Agentic AI Platform
            </Typography>
            <Chip label="Self-Correcting Enabled" size="small" sx={{ fontWeight: 700, fontSize: 10, bgcolor: alpha(theme.palette.success.main, 0.12), color: theme.palette.success.main }} />
          </Box>
          <Button
            size="small"
            startIcon={<TuneRoundedIcon />}
            onClick={() => setSettingsOpen(true)}
            sx={{ fontWeight: 600, textTransform: 'none', borderRadius: 2 }}
          >
            Config Thresholds
          </Button>
        </Box>

        <Box sx={{ flex: 1, overflowY: 'auto', p: 2, pb: 14 }}>
          {messages.length === 0 ? (
            <Box component={motion.div} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} sx={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
              <Avatar sx={{ width: 64, height: 64, bgcolor: alpha(theme.palette.info.main, 0.1), color: theme.palette.info.main, mb: 3 }}>
                <AutoAwesomeRoundedIcon fontSize="large" />
              </Avatar>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Agentic RAG & Evaluation Engine</Typography>
              <Typography color="text.secondary" sx={{ mb: 4, textAlign: 'center', maxWidth: 480 }}>
                Query your GraphRAG architecture. Answers are automatically evaluated for groundedness, faithfulness, completeness, and self-corrected iteratively.
              </Typography>
              
              <Grid container spacing={2} sx={{ maxWidth: 650 }}>
                {[
                  'Explain battery degradation factors and thermal mitigation',
                  'Summarize key relationships in our technical documentation',
                  'Compare system throughput parameters across versions'
                ].map((suggestion, i) => (
                  <Grid item xs={12} sm={4} key={i}>
                    <Card 
                      onClick={() => handleSend(suggestion)}
                      sx={{ 
                        p: 2, height: '100%', cursor: 'pointer', borderRadius: 3,
                        transition: 'all 0.2s',
                        '&:hover': { borderColor: theme.palette.info.main, transform: 'translateY(-2px)' }
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{suggestion}</Typography>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : (
            <Box sx={{ maxWidth: 880, mx: 'auto' }}>
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                const meta = msg.metadata || {};
                const report = meta.critic_report;
                const history = meta.correction_history || [];
                const metrics = meta.metrics || {};
                const whatChanged = meta.what_changed;
                const draftAns = meta.draft_answer;

                return (
                  <Box component={motion.div} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key={idx} sx={{ mb: 4 }}>
                    <Box sx={{ display: 'flex', gap: 2, flexDirection: isUser ? 'row-reverse' : 'row' }}>
                      <Avatar sx={{ 
                        bgcolor: isUser ? theme.palette.primary.main : alpha(theme.palette.info.main, 0.1),
                        color: isUser ? theme.palette.primary.contrastText : theme.palette.info.main,
                        width: 34, height: 34
                      }}>
                        {isUser ? <PersonRoundedIcon fontSize="small" /> : <AutoAwesomeRoundedIcon fontSize="small" />}
                      </Avatar>

                      <Box sx={{ flex: 1, maxWidth: isUser ? '85%' : '100%' }}>
                        
                        {/* Assistant Answer Header Card */}
                        {!isUser && report && (
                          <Card
                            sx={{
                              p: 1.5,
                              mb: 2,
                              borderRadius: 2.5,
                              bgcolor: alpha(theme.palette.info.main, 0.04),
                              border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                              boxShadow: 'none',
                              display: 'flex',
                              alignItems: 'center',
                              justify: 'space-between',
                              flexWrap: 'wrap',
                              gap: 1
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <VerifiedUserRoundedIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                                Verified by Critic Agent
                              </Typography>
                            </Box>

                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                              <Chip
                                label={`Reliability: ${report.overall_quality_score}/100`}
                                size="small"
                                sx={{ fontWeight: 700, bgcolor: alpha(theme.palette.success.main, 0.12), color: theme.palette.success.main }}
                              />
                              <Chip
                                label={`Groundedness: ${Math.round((report.groundedness || 0.9)*100)}%`}
                                size="small"
                                sx={{ fontWeight: 700, bgcolor: alpha(theme.palette.info.main, 0.12), color: theme.palette.info.main }}
                              />
                              <Chip
                                icon={<AutoFixHighRoundedIcon sx={{ fontSize: 14 }} />}
                                label={`${metrics.retry_count || 0} Corrections`}
                                size="small"
                                sx={{ fontWeight: 700, bgcolor: alpha(theme.palette.warning.main, 0.12), color: theme.palette.warning.main }}
                              />
                              <Chip
                                icon={<TimerRoundedIcon sx={{ fontSize: 14 }} />}
                                label={`${metrics.total_response_time_seconds || 0}s`}
                                size="small"
                                variant="outlined"
                                sx={{ fontWeight: 600 }}
                              />
                            </Box>
                          </Card>
                        )}

                        {/* Answer Content Card */}
                        <Box sx={{ 
                          bgcolor: isUser ? theme.palette.background.paper : alpha(theme.palette.background.paper, 0.6),
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 3, p: 2.5
                        }}>
                          <Typography component="div" variant="body1" sx={{ 
                            '& p': { mt: 0, mb: 2, lineHeight: 1.7 },
                            '& pre': { p: 2, borderRadius: 2, bgcolor: theme.palette.mode === 'light' ? '#F1F5F9' : '#0D1117', overflowX: 'auto' },
                            '& code': { fontFamily: 'monospace' }
                          }}>
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </Typography>
                        </Box>

                        {/* Answer Comparison Expander (If Self-Corrections Occurred) */}
                        {!isUser && (draftAns || whatChanged) && (
                          <Accordion
                            sx={{ mt: 1.5, borderRadius: '12px !important', border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`, boxShadow: 'none', '&:before': { display: 'none' } }}
                          >
                            <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CompareArrowsRoundedIcon sx={{ color: theme.palette.warning.main, fontSize: 20 }} />
                                <Typography variant="subtitle2" sx={{ fontWeight: 700, color: theme.palette.warning.main }}>
                                  Show Answer Improvements & Comparison
                                </Typography>
                              </Box>
                            </AccordionSummary>
                            <AccordionDetails sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              <Grid container spacing={2}>
                                {draftAns && (
                                  <Grid item xs={12} md={6}>
                                    <Paper sx={{ p: 2, border: `1px solid ${theme.palette.divider}`, borderRadius: 2, bgcolor: alpha(theme.palette.error.main, 0.02) }}>
                                      <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.error.main, display: 'block', mb: 1 }}>
                                        INITIAL DRAFT ANSWER (Pre-Correction)
                                      </Typography>
                                      <Typography variant="body2" sx={{ fontSize: 13, lineHeight: 1.5, color: theme.palette.text.secondary }}>
                                        {draftAns}
                                      </Typography>
                                    </Paper>
                                  </Grid>
                                )}

                                <Grid item xs={12} md={draftAns ? 6 : 12}>
                                  <Paper sx={{ p: 2, border: `1px solid ${theme.palette.divider}`, borderRadius: 2, bgcolor: alpha(theme.palette.success.main, 0.02) }}>
                                    <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.success.main, display: 'block', mb: 1 }}>
                                      VERIFIED FINAL ANSWER
                                    </Typography>
                                    <Typography variant="body2" sx={{ fontSize: 13, lineHeight: 1.5 }}>
                                      {msg.content}
                                    </Typography>
                                  </Paper>
                                </Grid>
                              </Grid>

                              {whatChanged && (
                                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha(theme.palette.info.main, 0.06), border: `1px solid ${alpha(theme.palette.info.main, 0.2)}` }}>
                                  <Typography variant="caption" sx={{ fontWeight: 700, color: theme.palette.info.main, display: 'block', mb: 0.5 }}>
                                    WHAT CHANGED & IMPROVED
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    • <strong>Missing Evidence Addressed:</strong> {Array.isArray(whatChanged.missing_evidence) ? whatChanged.missing_evidence.join(', ') : whatChanged.missing_evidence}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    • <strong>Evidence Context Added:</strong> {whatChanged.evidence_added}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    • <strong>Quality Outcome:</strong> {whatChanged.quality_improved}
                                  </Typography>
                                </Box>
                              )}
                            </AccordionDetails>
                          </Accordion>
                        )}

                        {/* Self-Correction Workflow Timeline */}
                        {!isUser && history.length > 1 && (
                          <CorrectionTimeline history={history} retryCount={metrics.retry_count || 1} />
                        )}

                        {/* Telemetry Metrics Panel */}
                        {!isUser && metrics && metrics.retrieval_time_seconds !== undefined && (
                          <MetricsPanel metrics={metrics} />
                        )}

                      </Box>
                    </Box>
                  </Box>
                );
              })}

              {/* LIVE STAGE TRACKER (WHILE PROCESSING) */}
              {loading && (
                <Box sx={{ my: 3 }}>
                  <LiveStageTracker
                    activeIndex={activeStageIdx}
                    isComplete={false}
                    retryCount={0}
                  />
                </Box>
              )}

              <div ref={messagesEndRef} />
            </Box>
          )}
        </Box>

        {/* Floating Input Bar */}
        <Box sx={{ 
          position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)', 
          width: '100%', maxWidth: 840, px: 2 
        }}>
          <Paper sx={{ 
            p: '6px 12px', display: 'flex', alignItems: 'flex-end', 
            borderRadius: 4, border: `1px solid ${theme.palette.divider}`,
            boxShadow: theme.palette.mode === 'light' ? '0 10px 30px rgba(0,0,0,0.06)' : '0 10px 30px rgba(0,0,0,0.6)',
            bgcolor: alpha(theme.palette.background.paper, 0.9),
            backdropFilter: 'blur(12px)',
            transition: 'border-color 0.2s',
            '&:focus-within': { borderColor: theme.palette.info.main }
          }}>
            <IconButton sx={{ p: '10px', color: theme.palette.text.secondary }}>
              <AttachFileRoundedIcon />
            </IconButton>
            <InputBase
              sx={{ ml: 1, flex: 1, py: 1.5, fontSize: 15 }}
              placeholder="Ask anything... Critic Agent will validate and self-correct answer."
              multiline
              maxRows={6}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              inputRef={inputRef}
              disabled={loading}
            />
            <IconButton 
              color="primary" 
              onClick={() => handleSend(input)}
              disabled={!input.trim() || loading}
              sx={{ p: '10px', mb: 0.5, bgcolor: input.trim() ? theme.palette.info.main : 'transparent', color: input.trim() ? '#fff' : theme.palette.text.disabled, '&:hover': { bgcolor: theme.palette.info.dark } }}
            >
              <SendRoundedIcon fontSize="small" />
            </IconButton>
          </Paper>
        </Box>
      </Box>

      {/* RIGHT PANEL: AI Reasoning & Validation (Critic Panel) */}
      <Box sx={{ width: 340, display: { xs: 'none', md: 'flex' }, flexDirection: 'column', gap: 2 }}>
        <CriticPanel
          criticReport={activeCriticReport}
          correctionHistory={activeCorrectionHistory}
          metrics={activeMetrics}
          sources={activeSources}
        />
      </Box>


      {/* Settings Dialog Modal */}
      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      
    </Box>
  );
};

export default ChatInterface;