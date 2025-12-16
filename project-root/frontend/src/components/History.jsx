import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  IconButton,
  Tooltip,
  Button,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import {
  History as HistoryIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Folder as FolderIcon,
  PlayArrow as PlayIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon
} from '@mui/icons-material'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

function History({ isOpen, onClose }) {
  const [history, setHistory] = useState([])
  const [selectedLogs, setSelectedLogs] = useState([])
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = () => {
    try {
      const storedHistory = localStorage.getItem('fileProcessorHistory')
      if (storedHistory) {
        setHistory(JSON.parse(storedHistory))
      }
    } catch (error) {
      console.error('Ошибка загрузки истории:', error)
    }
  }

  const clearHistory = () => {
    if (window.confirm('Вы уверены, что хотите очистить всю историю?')) {
      localStorage.removeItem('fileProcessorHistory')
      setHistory([])
    }
  }

  const deleteItem = (id) => {
    const newHistory = history.filter(item => item.id !== id)
    setHistory(newHistory)
    localStorage.setItem('fileProcessorHistory', JSON.stringify(newHistory))
  }

  const viewLogs = (logs) => {
    setSelectedLogs(logs)
    setViewDialogOpen(true)
  }

  const exportHistory = () => {
    const dataStr = JSON.stringify(history, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `история_обработки_${dayjs().format('YYYY-MM-DD_HH-mm')}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const formatDuration = (start, end) => {
    if (!start || !end) return 'Н/Д'
    const duration = dayjs(end).diff(dayjs(start), 'second')
    if (duration < 60) return `${duration} сек`
    return `${Math.floor(duration / 60)} мин ${duration % 60} сек`
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <SuccessIcon color="success" />
      case 'failed': return <ErrorIcon color="error" />
      case 'running': return <PlayIcon color="primary" />
      default: return <InfoIcon color="info" />
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return 'Завершено'
      case 'failed': return 'Ошибка'
      case 'running': return 'Выполняется'
      default: return 'Неизвестно'
    }
  }

  const getTypeText = (type) => {
    switch (type) {
      case 'find-broken': return 'Поиск битых файлов'
      case 'parse': return 'Парсинг файлов'
      default: return type
    }
  }

  const filteredHistory = history.filter(item => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      item.folderName?.toLowerCase().includes(search) ||
      item.taskId?.toLowerCase().includes(search) ||
      getTypeText(item.type)?.toLowerCase().includes(search) ||
      item.status?.toLowerCase().includes(search)
    )
  })

  return (
    <Dialog open={isOpen} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <HistoryIcon />
            <Typography variant="h6">История обработки</Typography>
            <Badge badgeContent={history.length} color="primary" showZero>
              <Chip label={`Всего: ${history.length}`} size="small" variant="outlined" />
            </Badge>
          </Box>
          <Box display="flex" gap={1}>
            <Button
              startIcon={<RefreshIcon />}
              onClick={loadHistory}
              size="small"
            >
              Обновить
            </Button>
            <Button
              startIcon={<DownloadIcon />}
              onClick={exportHistory}
              size="small"
              variant="outlined"
            >
              Экспорт
            </Button>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Box mb={2}>
          <TextField
            fullWidth
            placeholder="Поиск по истории..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            size="small"
            sx={{ mb: 2 }}
          />
          
          {history.length === 0 ? (
            <Alert severity="info">
              История пуста. Запустите обработку файлов, чтобы увидеть историю здесь.
            </Alert>
          ) : filteredHistory.length === 0 ? (
            <Alert severity="warning">
              По вашему запросу ничего не найдено.
            </Alert>
          ) : (
            <List>
              {filteredHistory.map((item) => (
                <React.Fragment key={item.id}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box display="flex" alignItems="center" width="100%">
                        <Box flex={1}>
                          <ListItemText
                            primary={
                              <Box display="flex" alignItems="center" gap={1}>
                                {getStatusIcon(item.status)}
                                <Typography variant="subtitle1">
                                  {getTypeText(item.type)}
                                </Typography>
                                <Chip
                                  label={getStatusText(item.status)}
                                  size="small"
                                  color={
                                    item.status === 'completed' ? 'success' :
                                    item.status === 'failed' ? 'error' : 'primary'
                                  }
                                />
                              </Box>
                            }
                            secondary={
                              <Box display="flex" alignItems="center" gap={2} mt={0.5}>
                                <Typography variant="body2" color="text.secondary">
                                  <FolderIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                                  {item.folderName || 'Не указано'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  📅 {dayjs(item.startTime).format('DD.MM.YYYY HH:mm')}
                                </Typography>
                                {item.duration && (
                                  <Typography variant="body2" color="text.secondary">
                                    ⏱️ {item.duration}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </Box>
                        <Box>
                          <Tooltip title="Просмотреть логи">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation()
                                viewLogs(item.logs || [])
                              }}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Удалить из истории">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteItem(item.id)
                              }}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>ID задачи:</strong> {item.taskId}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Путь:</strong> {item.path}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Время начала:</strong> {dayjs(item.startTime).format('DD.MM.YYYY HH:mm:ss')}
                        </Typography>
                        {item.endTime && (
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            <strong>Время завершения:</strong> {dayjs(item.endTime).format('DD.MM.YYYY HH:mm:ss')}
                          </Typography>
                        )}
                        {item.result && (
                          <Box mt={1}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Результат:</strong>
                            </Typography>
                            <Paper variant="outlined" sx={{ p: 1, mt: 0.5, bgcolor: 'grey.50' }}>
                              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                                {JSON.stringify(item.result, null, 2)}
                              </Typography>
                            </Paper>
                          </Box>
                        )}
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={clearHistory} color="error" startIcon={<DeleteIcon />}>
          Очистить историю
        </Button>
        <Button onClick={onClose}>Закрыть</Button>
      </DialogActions>

      {/* Диалог просмотра логов */}
      <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Логи обработки</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ maxHeight: '60vh', overflow: 'auto' }}>
            {selectedLogs.length === 0 ? (
              <Alert severity="info">Логи отсутствуют</Alert>
            ) : (
              <List dense>
                {selectedLogs.map((log, index) => (
                  <ListItem key={index} sx={{ py: 0.5 }}>
                    <ListItemText
                      primary={
                        <Typography
                          variant="body2"
                          sx={{
                            color: log.type === 'error' ? 'error.main' :
                                   log.type === 'success' ? 'success.main' :
                                   log.type === 'warning' ? 'warning.main' : 'text.primary',
                            fontFamily: 'monospace',
                            fontSize: '0.85rem'
                          }}
                        >
                          {log.message}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>Закрыть</Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  )
}

export default History