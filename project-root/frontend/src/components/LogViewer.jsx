import React, { useEffect, useRef } from 'react'
import { Box, Paper, Typography } from '@mui/material'

const LogViewer = ({ logs }) => {
  const logEndRef = useRef(null)

  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [logs])

  const getColorByType = (type) => {
    switch (type) {
      case 'error': return '#f44336'
      case 'success': return '#4caf50'
      case 'warning': return '#ff9800'
      case 'info': return '#2196f3'
      default: return '#757575'
    }
  }

  const getIconByType = (type) => {
    switch (type) {
      case 'error': return '❌'
      case 'success': return '✅'
      case 'warning': return '⚠️'
      case 'info': return 'ℹ️'
      default: return '📝'
    }
  }

  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        backgroundColor: '#1e1e1e',
        color: '#ffffff',
        fontFamily: 'Monaco, monospace',
        fontSize: '0.875rem',
        height: '400px',
        overflow: 'auto',
        whiteSpace: 'pre-wrap'
      }}
    >
      {logs.length === 0 ? (
        <Typography 
          sx={{ 
            fontStyle: 'italic',
            color: '#ffffff' 
          }}
        >
          Логи будут отображаться здесь...
        </Typography>
      ) : (
        logs.map((log, index) => (
          <Box
            key={index}
            sx={{
              mb: 0.5,
              borderLeft: `3px solid ${getColorByType(log.type)}`,
              pl: 1
            }}
          >
            <span style={{ color: getColorByType(log.type), marginRight: 8 }}>
              {getIconByType(log.type)}
            </span>
            <span style={{ color: '#ffffff' }}>
              {log.message}
            </span>
          </Box>
        ))
      )}
      <div ref={logEndRef} />
    </Paper>
  )
}

export default LogViewer