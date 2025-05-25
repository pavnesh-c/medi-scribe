'use client'

import { useState } from 'react'
import { Container, Typography, Box, CircularProgress } from '@mui/material'
import UploadRecord from './components/UploadRecord'

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState('')

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'white' }}>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h1" component="h1" gutterBottom color="primary">
            Medi-Scribe
          </Typography>
          <Typography variant="h6" color="textSecondary" gutterBottom>
            Upload or record your medical consultation
          </Typography>
        </Box>

        <UploadRecord
          isProcessing={isProcessing}
          setIsProcessing={setIsProcessing}
          setProcessingStatus={setProcessingStatus}
        />

        {isProcessing && (
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <CircularProgress sx={{ mb: 2 }} />
            <Typography variant="body1" color="textSecondary">
              {processingStatus}
            </Typography>
          </Box>
        )}
      </Container>
    </Box>
  )
}
