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
  Alert
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import MicIcon from '@mui/icons-material/Mic'
import StopIcon from '@mui/icons-material/Stop'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'

export default function UploadRecord({ isProcessing, setIsProcessing, setProcessingStatus }) {
  const [activeTab, setActiveTab] = useState(0)
  const [file, setFile] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [showStopDialog, setShowStopDialog] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)
  const audioPlayerRef = useRef(null)
  const MAX_RECORDING_DURATION = 300 // 5 minutes in seconds

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

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

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        const audioUrl = URL.createObjectURL(blob)
        if (audioPlayerRef.current) {
          audioPlayerRef.current.src = audioUrl
        }
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingDuration(0)

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => {
          if (prev >= MAX_RECORDING_DURATION) {
            stopRecording()
            return prev
          }
          return prev + 1
        })
      }, 1000)
    } catch (err) {
      console.error('Error accessing microphone:', err)
      setError('Failed to access microphone. Please ensure you have granted microphone permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      setShowStopDialog(false)
    }
  }

  const handleStopClick = () => {
    setShowStopDialog(true)
  }

  const togglePlayback = () => {
    if (audioPlayerRef.current) {
      if (isPlaying) {
        audioPlayerRef.current.pause()
      } else {
        audioPlayerRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleSubmit = async () => {
    if (!file && !audioBlob) return

    setIsProcessing(true)
    setProcessingStatus('Initializing upload session...')

    try {
      const audioFile = file || new File([audioBlob], 'recording.webm', { type: 'audio/webm' })

      // Initialize upload session
      const sessionResponse = await fetch('http://127.0.0.1:5000/api/v1/upload/init', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: `session_${Date.now()}`,
          file_name: audioFile.name,
          total_size: audioFile.size,
          total_chunks: Math.ceil(audioFile.size / (1024 * 1024)), // 1MB chunks
        }),
      })

      if (!sessionResponse.ok) {
        const errorData = await sessionResponse.json()
        throw new Error(errorData.message || 'Failed to initialize upload session')
      }

      const sessionData = await sessionResponse.json()
      console.log('Session init response:', sessionData)
      const sessionId = sessionData.id
      if (!sessionId) throw new Error('No session_id returned from backend')

      // Upload file in chunks
      setProcessingStatus('Uploading file...')
      const chunkSize = 1024 * 1024 // 1MB chunks
      const totalChunks = Math.ceil(audioFile.size / chunkSize)

      for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
        const start = chunkNumber * chunkSize
        const end = Math.min(start + chunkSize, audioFile.size)
        const chunk = audioFile.slice(start, end)

        const chunkFormData = new FormData()
        chunkFormData.append('session_id', sessionId)
        chunkFormData.append('chunk_number', chunkNumber)
        chunkFormData.append('chunk', chunk)

        const chunkResponse = await fetch('http://127.0.0.1:5000/api/v1/upload/chunk', {
          method: 'POST',
          body: chunkFormData,
        })

        if (!chunkResponse.ok) {
          const errorData = await chunkResponse.json()
          throw new Error(errorData.message || `Failed to upload chunk ${chunkNumber + 1}/${totalChunks}`)
        }

        setProcessingStatus(`Uploading file... ${Math.round(((chunkNumber + 1) / totalChunks) * 100)}%`)
      }

      // Call finish endpoint to combine chunks
      setProcessingStatus('Processing file...')
      const finishResponse = await fetch('http://127.0.0.1:5000/api/v1/upload/finish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      })

      if (!finishResponse.ok) {
        const errorData = await finishResponse.json()
        throw new Error(errorData.message || 'Failed to finish upload and combine chunks')
      }

      const finishData = await finishResponse.json()
      console.log('Finish response:', finishData)
      const recordingId = finishData.recording_id
      if (!recordingId) throw new Error('No recording_id returned from finish endpoint')

      // Start transcription
      setProcessingStatus('Starting transcription...')
      const transcriptionResponse = await fetch(`http://127.0.0.1:5000/api/v1/transcription/start/${recordingId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!transcriptionResponse.ok) {
        const errorData = await transcriptionResponse.json()
        throw new Error(errorData.message || 'Failed to start transcription')
      }

      const transcriptionData = await transcriptionResponse.json()
      const transcriptionId = transcriptionData.transcription_id
      if (!transcriptionId) throw new Error('No transcription_id returned from transcription start endpoint')

      // Poll for transcription completion
      setProcessingStatus('Transcribing audio...')
      let transcriptionCompleted = false
      let attempts = 0
      const maxAttempts = 30

      while (!transcriptionCompleted && attempts < maxAttempts) {
        const statusResponse = await fetch(`http://127.0.0.1:5000/api/v1/transcription/${transcriptionId}`)
        if (!statusResponse.ok) {
          const errorData = await statusResponse.json()
          throw new Error(errorData.message || 'Failed to check transcription status')
        }

        const statusData = await statusResponse.json()
        if (statusData.transcription && statusData.transcription.status === 'completed') {
          transcriptionCompleted = true
        } else if (statusData.transcription && statusData.transcription.status === 'failed') {
          throw new Error('Transcription failed')
        }

        attempts++
        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      if (!transcriptionCompleted) {
        throw new Error('Transcription timed out')
      }

      // Generate SOAP note
      setProcessingStatus('Generating SOAP note...')
      const soapResponse = await fetch(`http://127.0.0.1:5000/api/v1/soap-note/generate/${transcriptionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!soapResponse.ok) {
        const errorData = await soapResponse.json()
        throw new Error(errorData.message || 'Failed to generate SOAP note')
      }

      const soapData = await soapResponse.json()
      window.location.href = `/soap/${soapData.soap_note_id}`

    } catch (err) {
      console.error('Error:', err)
      setProcessingStatus(`Error: ${err.message}`)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <Box>
      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        centered
        sx={{ mb: 3 }}
      >
        <Tab label="Upload File" />
        <Tab label="Record Audio" />
      </Tabs>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
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
        </Paper>
      )}

      {activeTab === 1 && (
        <Box sx={{ textAlign: 'center' }}>
          <IconButton
            color={isRecording ? 'error' : 'primary'}
            onClick={isRecording ? handleStopClick : startRecording}
            sx={{ fontSize: 64 }}
            disabled={isProcessing}
          >
            {isRecording ? <StopIcon fontSize="inherit" /> : <MicIcon fontSize="inherit" />}
          </IconButton>
          <Typography variant="body1" sx={{ mt: 2 }} color={isRecording ? 'error' : 'black'}>
            {isRecording ? `Recording... ${formatTime(recordingDuration)}` : 'Click to start recording'}
          </Typography>
          {audioBlob && (
            <Box sx={{ mt: 2 }}>
              <IconButton onClick={togglePlayback} color="primary">
                {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
              </IconButton>
              <Typography variant="body2">
                {isPlaying ? 'Playing...' : 'Click to preview recording'}
              </Typography>
            </Box>
          )}
          <audio ref={audioPlayerRef} style={{ display: 'none' }} />
        </Box>
      )}

      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSubmit}
          disabled={(!file && !audioBlob) || isProcessing}
          size="large"
        >
          {isProcessing ? 'Processing...' : 'Process Audio'}
        </Button>
      </Box>

      <Dialog
        open={showStopDialog}
        onClose={() => setShowStopDialog(false)}
      >
        <DialogTitle>Stop Recording?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to stop recording? The current recording will be saved.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowStopDialog(false)}>Cancel</Button>
          <Button onClick={stopRecording} color="error">Stop Recording</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
} 