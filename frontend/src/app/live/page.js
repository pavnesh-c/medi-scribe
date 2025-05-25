'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Box,
  Container,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Paper
} from '@mui/material'
import LiveConversation from '@/components/ui/LiveConversation'
import ConversationStats from '@/components/ui/ConversationStats'

export default function LivePage() {
  const [conversationId, setConversationId] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const router = useRouter()

  const startConversation = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch('http://127.0.0.1:5000/api/v1/live-conversation/start', {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to start conversation')
      }

      const data = await response.json()
      setConversationId(data.conversation_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const endConversation = async () => {
    if (!conversationId) return

    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`http://127.0.0.1:5000/api/v1/live-conversation/${conversationId}/end`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error('Failed to end conversation')
      }

      const data = await response.json()
      router.push(`/soap-note/${data.soap_note.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const updateStats = async () => {
    if (!conversationId) return

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/v1/live-conversation/${conversationId}/stats`)
      if (!response.ok) {
        throw new Error('Failed to fetch stats')
      }
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to update stats:', err)
    }
  }

  useEffect(() => {
    if (conversationId) {
      const interval = setInterval(updateStats, 5000)
      return () => clearInterval(interval)
    }
  }, [conversationId])

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'white' }}>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h1" component="h1" gutterBottom color="primary">
            Live Conversation
          </Typography>
          <Typography variant="h6" color="textSecondary" gutterBottom>
            Start a new medical consultation
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!conversationId ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={startConversation}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Start New Conversation'}
            </Button>
          </Box>
        ) : (
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <LiveConversation
                conversationId={conversationId}
                onError={setError}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <ConversationStats stats={stats} />
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Button
                  variant="contained"
                  color="error"
                  onClick={endConversation}
                  disabled={loading}
                >
                  {loading ? <CircularProgress size={24} /> : 'End Conversation'}
                </Button>
              </Box>
            </Grid>
          </Grid>
        )}
      </Container>
    </Box>
  )
} 