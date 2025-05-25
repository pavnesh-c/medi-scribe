'use client'

import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert
} from '@mui/material'
import { useParams, useRouter } from 'next/navigation'

export default function SOAPNotePage() {
  const { id } = useParams()
  const router = useRouter()
  const [soapNote, setSoapNote] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)
  const [editedNote, setEditedNote] = useState({
    subjective: '',
    objective: '',
    assessment: '',
    plan: ''
  })

  useEffect(() => {
    fetchSOAPNote()
  }, [id])

  const fetchSOAPNote = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/v1/soap-note/${id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch SOAP note')
      }
      const data = await response.json()
      if (data.status === 'ok' && data.soap_note) {
        setSoapNote(data.soap_note)
        setEditedNote({
          subjective: data.soap_note.subjective || '',
          objective: data.soap_note.objective || '',
          assessment: data.soap_note.assessment || '',
          plan: data.soap_note.plan || ''
        })
      } else {
        throw new Error('Invalid response format')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/v1/soap-note/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editedNote),
      })

      if (!response.ok) {
        throw new Error('Failed to save SOAP note')
      }

      const data = await response.json()
      if (data.status === 'ok') {
        // Refresh the note after saving
        await fetchSOAPNote()
      } else {
        throw new Error('Failed to save SOAP note')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleFieldChange = (field, value) => {
    setEditedNote(prev => ({
      ...prev,
      [field]: value
    }))
  }

  if (isLoading) {
    return (
      <Container maxWidth="md" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    )
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          SOAP Note
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          Patient Consultation Record
        </Typography>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Subjective
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={editedNote.subjective}
            onChange={(e) => handleFieldChange('subjective', e.target.value)}
            variant="outlined"
            placeholder="Patient's reported symptoms and concerns..."
          />
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Objective
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={editedNote.objective}
            onChange={(e) => handleFieldChange('objective', e.target.value)}
            variant="outlined"
            placeholder="Clinical findings, vital signs, and observations..."
          />
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Assessment
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={editedNote.assessment}
            onChange={(e) => handleFieldChange('assessment', e.target.value)}
            variant="outlined"
            placeholder="Diagnosis and clinical impression..."
          />
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Plan
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={editedNote.plan}
            onChange={(e) => handleFieldChange('plan', e.target.value)}
            variant="outlined"
            placeholder="Treatment plan, medications, follow-up..."
          />
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={() => router.push('/soap')}
          >
            Back to List
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Paper>
    </Container>
  )
} 