'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Box,
  Button,
  Typography,
  Paper,
  Tabs,
  Tab,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Grid
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import MicIcon from '@mui/icons-material/Mic'
import StopIcon from '@mui/icons-material/Stop'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import ChatIcon from '@mui/icons-material/Chat'
import { useRouter } from 'next/navigation'
import LiveConversation from '@/components/ui/LiveConversation'
import ConversationStats from '@/components/ui/ConversationStats'
import { API_ENDPOINTS } from '@/constants/api'

export default function UploadRecord({ isProcessing, setIsProcessing, setProcessingStatus }) {
  const [activeTab, setActiveTab] = useState(0)
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const [stats, setStats] = useState(null)
  const fileInputRef = useRef(null)
  const router = useRouter()

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue)
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type.startsWith('audio/')) {
      setFile(selectedFile)
    }
  }

  const handleContainerClick = () => {
    fileInputRef.current?.click()
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('audio/')) {
      setFile(droppedFile)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Initialize upload session
      const chunkSize = 1024 * 1024; // 1MB chunks
      const totalChunks = Math.ceil(file.size / chunkSize);

      const initResponse = await fetch(API_ENDPOINTS.UPLOAD.INIT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          total_chunks: totalChunks,
          chunk_size: file.size,
        }),
      });

      if (!initResponse.ok) {
        throw new Error('Failed to initialize upload');
      }

      const { session_id } = await initResponse.json();

      // Upload file in chunks
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('file', chunk);
        formData.append('session_id', session_id);
        formData.append('chunk_index', chunkIndex);

        const uploadResponse = await fetch(API_ENDPOINTS.UPLOAD.CHUNK, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          throw new Error(`Failed to upload chunk ${chunkIndex + 1}`);
        }
      }

      // Finish upload and process
      const finishResponse = await fetch(API_ENDPOINTS.UPLOAD.FINISH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id,
          filename: file.name,
        }),
      });

      if (!finishResponse.ok) {
        throw new Error('Failed to finish upload');
      }

      const { soap_note_id } = await finishResponse.json();
      setIsProcessing(false);

      // Redirect to SOAP note page
      window.location.href = `/soap-note/${soap_note_id}`;
    } catch (err) {
      console.error('Error:', err);
      setError(err.message);
      setIsProcessing(false);
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper elevation={2} sx={{ p: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange} centered>
          <Tab icon={<CloudUploadIcon />} label="Upload" />
          <Tab icon={<MicIcon />} label="Live" />
        </Tabs>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {activeTab === 0 && (
          <Paper
            onClick={handleContainerClick}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            sx={{
              p: 3,
              textAlign: 'center',
              cursor: 'pointer',
              border: '2px dashed #ccc',
              '&:hover': {
                borderColor: 'primary.main',
              },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drag and drop an audio file here
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              or click to select a file
            </Typography>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="audio/*"
              style={{ display: 'none' }}
            />
            {file && (
              <Typography variant="body2" sx={{ mt: 2 }}>
                Selected file: {file.name}
              </Typography>
            )}
            <Box sx={{ mt: 3 }}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSubmit}
                disabled={!file || isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Process Audio'}
              </Button>
            </Box>
          </Paper>
        )}

        {activeTab === 1 && (
          <LiveConversation
            conversationId={conversationId}
            onError={setError}
          />
        )}
      </Paper>
    </Box>
  )
} 