import React from 'react';
import { Box, IconButton, Tooltip, ToggleButtonGroup, ToggleButton, Divider, alpha, useTheme, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import FitScreenIcon from '@mui/icons-material/FitScreen';
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong';
import RefreshIcon from '@mui/icons-material/Refresh';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import ViewQuiltIcon from '@mui/icons-material/ViewQuilt';
import MapIcon from '@mui/icons-material/Map';
import SettingsEthernetIcon from '@mui/icons-material/SettingsEthernet';
import ImageIcon from '@mui/icons-material/Image';
import CodeIcon from '@mui/icons-material/Code';
import GridViewIcon from '@mui/icons-material/GridView';

const GraphToolbar = ({ onZoomIn, onZoomOut, onFitScreen, onCenterGraph, onResetLayout, onToggleFullscreen, onExportPng, onExportJson, layout, onLayoutChange, showMinimap, onToggleMinimap }) => {
  const theme = useTheme();
  const [exportAnchor, setExportAnchor] = React.useState(null);
  const [layoutAnchor, setLayoutAnchor] = React.useState(null);

  const layouts = ['Force Directed', 'Hierarchical', 'Circular', 'Concentric', 'Grid', 'Radial'];

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.5, bgcolor: alpha(theme.palette.background.paper, 0.9), backdropFilter: 'blur(8px)', borderBottom: `1px solid ${theme.palette.divider}`, flexWrap: 'wrap' }}>
      <Tooltip title="Zoom In"><IconButton size="small" onClick={onZoomIn}><ZoomInIcon fontSize="small" /></IconButton></Tooltip>
      <Tooltip title="Zoom Out"><IconButton size="small" onClick={onZoomOut}><ZoomOutIcon fontSize="small" /></IconButton></Tooltip>
      <Tooltip title="Fit to Screen"><IconButton size="small" onClick={onFitScreen}><FitScreenIcon fontSize="small" /></IconButton></Tooltip>
      <Tooltip title="Center Graph"><IconButton size="small" onClick={onCenterGraph}><CenterFocusStrongIcon fontSize="small" /></IconButton></Tooltip>
      <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
      <Tooltip title="Reset Layout"><IconButton size="small" onClick={onResetLayout}><RefreshIcon fontSize="small" /></IconButton></Tooltip>
      <Tooltip title="Change Layout">
        <IconButton size="small" onClick={(e) => setLayoutAnchor(e.currentTarget)}>
          <GridViewIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu anchorEl={layoutAnchor} open={Boolean(layoutAnchor)} onClose={() => setLayoutAnchor(null)}>
        {layouts.map((l) => (
          <MenuItem key={l} selected={layout === l} onClick={() => { onLayoutChange?.(l); setLayoutAnchor(null); }}>
            <ListItemText primary={l} />
          </MenuItem>
        ))}
      </Menu>
      <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
      <Tooltip title="Toggle Minimap"><IconButton size="small" onClick={onToggleMinimap} color={showMinimap ? 'primary' : 'default'}><MapIcon fontSize="small" /></IconButton></Tooltip>
      <Tooltip title="Fullscreen"><IconButton size="small" onClick={onToggleFullscreen}><FullscreenIcon fontSize="small" /></IconButton></Tooltip>
      <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
      <Tooltip title="Export">
        <IconButton size="small" onClick={(e) => setExportAnchor(e.currentTarget)}>
          <FileDownloadIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu anchorEl={exportAnchor} open={Boolean(exportAnchor)} onClose={() => setExportAnchor(null)}>
        <MenuItem onClick={() => { onExportPng?.(); setExportAnchor(null); }}>
          <ListItemIcon><ImageIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Export as PNG</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => { onExportJson?.(); setExportAnchor(null); }}>
          <ListItemIcon><CodeIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Export as JSON</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default GraphToolbar;
