// import React, { useState, useCallback, useEffect } from 'react';
// import { useDropzone } from 'react-dropzone';
// import {
//   Box,
// } from '@mui/material';
// import { AnimatePresence } from 'framer-motion';

// import LeftPanel from './documents/LeftPanel';
// import DocumentToolbar from './documents/DocumentToolbar';
// import UploadDropzone from './documents/UploadDropzone';
// import DocumentGrid from './documents/DocumentGrid';
// import EmptyState from './documents/EmptyState';
// import InspectorPanel from './documents/InspectorPanel';

// const DocumentUpload = ({ darkMode }) => {

//   // === EXISTING STATE - UNCHANGED ===
//   const [documents, setDocuments] = useState([]);
//   const [uploadQueue, setUploadQueue] = useState([]);
//   const [searchQuery, setSearchQuery] = useState('');
//   const [selectedDoc, setSelectedDoc] = useState(null);
//   const [loading, setLoading] = useState(true);

//   // New UI state
//   const [activeFilter, setActiveFilter] = useState('all');
//   const [sortBy, setSortBy] = useState('newest');
//   const [viewMode, setViewMode] = useState('grid');

//   // === EXISTING LOGIC - UNCHANGED ===
//   const fetchDocuments = async () => {
//     try {
//       const res = await fetch('http://localhost:5000/documents');
//       const data = await res.json();
//       setDocuments(data.documents || []);
//     } catch (err) {
//       console.error('Failed to fetch documents', err);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchDocuments();
//   }, []);

//   const onDrop = useCallback((acceptedFiles) => {
//     const newFiles = acceptedFiles.map(file => ({
//       file,
//       id: Math.random().toString(36).substring(7),
//       filename: file.name,
//       status: 'pending',
//       progress: 0,
//       size_mb: (file.size / (1024 * 1024)).toFixed(2),
//       uploaded_at: new Date().toISOString(),
//       result: null
//     }));

//     setUploadQueue(prev => [...prev, ...newFiles]);
//   }, []);

//   const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
//     onDrop,
//     accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] },
//     maxSize: 16 * 1024 * 1024,
//     noClick: true,
//     noKeyboard: true
//   });

//   const uploadFile = async (fileItem) => {
//     const formData = new FormData();
//     formData.append('file', fileItem.file);

//     setUploadQueue(prev => prev.map(f => f.id === fileItem.id ? { ...f, status: 'uploading', progress: 30 } : f));

//     try {
//       const response = await fetch('http://localhost:5000/upload', {
//         method: 'POST',
//         body: formData
//       });

//       const data = await response.json();

//       if (response.ok) {
//         setUploadQueue(prev => prev.map(f => f.id === fileItem.id ? { ...f, status: 'completed', progress: 100, result: data } : f));
//         fetchDocuments();
//       } else {
//         throw new Error(data.error || 'Upload failed');
//       }
//     } catch (error) {
//       setUploadQueue(prev => prev.map(f => f.id === fileItem.id ? { ...f, status: 'error', error: error.message } : f));
//     }
//   };

//   const handleUploadAll = async () => {
//     const pendingFiles = uploadQueue.filter(f => f.status === 'pending');
//     for (const file of pendingFiles) {
//       await uploadFile(file);
//     }
//   };

//   const removeUpload = (id) => {
//     setUploadQueue(prev => prev.filter(f => f.id !== id));
//   };

//   // === COMPUTED VALUES ===
//   const allItems = [...uploadQueue, ...documents.filter(d => !uploadQueue.find(uq => uq.filename === d.filename))];

//   let filteredItems = allItems.filter(item => 
//     item.filename?.toLowerCase().includes(searchQuery.toLowerCase())
//   );

//   // Apply filter
//   if (activeFilter === 'recent') {
//     filteredItems = filteredItems.sort((a, b) => new Date(b.uploaded_at || 0) - new Date(a.uploaded_at || 0)).slice(0, 10);
//   } else if (activeFilter === 'completed') {
//     filteredItems = filteredItems.filter(d => d.status === 'completed' || (!d.status && d.filename));
//   } else if (activeFilter === 'processing') {
//     filteredItems = filteredItems.filter(d => d.status === 'uploading' || d.status === 'pending');
//   } else if (activeFilter === 'failed') {
//     filteredItems = filteredItems.filter(d => d.status === 'error');
//   }

