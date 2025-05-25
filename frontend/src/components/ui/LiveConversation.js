'use client'

import React, { useState, useEffect, useRef } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material'
import MicIcon from '@mui/icons-material/Mic'
import StopIcon from '@mui/icons-material/Stop'
import PauseIcon from '@mui/icons-material/Pause'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import { API_ENDPOINTS } from '@/constants/api'

export default function LiveConversation({ conversationId, onError }) {
  const [utterances, setUtterances] = useState([])
  const [isRecording, setIsRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [summaries, setSummaries] = useState([])
  const [audioLevel, setAudioLevel] = useState(0)
  const [debugInfo, setDebugInfo] = useState('')
  const [previewUrl, setPreviewUrl] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [availableMics, setAvailableMics] = useState([])
  const [selectedMic, setSelectedMic] = useState('')

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  const conversationEndRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const audioPlayerRef = useRef(null)

  const scrollToBottom = () => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [utterances])

  // Get available microphones
  const getMicrophones = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const mics = devices.filter(device => device.kind === 'audioinput')
      setAvailableMics(mics)
      if (mics.length > 0) {
        setSelectedMic(mics[0].deviceId)
      }
      setDebugInfo(`Found ${mics.length} microphones`)
    } catch (err) {
      setDebugInfo(`Error getting microphones: ${err.message}`)
    }
  }

  // Get microphones when component mounts
  useEffect(() => {
    getMicrophones()
  }, [])

  const startRecording = async () => {
    try {
      if (!selectedMic) {
        throw new Error('No microphone selected')
      }

      setDebugInfo('Requesting microphone access...')
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: selectedMic },
          channelCount: 1,
          sampleRate: 48000,
          sampleSize: 16,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          volume: 1.0,
          latency: 0,
          googEchoCancellation: true,
          googAutoGainControl: true,
          googNoiseSuppression: true,
          googHighpassFilter: true
        }
      })
      streamRef.current = stream
      setDebugInfo('Microphone access granted')

      // Set up audio analysis with gain
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)

      // Add gain node to boost the signal
      const gainNode = audioContextRef.current.createGain()
      gainNode.gain.value = 2.0 // Boost the signal by 2x

      // Connect the nodes: source -> gain -> analyser
      source.connect(gainNode)
      gainNode.connect(analyserRef.current)

      analyserRef.current.fftSize = 256
      analyserRef.current.smoothingTimeConstant = 0.8

      // Start monitoring audio levels with enhanced sensitivity
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
      const updateLevel = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray)
          // Calculate RMS value for better level representation
          const rms = Math.sqrt(dataArray.reduce((acc, val) => acc + (val * val), 0) / dataArray.length)
          // Scale the value to be more sensitive
          const scaledLevel = Math.min(100, (rms / 128) * 100)
          setAudioLevel(scaledLevel)
          requestAnimationFrame(updateLevel)
        }
      }
      updateLevel()

      // Check available MIME types
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4'
      ]
      const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type))
      setDebugInfo(`Supported MIME type: ${supportedMimeType || 'None'}`)

      if (!supportedMimeType) {
        throw new Error('No supported audio MIME types found')
      }

      // Clear any previous chunks
      audioChunksRef.current = []

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: supportedMimeType,
        audioBitsPerSecond: 128000
      })
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
          setDebugInfo(`Received audio chunk: ${event.data.size} bytes`)
        }
      }

      mediaRecorder.onstop = async () => {
        // Process the current chunk
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: supportedMimeType })
          setDebugInfo(`Processing audio chunk: ${audioBlob.size} bytes`)
          await processAudioChunk(audioBlob)
        }

        // Restart recording if still active
        if (isRecording) {
          audioChunksRef.current = []
          mediaRecorder.start(5000)
        }
      }

      // Record in 5-second chunks
      mediaRecorder.start(5000)
      setIsRecording(true)
      setDebugInfo('Recording started')
    } catch (err) {
      setDebugInfo(`Error: ${err.message}`)
      onError('Failed to access microphone: ' + err.message)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      streamRef.current?.getTracks().forEach(track => track.stop())
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      setIsRecording(false)
      setAudioLevel(0)
      setDebugInfo('Recording stopped')

      if (audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm;codecs=opus' })
        const url = URL.createObjectURL(audioBlob)
        setPreviewUrl(url)
        setDebugInfo(`Created preview with ${audioChunksRef.current.length} chunks`)
      } else {
        setDebugInfo('No audio chunks recorded')
      }
    }
  }

  const togglePreview = () => {
    if (audioPlayerRef.current) {
      if (isPlaying) {
        audioPlayerRef.current.pause()
      } else {
        audioPlayerRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const processAudioChunk = async (audioBlob) => {
    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('audio', audioBlob)

      const response = await fetch(API_ENDPOINTS.LIVE_CONVERSATION.UTTERANCE(conversationId), {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Failed to process audio chunk')
      }

      const data = await response.json()

      if (data.utterance_processed) {
        setUtterances(prev => [...prev, {
          speaker: data.speaker,
          text: data.transcription,
          timestamp: new Date().toISOString()
        }])

        if (data.summary) {
          setSummaries(prev => [...prev, data.summary])
        }
      }
    } catch (err) {
      onError('Failed to process audio: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Live Conversation</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {!isRecording && (
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel>Select Microphone</InputLabel>
                <Select
                  value={selectedMic}
                  onChange={(e) => setSelectedMic(e.target.value)}
                  label="Select Microphone"
                >
                  {availableMics.map((mic) => (
                    <MenuItem key={mic.deviceId} value={mic.deviceId}>
                      {mic.label || `Microphone ${mic.deviceId.slice(0, 5)}...`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {!isRecording ? (
              <Button
                variant="contained"
                color="primary"
                startIcon={<MicIcon />}
                onClick={startRecording}
                disabled={loading || !selectedMic}
              >
                Start Listening
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                startIcon={<StopIcon />}
                onClick={stopRecording}
                disabled={loading}
              >
                Stop Listening
              </Button>
            )}
          </Box>
        </Box>

        {previewUrl && (
          <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Recording Preview
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={togglePreview}
                startIcon={isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
              >
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <audio
                ref={audioPlayerRef}
                src={previewUrl}
                onEnded={() => setIsPlaying(false)}
                style={{ display: 'none' }}
              />
            </Box>
          </Box>
        )}

        {isRecording && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" display="block" gutterBottom>
              Audio Level: {Math.round(audioLevel)}%
            </Typography>
            <Box sx={{
              width: '100%',
              height: '20px',
              bgcolor: 'grey.200',
              borderRadius: 1,
              overflow: 'hidden'
            }}>
              <Box sx={{
                width: `${audioLevel}%`,
                height: '100%',
                bgcolor: 'primary.main',
                transition: 'width 0.1s ease-in-out'
              }} />
            </Box>
          </Box>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
          {debugInfo}
        </Typography>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
            <CircularProgress />
          </Box>
        )}

        <Box sx={{ maxHeight: '400px', overflow: 'auto', mb: 2 }}>
          <List>
            {utterances.map((utterance, index) => (
              <ListItem key={index} alignItems="flex-start">
                <ListItemText
                  primary={`${utterance.speaker} (${new Date(utterance.timestamp).toLocaleTimeString()})`}
                  secondary={utterance.text}
                />
              </ListItem>
            ))}
            <div ref={conversationEndRef} />
          </List>
        </Box>

        {summaries.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Recent Summaries
            </Typography>
            <List>
              {summaries.slice(-3).map((summary, index) => (
                <ListItem key={index}>
                  <ListItemText secondary={summary} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Paper>
    </Box>
  )
} 