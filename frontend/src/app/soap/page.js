'use client'

import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  Button,
  CircularProgress,
  Alert
} from '@mui/material'
import { useRouter } from 'next/navigation'

export default function SOAPNotesList() {
  const [soapNotes, setSoapNotes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const router = useRouter()

  useEffect(() => {
    fetchSOAPNotes()
  }, [])

  const fetchSOAPNotes = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/v1/soap-note')
      if (!response.ok) {
        throw new Error('Failed to fetch SOAP notes')
      }
      const data = await response.json()
      if (data.status === 'ok' && Array.isArray(data.soap_notes)) {
        setSoapNotes(data.soap_notes)
      } else {
        throw new Error('Invalid response format')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
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
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          SOAP Notes
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={() => router.push('/')}
        >
          New Recording
        </Button>
      </Box>

      {soapNotes.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="textSecondary">
            No SOAP notes found. Create one by uploading or recording a consultation.
          </Typography>
        </Paper>
      ) : (
        <Paper>
          <List>
            {soapNotes.map((note) => (
              <ListItem
                key={note.id}
                button
                onClick={() => router.push(`/soap/${note.id}`)}
                divider
              >
                <ListItemText
                  primary={`SOAP Note #${note.id}`}
                  secondary={`Created: ${new Date(note.created_at).toLocaleString()}`}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Container>
  )
} 