//   // Apply sort
//   const sortedItems = [...filteredItems].sort((a, b) => {
//     switch (sortBy) {
//       case 'oldest':
//         return new Date(a.uploaded_at || 0) - new Date(b.uploaded_at || 0);
//       case 'alpha':
//         return (a.filename || '').localeCompare(b.filename || '');
//       case 'size':
//         return parseFloat(b.size_mb || 0) - parseFloat(a.size_mb || 0);
//       case 'newest':
//       default:
//         return new Date(b.uploaded_at || 0) - new Date(a.uploaded_at || 0);
//     }
//   });

//   const hasPendingUploads = uploadQueue.some(f => f.status === 'pending');
//   const showEmptyState = sortedItems.length === 0 && !loading;

//   return (
//     <Box sx={{ display: 'flex', height: 'calc(100vh - 120px)', width: '100%', gap: 2 }}>

//       {/* LEFT PANEL: Knowledge Repository */}
//       <LeftPanel
//         documentCount={allItems.length}
//         activeFilter={activeFilter}
//         onFilterChange={setActiveFilter}
//       />

//       {/* CENTER PANEL: Main Document Workspace */}
//       <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

//         {/* Toolbar with Search, Filters, Sort, View Toggle, Upload */}
//         <DocumentToolbar
//           searchQuery={searchQuery}
//           onSearchChange={setSearchQuery}
//           activeFilter={activeFilter}
//           onFilterChange={setActiveFilter}
//           sortBy={sortBy}
//           onSortChange={setSortBy}
//           viewMode={viewMode}
//           onViewModeChange={setViewMode}
//           hasPendingUploads={hasPendingUploads}
//           onUploadAll={handleUploadAll}
//           onUploadClick={open}
//         />

//         {/* Upload Dropzone */}
//         <UploadDropzone
//           getRootProps={getRootProps}
//           getInputProps={getInputProps}
//           isDragActive={isDragActive}
//           hasDocuments={sortedItems.length > 0}
//         />

//         {/* Always-mounted hidden file input — required for open() to work when dropzone is conditional */}
//         {/* The dropzone input unmounts when documents exist, so this permanent input ensures the file picker opens */}
//         <input {...getInputProps()} style={{ display: 'none' }} />

//         {/* Document Grid/List or Empty State */}
//         <Box sx={{ flex: 1, overflowY: 'auto' }}>
//           <AnimatePresence mode="wait">
//             {showEmptyState ? (
//               <EmptyState
//                 key="empty"
//                 onClickUpload={() => document.querySelector('input[type="file"]')?.click()}
//               />
//             ) : (
//               <DocumentGrid
//                 key="grid"
//                 documents={sortedItems}
//                 viewMode={viewMode}
//                 selectedDoc={selectedDoc}
//                 onSelect={setSelectedDoc}
//                 onRemoveUpload={removeUpload}
//                 isLoading={loading}
//               />
//             )}
//           </AnimatePresence>
//         </Box>
//       </Box>

//       {/* RIGHT PANEL: Document Intelligence Inspector */}
//       <InspectorPanel
//         selectedDoc={selectedDoc}
//         onClose={() => setSelectedDoc(null)}
//         darkMode={darkMode}
//       />

//     </Box>
//   );
// };

// export default DocumentUpload;


import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Alert,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  Tooltip,
  Collapse
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';

