import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, TextField, Slider, Chip, IconButton, List, ListItem, ListItemButton, ListItemText, ListItemIcon, alpha, useTheme, CircularProgress, Paper } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HistoryIcon from '@mui/icons-material/History';
import ClearIcon from '@mui/icons-material/Clear';

const API_BASE = 'http://localhost:5000';

const LeftSidebar = ({ onSearchResult, onFilterChange, stats }) => {
  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [autocompleteResults, setAutocompleteResults] = useState([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [entityTypes, setEntityTypes] = useState([]);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [minConfidence, setMinConfidence] = useState(0);
  const [minFrequency, setMinFrequency] = useState(0);
  const [recentSearches, setRecentSearches] = useState([]);

  useEffect(() => { fetchEntityTypes(); }, []);

  const fetchEntityTypes = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/graph/analytics`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.entity_type_distribution) {
          setEntityTypes(data.entity_type_distribution.map(t => t.entity_type));
        }
      }
    } catch (e) { console.error('Error fetching types', e); }
  };

  const handleSearch = useCallback(async (query) => {
    const q = query || searchQuery;
    if (!q.trim()) return;
    setSearching(true);
    setShowAutocomplete(false);
    try {
      const resp = await fetch(`${API_BASE}/graph/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, limit: 50 })
      });
      if (resp.ok) {
        const data = await resp.json();
        setSearchResults(data.results || []);
        onSearchResult?.(data.results || []);
        setRecentSearches(prev => [q, ...prev.filter(s => s !== q)].slice(0, 10));
      }
    } catch (e) { console.error('Search error', e); }
    finally { setSearching(false); }
  }, [searchQuery, onSearchResult]);

  const handleAutocomplete = useCallback(async (query) => {
    if (!query.trim()) { setAutocompleteResults([]); setShowAutocomplete(false); return; }
    try {
      const resp = await fetch(`${API_BASE}/api/graph/autocomplete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 8 })
      });
      if (resp.ok) { const data = await resp.json(); setAutocompleteResults(data.results || []); setShowAutocomplete(data.results?.length > 0); }
    } catch (e) {}
  }, []);

  const handleTypeToggle = (type) => {
    const updated = selectedTypes.includes(type) ? selectedTypes.filter(t => t !== type) : [...selectedTypes, type];
    setSelectedTypes(updated);
    onFilterChange?.({ entity_types: updated, min_confidence: minConfidence, min_frequency: minFrequency });
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setAutocompleteResults([]);
    setShowAutocomplete(false);
    onSearchResult?.(null);
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper', borderRight: `1px solid ${theme.palette.divider}` }}>
      {/* Search Header */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          <SearchIcon sx={{ fontSize: 18, color: theme.palette.info.main }} />
          Knowledge Search
        </Typography>
        <Paper sx={{ display: 'flex', alignItems: 'center', borderRadius: 2, border: `1px solid ${searchQuery ? theme.palette.info.main : theme.palette.divider}`, '&:focus-within': { borderColor: theme.palette.info.main } }}>
          <TextField
            fullWidth
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); handleAutocomplete(e.target.value); }}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            variant="standard"
            InputProps={{ disableUnderline: true, sx: { px: 1.5, py: 0.75, fontSize: 13 } }}
          />
          {searchQuery && (
            <IconButton size="small" onClick={handleClearSearch} sx={{ mr: 0.5 }}>
              <ClearIcon fontSize="small" />
            </IconButton>
          )}
          <IconButton size="small" onClick={() => handleSearch()} disabled={searching || !searchQuery.trim()} sx={{ mr: 0.5, color: theme.palette.info.main }}>
            {searching ? <CircularProgress size={16} /> : <SearchIcon fontSize="small" />}
          </IconButton>
        </Paper>
      </Box>

      {/* Entity Type Filters */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, maxHeight: 180, overflowY: 'auto' }}>
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>ENTITY TYPES</Typography>
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {entityTypes.map(type => (
            <Chip
              key={type}
              label={type}
              size="small"
              variant={selectedTypes.includes(type) ? 'filled' : 'outlined'}
              onClick={() => handleTypeToggle(type)}
              sx={{ fontSize: 10, fontWeight: 600, height: 24 }}
              color={selectedTypes.includes(type) ? 'info' : 'default'}
            />
          ))}
          {entityTypes.length === 0 && <Typography variant="caption" color="text.disabled">No types</Typography>}
        </Box>
      </Box>

      {/* Confidence & Frequency Filters */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1.5 }}>FILTERS</Typography>
        <Typography variant="caption" sx={{ fontSize: 11 }}>Min. Confidence</Typography>
        <Slider
          size="small"
          value={minConfidence}
          onChange={(_, v) => { 
            setMinConfidence(v); 
            onFilterChange?.({ entity_types: selectedTypes, min_confidence: v, min_frequency: minFrequency }); 
          }}
          step={0.05} 
          min={0} 
          max={1}
          valueLabelDisplay="auto"
          valueLabelFormat={v => `${(v * 100).toFixed(0)}%`}
          sx={{ mb: 1 }}
        />
        <Typography variant="caption" sx={{ fontSize: 11 }}>Min. Frequency</Typography>
        <Slider
          size="small"
          value={minFrequency}
          onChange={(_, v) => { 
            setMinFrequency(v); 
            onFilterChange?.({ entity_types: selectedTypes, min_confidence: minConfidence, min_frequency: v }); 
          }}
          step={1} 
          min={0} 
          max={20}
          valueLabelDisplay="auto"
          sx={{ mb: 1 }}
        />
      </Box>

      {/* Quick Stats */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 1 }}>QUICK STATISTICS</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
          {[
            { label: 'Entities', value: stats?.entity_count || 0 },
            { label: 'Relationships', value: stats?.relationship_count || 0 },
            { label: 'Documents', value: stats?.document_count || 0 },
            { label: 'Chunks', value: stats?.chunk_count || 0 }
          ].map((s, i) => (
            <Box key={i} sx={{ p: 1, borderRadius: 1.5, bgcolor: alpha(theme.palette.info.main, 0.04), border: `1px solid ${alpha(theme.palette.divider, 0.5)}` }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>{s.label}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{s.value}</Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Recent Searches */}
      {recentSearches.length > 0 && (
        <Box sx={{ flex: 1, overflowY: 'auto', p: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block', mb: 0.5, px: 1 }}>RECENT SEARCHES</Typography>
          <List dense disablePadding>
            {recentSearches.map((s, i) => (
              <ListItem key={i} disablePadding sx={{ mb: 0.25 }}>
                <ListItemButton onClick={() => { setSearchQuery(s); handleSearch(s); }} sx={{ borderRadius: 1.5, px: 1.5, py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 28 }}><HistoryIcon sx={{ fontSize: 14, color: 'text.secondary' }} /></ListItemIcon>
                  <ListItemText primary={s} primaryTypographyProps={{ variant: 'body2', sx: { fontSize: 12 } }} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default LeftSidebar;