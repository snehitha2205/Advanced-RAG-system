import React from 'react';
import { Box, Typography, Chip, IconButton, Divider, alpha, useTheme, Paper, List, ListItem, ListItemText, Button } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SchemaIcon from '@mui/icons-material/Schema';
import { getEntityColor, getPredicateColor } from './GraphCanvas';

const DetailRow = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.75, px: 1, borderRadius: 1, '&:hover': { bgcolor: alpha('#000', 0.02) } }}>
    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, fontSize: 11 }}>{label}</Typography>
    <Box sx={{ textAlign: 'right' }}>
      {typeof value === 'string' && value.startsWith('http') ? (
        <Typography variant="caption" sx={{ fontSize: 11, wordBreak: 'break-all', maxWidth: 180 }}>{value}</Typography>
      ) : (
        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: 12, color }}>{value || '-'}</Typography>
      )}
    </Box>
  </Box>
);

const RightInspector = ({ selectedNode, selectedEdge, onClose, onExpandNode, onFindPath }) => {
  const theme = useTheme();

  const renderEntityInspector = () => {
    if (!selectedNode) return null;
    const color = getEntityColor(selectedNode.entity_type || 'ENTITY');
    const aliases = selectedNode.aliases || [];
    const sourceDocs = selectedNode.source_documents || [];
    const frequency = selectedNode.frequency || 1;
    const confidence = selectedNode.confidence || 0.8;
    const degree = selectedNode.degree || 0;

    return (
      <Box>
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: 16, mb: 1, wordBreak: 'break-word' }}>
            {selectedNode.canonical_name || selectedNode.label || selectedNode.id}
          </Typography>
          <Chip label={selectedNode.entity_type || 'ENTITY'} size="small" sx={{ fontWeight: 700, fontSize: 10, bgcolor: alpha(color, 0.12), color, borderRadius: 1 }} />
        </Box>
        <Box sx={{ p: 1.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>ENTITY DETAILS</Typography>
          <Box sx={{ bgcolor: alpha(theme.palette.background.default, 0.5), borderRadius: 1.5, p: 0.5 }}>
            <DetailRow label="Entity ID" value={selectedNode.id?.substring(0, 16) + '...'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Original Name" value={selectedNode.original_name || selectedNode.canonical_name} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Entity Type" value={selectedNode.entity_type} color={color} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Confidence" value={`${(confidence * 100).toFixed(1)}%`} color={confidence > 0.7 ? '#10B981' : confidence > 0.4 ? '#F59E0B' : '#EF4444'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Frequency" value={frequency} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Graph Degree" value={degree} />
          </Box>
        </Box>

        {aliases.length > 0 && (
          <Box sx={{ px: 1.5, pb: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5 }}>ALIASES</Typography>
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {aliases.map((a, i) => <Chip key={i} label={a} size="small" variant="outlined" sx={{ fontSize: 10, height: 22 }} />)}
            </Box>
          </Box>
        )}

        {sourceDocs.length > 0 && (
          <Box sx={{ px: 1.5, pb: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5 }}>SOURCE DOCUMENTS</Typography>
            <List dense disablePadding>
              {sourceDocs.slice(0, 5).map((doc, i) => (
                <ListItem key={i} disablePadding sx={{ mb: 0.25 }}>
                  <ListItemText primary={doc} primaryTypographyProps={{ variant: 'caption', sx: { fontSize: 10, wordBreak: 'break-all' } }} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {/* Timeline */}
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>TIMELINE</Typography>
          <Box sx={{ bgcolor: alpha(theme.palette.background.default, 0.5), borderRadius: 1.5, p: 0.5 }}>
            <DetailRow label="First Seen" value={selectedNode.first_seen ? new Date(selectedNode.first_seen).toLocaleDateString() : '-'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Last Seen" value={selectedNode.last_seen ? new Date(selectedNode.last_seen).toLocaleDateString() : '-'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Created" value={selectedNode.created_at ? new Date(selectedNode.created_at).toLocaleDateString() : '-'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Updated" value={selectedNode.updated_at ? new Date(selectedNode.updated_at).toLocaleDateString() : '-'} />
          </Box>
        </Box>

        {/* Actions */}
        <Box sx={{ p: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" variant="contained" color="info" startIcon={<SchemaIcon />} onClick={() => onExpandNode?.(selectedNode.id)} sx={{ borderRadius: 1.5, fontSize: 11 }}>
            Expand
          </Button>
          <Button size="small" variant="outlined" startIcon={<AccountTreeIcon />} onClick={() => onFindPath?.(selectedNode.id)} sx={{ borderRadius: 1.5, fontSize: 11 }}>
            Find Path
          </Button>
        </Box>
      </Box>
    );
  };

  const renderRelationshipInspector = () => {
    if (!selectedEdge) return null;
    const color = getPredicateColor(selectedEdge.predicate || selectedEdge.normalized_predicate);
    const confidence = selectedEdge.confidence || 0.5;
    const weight = selectedEdge.weight || 1;
    const supportingSentences = selectedEdge.supporting_sentences || [];
    const sourceDocs = selectedEdge.source_documents || [];

    return (
      <Box>
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: 14, mb: 1 }}>
            Relationship Details
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={selectedEdge.source_name || selectedEdge.source} size="small" sx={{ fontWeight: 600, fontSize: 10, bgcolor: alpha('#0EA5E9', 0.1), color: '#0EA5E9', borderRadius: 1 }} />
            <Typography variant="caption" sx={{ fontWeight: 700 }}>→</Typography>
            <Chip label={selectedEdge.predicate || selectedEdge.normalized_predicate || 'RELATED_TO'} size="small" sx={{ fontWeight: 600, fontSize: 10, bgcolor: alpha(color, 0.15), color, borderRadius: 1 }} />
            <Typography variant="caption" sx={{ fontWeight: 700 }}>→</Typography>
            <Chip label={selectedEdge.target_name || selectedEdge.target} size="small" sx={{ fontWeight: 600, fontSize: 10, bgcolor: alpha('#10B981', 0.1), color: '#10B981', borderRadius: 1 }} />
          </Box>
        </Box>
        <Box sx={{ p: 1.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>RELATIONSHIP PROPERTIES</Typography>
          <Box sx={{ bgcolor: alpha(theme.palette.background.default, 0.5), borderRadius: 1.5, p: 0.5 }}>
            <DetailRow label="Source" value={selectedEdge.source_name || selectedEdge.source} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Predicate" value={selectedEdge.predicate || selectedEdge.normalized_predicate || 'RELATED_TO'} color={color} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Target" value={selectedEdge.target_name || selectedEdge.target} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Confidence" value={`${(confidence * 100).toFixed(1)}%`} color={confidence > 0.7 ? '#10B981' : '#F59E0B'} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Weight" value={weight.toFixed(2)} />
            <Divider sx={{ mx: 1 }} />
            <DetailRow label="Frequency" value={selectedEdge.frequency || 1} />
          </Box>
        </Box>

        {supportingSentences.length > 0 && (
          <Box sx={{ px: 1.5, pb: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5 }}>SUPPORTING SENTENCES</Typography>
            {supportingSentences.slice(0, 3).map((s, i) => (
              <Paper key={i} variant="outlined" sx={{ p: 1, mb: 0.5, borderRadius: 1, bgcolor: alpha(theme.palette.info.main, 0.02) }}>
                <Typography variant="caption" sx={{ fontSize: 11, fontStyle: 'italic', color: 'text.secondary' }}>"{s}"</Typography>
              </Paper>
            ))}
          </Box>
        )}

        {sourceDocs.length > 0 && (
          <Box sx={{ px: 1.5, pb: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5 }}>SOURCE DOCUMENTS</Typography>
            <List dense disablePadding>
              {sourceDocs.slice(0, 3).map((doc, i) => (
                <ListItem key={i} disablePadding>
                  <ListItemText primary={doc} primaryTypographyProps={{ variant: 'caption', sx: { fontSize: 10, wordBreak: 'break-all' } }} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Box>
    );
  };

  const isVisible = selectedNode || selectedEdge;
  if (!isVisible) {
    return (
      <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
        <SchemaIcon sx={{ fontSize: 40, color: alpha(theme.palette.text.secondary, 0.2), mb: 1 }} />
        <Typography variant="body2" sx={{ fontWeight: 500 }}>Select a node or edge</Typography>
        <Typography variant="caption">Click on any entity or relationship to inspect details</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper', borderLeft: `1px solid ${theme.palette.divider}` }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 1.5, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'text.secondary' }}>
          INSPECTOR
        </Typography>
        <IconButton size="small" onClick={onClose}><CloseIcon fontSize="small" /></IconButton>
      </Box>
      <Box sx={{ flex: 1, overflowY: 'auto' }}>
        {selectedNode ? renderEntityInspector() : renderRelationshipInspector()}
      </Box>
    </Box>
  );
};

export default RightInspector;