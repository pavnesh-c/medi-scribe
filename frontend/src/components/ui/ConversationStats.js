'use client'

import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material'

export default function ConversationStats({ stats }) {
  if (!stats) {
    return (
      <Paper elevation={2} sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Conversation Stats
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No statistics available
        </Typography>
      </Paper>
    )
  }

  const formatTime = (isoString) => {
    if (!isoString) return 'N/A'
    return new Date(isoString).toLocaleTimeString()
  }

  const duration = stats.start_time
    ? Math.floor((new Date() - new Date(stats.start_time)) / 1000)
    : 0

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Conversation Stats
      </Typography>
      <List>
        <ListItem>
          <ListItemText
            primary="Status"
            secondary={stats.is_active ? 'Active' : 'Ended'}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Start Time"
            secondary={formatTime(stats.start_time)}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Duration"
            secondary={formatDuration(duration)}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Total Utterances"
            secondary={stats.total_utterances}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Current Buffer"
            secondary={`${stats.current_buffer_size} utterances`}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Total Summaries"
            secondary={stats.total_summaries}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Last Summary"
            secondary={formatTime(stats.last_summary_time)}
          />
        </ListItem>
      </List>
    </Paper>
  )
} 