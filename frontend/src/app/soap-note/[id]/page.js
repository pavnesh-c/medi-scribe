'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material'

export default function SOAPNoteView() {
  const [soapNote, setSoapNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { id } = useParams()

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
      setSoapNote(data.soap_note)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  if (!soapNote) {
    return (
      <Box p={3}>
        <Alert severity="warning">SOAP note not found</Alert>
      </Box>
    )
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        SOAP Note #{id}
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Box mb={3}>
          <Typography variant="h6" color="primary" gutterBottom>
            Subjective
          </Typography>
          <Typography variant="body1" paragraph>
            {soapNote.subjective}
          </Typography>
        </Box>
        <Divider />
        <Box my={3}>
          <Typography variant="h6" color="primary" gutterBottom>
            Objective
          </Typography>
          <Typography variant="body1" paragraph>
            {soapNote.objective}
          </Typography>
        </Box>
        <Divider />
        <Box my={3}>
          <Typography variant="h6" color="primary" gutterBottom>
            Assessment
          </Typography>
          <Typography variant="body1" paragraph>
            {soapNote.assessment}
          </Typography>
        </Box>
        <Divider />
        <Box mt={3}>
          <Typography variant="h6" color="primary" gutterBottom>
            Plan
          </Typography>
          <Typography variant="body1">
            {soapNote.plan}
          </Typography>
        </Box>
      </Paper>
    </Box>
  )
} 