'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  CircularProgress,
  Alert
} from '@mui/material'
import VisibilityIcon from '@mui/icons-material/Visibility'

function SOAPNoteList() {
  const [soapNotes, setSoapNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const router = useRouter()

  useEffect(() => {
    fetchSOAPNotes()
  }, [])

  const fetchSOAPNotes = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/v1/soap-notes')
      if (!response.ok) {
        throw new Error('Failed to fetch SOAP notes')
      }
      const data = await response.json()
      setSoapNotes(data.soap_notes)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleViewNote = (id) => {
    router.push(`/soap-note/${id}`)
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

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        SOAP Notes
      </Typography>
      <Paper>
        <List>
          {soapNotes.length === 0 ? (
            <ListItem>
              <ListItemText primary="No SOAP notes found" />
            </ListItem>
          ) : (
            soapNotes.map((note) => (
              <ListItem key={note.id}>
                <ListItemText
                  primary={`SOAP Note #${note.id}`}
                  secondary={`Created: ${new Date(note.created_at).toLocaleString()}`}
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    aria-label="view"
                    onClick={() => handleViewNote(note.id)}
                  >
                    <VisibilityIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))
          )}
        </List>
      </Paper>
    </Box>
  )
}

export default SOAPNoteList