const DocumentUpload = ({ darkMode }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState([]);

  // ─── Fetch existing documents on mount ──────────────────────────────
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/documents');
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      } else {
        console.error('Failed to fetch documents');
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  // ─── Dropzone logic ───────────────────────────────────────────────────
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      setError(`${rejectedFiles.length} file(s) rejected. Please upload PDF or TXT files only.`);
    }

    // Add new files to the queue
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substring(7),
      filename: file.name,
      status: 'pending',
      progress: 0,
      size_mb: (file.size / (1024 * 1024)).toFixed(2),
      uploaded_at: new Date().toISOString(),
      result: null,
      error: null
    }));

    setFiles(prev => [...prev, ...newFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt']
    },
    maxSize: 16 * 1024 * 1024, // 16MB
    noClick: true, // We'll handle click manually
    noKeyboard: true
  });

  // ─── Upload single file ──────────────────────────────────────────────
  const uploadFile = async (fileItem) => {
    const formData = new FormData();
    formData.append('file', fileItem.file);

    // Update status to uploading
    setFiles(prev => prev.map(f =>
      f.id === fileItem.id ? { ...f, status: 'uploading', progress: 30 } : f
    ));

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        // Update to completed
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id ? {
            ...f,
            status: 'completed',
            progress: 100,
            result: data
          } : f
        ));

        setSuccess(`Successfully processed ${fileItem.file.name}`);
        setTimeout(() => setSuccess(null), 5000);

        // Refresh document list
        fetchDocuments();
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      setFiles(prev => prev.map(f =>
        f.id === fileItem.id ? { ...f, status: 'error', error: error.message } : f
      ));
      setError(`Failed to upload ${fileItem.file.name}: ${error.message}`);
    }
  };

  // ─── Upload all pending files ────────────────────────────────────────
  const handleUploadAll = async () => {
    setUploading(true);
    setError(null);

    const pendingFiles = files.filter(f => f.status === 'pending');

    for (const file of pendingFiles) {
      await uploadFile(file);
    }

    setUploading(false);
  };

  // ─── Remove file from queue ──────────────────────────────────────────
  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  // ─── Clear completed files ───────────────────────────────────────────
  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status !== 'completed'));
  };

  // ─── Helper functions ────────────────────────────────────────────────
  const getFileIcon = (filename) => {
    if (filename?.endsWith('.pdf')) return <PictureAsPdfIcon color="error" />;
    if (filename?.endsWith('.txt')) return <TextSnippetIcon color="primary" />;
    return <DescriptionIcon />;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'error': return 'error';
      case 'uploading': return 'warning';
      default: return 'default';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed': return 'Done';
      case 'error': return 'Failed';
      case 'uploading': return 'Processing';
      case 'pending': return 'Pending';
      default: return status || 'Unknown';
    }
  };

  // ─── Combined file list (upload queue + existing documents) ──────────
  const allFiles = [
    ...files,
    ...documents.map(doc => ({
      id: doc.id || `doc_${doc.filename}`,
      filename: doc.filename,
      status: 'completed',
      progress: 100,
      size_mb: doc.size_mb || '0.00',
      uploaded_at: doc.uploaded_at || new Date().toISOString(),
      result: {
        chunks: doc.chunks || 0,
        entities_found: doc.entities_found || 0,
        relationships_found: doc.relationships_found || 0,
        processing_time_seconds: doc.processing_time_seconds || 0
      },
      isExisting: true
    }))
  ];

  // Remove duplicates (upload queue files that have already been uploaded)
  const uniqueFiles = allFiles.filter((file, index, self) =>
    index === self.findIndex(f =>
      f.filename === file.filename && f.status === 'completed'
    )
  );

  const hasPendingUploads = files.some(f => f.status === 'pending');
  const hasUploadQueue = files.length > 0;

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {/* ─── Dropzone ──────────────────────────────────────────────── */}
          <Paper
            {...getRootProps()}
            onClick={open}
            sx={{
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive
                ? (darkMode ? '#1e3a5f' : '#e3f2fd')
                : (darkMode ? '#1e1e1e' : '#fafafa'),
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'divider',
              borderRadius: 3,
              mb: 3,
              transition: 'all 0.3s ease',
              '&:hover': {
                borderColor: 'primary.main',
                backgroundColor: darkMode ? '#2d2d2d' : '#f5f5f5'
              }
            }}
          >
            <input {...getInputProps()} style={{ display: 'none' }} />
            <CloudUploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              {isDragActive ? 'Drop files here' : 'Upload Documents'}
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              Drag & drop files here, or click to select
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', mt: 2 }}>
              <Chip label="PDF" icon={<PictureAsPdfIcon />} variant="outlined" />
              <Chip label="TXT" icon={<TextSnippetIcon />} variant="outlined" />
              <Chip label="Max 16MB" variant="outlined" />
            </Box>
          </Paper>

          {/* ─── Alerts ────────────────────────────────────────────────── */}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
              {success}
            </Alert>
          )}

          {/* ─── File List ────────────────────────────────────────────── */}
          {(uniqueFiles.length > 0 || loading) && (
            <Paper sx={{ p: 2, borderRadius: 3 }}>
              <Box sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2
              }}>
                <Typography variant="h6">
                  Files ({uniqueFiles.length})
                </Typography>
                <Box>
                  {hasUploadQueue && (
                    <Button
                      onClick={clearCompleted}
                      disabled={uploading}
                      sx={{ mr: 1 }}
                      size="small"
                    >
                      Clear Completed
                    </Button>
                  )}
                  {hasPendingUploads && (
                    <Button
                      variant="contained"
                      onClick={handleUploadAll}
                      disabled={uploading}
                      startIcon={<CloudUploadIcon />}
                    >
                      {uploading ? 'Processing...' : 'Upload All'}
                    </Button>
                  )}
                </Box>
              </Box>

              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <LinearProgress sx={{ width: '100%' }} />
                </Box>
              ) : uniqueFiles.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    No documents yet. Upload your first document to get started.
                  </Typography>
                </Box>
              ) : (
                <List>
                  {uniqueFiles.map((fileItem, index) => (
                    <Card
                      key={fileItem.id || index}
                      variant="outlined"
                      sx={{ mb: 1, borderRadius: 2 }}
                    >
                      <ListItem>
                        <ListItemIcon>
                          {getFileIcon(fileItem.filename)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                                {fileItem.filename}
                              </Typography>
                              <Chip
                                label={getStatusLabel(fileItem.status)}
                                size="small"
                                color={getStatusColor(fileItem.status)}
                              />
                              {fileItem.isExisting && (
                                <Chip
                                  label="Saved"
                                  size="small"
                                  variant="outlined"
                                  color="info"
                                  sx={{ fontSize: '0.65rem' }}
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              {fileItem.size_mb && (
                                <Typography variant="caption" display="block">
                                  Size: {fileItem.size_mb} MB
                                </Typography>
                              )}
                              {fileItem.uploaded_at && (
                                <Typography variant="caption" display="block" color="text.secondary">
                                  Uploaded: {new Date(fileItem.uploaded_at).toLocaleString()}
                                </Typography>
                              )}
                              {fileItem.status === 'completed' && fileItem.result && (
                                <>
                                  <Typography variant="caption" display="block" color="success.main">
                                    ✓ Chunks: {fileItem.result.chunks || 0} |
                                    Entities: {fileItem.result.entities_found || 0} |
                                    Relationships: {fileItem.result.relationships_found || 0}
                                  </Typography>
                                  {fileItem.result.processing_time_seconds && (
                                    <Typography variant="caption" display="block" color="text.secondary">
                                      Processing time: {fileItem.result.processing_time_seconds}s
                                    </Typography>
                                  )}
                                </>
                              )}
                              {fileItem.status === 'error' && (
                                <Typography variant="caption" display="block" color="error">
                                  Error: {fileItem.error}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {fileItem.status === 'uploading' && (
                            <Box sx={{ width: 100, mr: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={fileItem.progress || 0}
                              />
                            </Box>
                          )}
                          {fileItem.status === 'completed' && !fileItem.isExisting && (
                            <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                          )}
                          {fileItem.status === 'error' && (
                            <ErrorIcon color="error" sx={{ mr: 1 }} />
                          )}
                          {fileItem.status !== 'uploading' && !fileItem.isExisting && (
                            <Tooltip title="Remove">
                              <IconButton
                                size="small"
                                onClick={() => removeFile(fileItem.id)}
                                disabled={uploading}
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </ListItem>
                    </Card>
                  ))}
                </List>
              )}
            </Paper>
          )}
        </Grid>

        {/* ─── Info Panel ────────────────────────────────────────────────── */}
        <Grid item xs={12} md={4}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <InfoIcon sx={{ mr: 1 }} color="primary" />
                <Typography variant="h6">Information</Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" paragraph>
                Upload PDF or TXT documents to build your knowledge base.
                The system will:
              </Typography>

              <List dense>
                <ListItem>
                  <ListItemText
                    primary="📄 Extract text content"
                    secondary="Automatically processes PDF and text files"
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="🔍 Create semantic embeddings"
                    secondary="Enable intelligent similarity search"
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="🕸️ Build knowledge graph"
                    secondary="Extract entities and relationships"
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="💬 Enable Q&A"
                    secondary="Ask questions about your documents"
                  />
                </ListItem>
              </List>

              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Tip:</strong> Upload multiple documents to create a comprehensive knowledge base.
                  The system will automatically link related information across documents.
                </Typography>
              </Alert>

              {files.length > 0 && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    <strong>{files.length}</strong> file(s) in upload queue.
                    {hasPendingUploads && ` ${files.filter(f => f.status === 'pending').length} pending.`}
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DocumentUpload;