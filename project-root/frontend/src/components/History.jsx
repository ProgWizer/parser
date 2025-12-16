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
  AccordionDetails,
  Tab,
  Tabs,
  CircularProgress,
  LinearProgress
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
  Download as DownloadIcon,
  DataObject as DataObjectIcon,
  Description as DescriptionIcon,
  Search as SearchIcon,
  Clear as ClearIcon
} from '@mui/icons-material'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

function History({ isOpen, onClose }) {
  const [history, setHistory] = useState([])
  const [selectedLogs, setSelectedLogs] = useState([])
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTab, setSelectedTab] = useState('all')
  const [loading, setLoading] = useState(false)
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState(null)
  const [selectedTaskName, setSelectedTaskName] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadHistory()
    }
  }, [isOpen])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/history')
      if (response.ok) {
        const data = await response.json()
        console.log('✅ Загружена история с сервера:', data.history.length, 'записей')
        
        // Отладочная информация для первых 3 записей
        data.history.slice(0, 3).forEach((item, index) => {
          console.log(`Запись ${index} структура:`, {
            id: item.id,
            taskId: item.taskId,
            hasLogsField: !!item.logs,
            logsIsArray: Array.isArray(item.logs),
            logsLength: item.logs?.length || 0,
            hasResultField: !!item.result,
            resultHasLogs: !!item.result?.logs,
            type: item.type
          })
        })
        
        setHistory(data.history)
      } else {
        console.warn('Сервер недоступен')
        setHistory([])
      }
    } catch (error) {
      console.error('Ошибка загрузки истории с сервера:', error)
      setHistory([])
    } finally {
      setLoading(false)
    }
  }

  const clearHistory = () => {
    if (window.confirm('Вы уверены, что хотите очистить всю историю на сервере?\nЭто действие нельзя отменить.')) {
      setHistory([])
      alert('История очищена (в демо-режиме)')
    }
  }

  const deleteItem = async (id) => {
    if (window.confirm('Удалить эту запись из истории?')) {
      const newHistory = history.filter(item => item.id !== id)
      setHistory(newHistory)
    }
  }

  const viewLogs = async (item) => {
    console.log('=== ПРОСМОТР ЛОГОВ ===');
    console.log('Задача ID:', item.id || item.taskId);
    console.log('Тип задачи:', item.type);
    console.log('Исходный объект item:', item);
    
    setSelectedTaskId(item.id || item.taskId);
    setSelectedTaskName(item.folderName || 'Неизвестная задача');
    
    // Ищем логи в разных местах объекта истории
    let logsToDisplay = [];
    
    // 1. Пробуем получить логи из item.logs (прямое поле)
    if (item.logs) {
      console.log('🔍 Проверяем item.logs:', item.logs);
      console.log('Тип item.logs:', typeof item.logs);
      console.log('Is array?', Array.isArray(item.logs));
      
      if (Array.isArray(item.logs) && item.logs.length > 0) {
        console.log('✅ Логи найдены в item.logs:', item.logs.length);
        logsToDisplay = item.logs;
      } else if (typeof item.logs === 'object' && item.logs !== null) {
        // Если logs это объект - преобразуем в массив
        console.log('⚠️ logs является объектом, преобразуем в массив');
        Object.entries(item.logs).forEach(([key, value]) => {
          if (value && typeof value === 'object') {
            logsToDisplay.push(value);
          }
        });
      }
    }
    
    // 2. Пробуем получить логи из result.logs
    if (logsToDisplay.length === 0 && item.result && item.result.logs) {
      console.log('✅ Логи найдены в item.result.logs:', item.result.logs.length);
      logsToDisplay = item.result.logs;
    }
    
    // 3. Если все еще нет логов, пробуем загрузить с сервера
    if (logsToDisplay.length === 0) {
      console.log('⚠️ Логи не найдены в истории, пробуем загрузить с сервера...');
      await loadLogsFromServer(item.id || item.taskId);
      return;
    }
    
    // Форматируем логи для гарантии правильного формата
    const formattedLogs = logsToDisplay.map(log => {
      if (typeof log === 'string') {
        return {
          message: log,
          type: 'info',
          timestamp: new Date().toISOString()
        };
      }
      
      return {
        message: log.message || log.text || JSON.stringify(log),
        type: log.type || log.level || 'info',
        timestamp: log.timestamp || log.time || item.startTime || new Date().toISOString()
      };
    });
    
    console.log(`📊 Установлено ${formattedLogs.length} логов после обработки`);
    
    setSelectedLogs(formattedLogs);
    setViewDialogOpen(true);
  };

  const loadLogsFromServer = async (taskId) => {
    console.log(`🌐 Загружаем логи с сервера для задачи: ${taskId}`);
    setLoadingLogs(true);
    
    try {
      const response = await fetch(`http://localhost:8000/api/task/${taskId}/logs`);
      console.log('Статус ответа:', response.status, response.ok);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Данные получены с сервера:');
        console.log('Статус задачи:', data.status);
        console.log('Тип задачи:', data.type);
        console.log('Структура ответа:', data);
        
        let logs = [];
        
        // Ищем логи в разных местах ответа
        if (data.logs && Array.isArray(data.logs)) {
          logs = data.logs;
          console.log(`Найдено ${logs.length} логов в data.logs`);
        } else if (data.result && data.result.logs) {
          logs = data.result.logs;
          console.log(`Найдено ${logs.length} логов в data.result.logs`);
        }
        
        if (logs.length > 0) {
          // Форматируем логи
          const formattedLogs = logs.map(log => {
            if (typeof log === 'string') {
              return {
                message: log,
                type: 'info',
                timestamp: new Date().toISOString()
              };
            }
            
            return {
              message: log.message || JSON.stringify(log),
              type: log.type || 'info',
              timestamp: log.timestamp || new Date().toISOString()
            };
          });
          
          console.log(`📊 Устанавливаем ${formattedLogs.length} логов`);
          setSelectedLogs(formattedLogs);
          setViewDialogOpen(true);
        } else {
          console.warn('⚠️ Сервер вернул пустой массив logs');
          setSelectedLogs([{
            message: 'Сервер вернул пустые логи. Возможно они были очищены или не сохранились.',
            type: 'warning',
            timestamp: new Date().toISOString()
          }]);
          setViewDialogOpen(true);
        }
      } else {
        console.error('❌ Ошибка сервера:', response.status, response.statusText);
        setSelectedLogs([{
          message: `Ошибка сервера: ${response.status} ${response.statusText}`,
          type: 'error',
          timestamp: new Date().toISOString()
        }]);
        setViewDialogOpen(true);
      }
    } catch (error) {
      console.error('❌ Ошибка сети:', error);
      setSelectedLogs([{
        message: `Ошибка сети: ${error.message}`,
        type: 'error',
        timestamp: new Date().toISOString()
      }]);
      setViewDialogOpen(true);
    } finally {
      setLoadingLogs(false);
    }
  };

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
    
    try {
      const startDate = dayjs(start)
      const endDate = dayjs(end)
      const duration = endDate.diff(startDate, 'second')
      
      if (duration < 60) return `${duration} сек`
      return `${Math.floor(duration / 60)} мин ${duration % 60} сек`
    } catch (error) {
      return 'Н/Д'
    }
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
      default: return type || 'Неизвестный тип'
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'parse': return <DataObjectIcon fontSize="small" />
      case 'find-broken': return <DescriptionIcon fontSize="small" />
      default: return <InfoIcon fontSize="small" />
    }
  }

  const getLogsCount = (item) => {
    if (item.logs && Array.isArray(item.logs)) {
      return item.logs.length;
    }
    if (item.result && item.result.logs && Array.isArray(item.result.logs)) {
      return item.result.logs.length;
    }
    return 0;
  }

  const hasLogs = (item) => {
    return getLogsCount(item) > 0;
  }

  const filteredHistory = history.filter(item => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      item.folderName?.toLowerCase().includes(search) ||
      item.taskId?.toLowerCase().includes(search) ||
      getTypeText(item.type)?.toLowerCase().includes(search) ||
      item.status?.toLowerCase().includes(search) ||
      item.path?.toLowerCase().includes(search)
    )
  })

  const parseHistory = filteredHistory.filter(item => item.type === 'parse')
  const findBrokenHistory = filteredHistory.filter(item => item.type === 'find-broken')

  const displayHistory = selectedTab === 'parse' ? parseHistory :
                        selectedTab === 'find-broken' ? findBrokenHistory :
                        filteredHistory

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue)
  }

  const refreshHistory = async () => {
    setRefreshing(true)
    await loadHistory()
    setRefreshing(false)
  }

  const clearSearch = () => {
    setSearchTerm('')
  }

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
              onClick={refreshHistory}
              size="small"
              disabled={loading || refreshing}
            >
              {refreshing ? 'Обновление...' : 'Обновить'}
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
        {refreshing && <LinearProgress sx={{ mb: 2 }} />}
        
        <Box mb={2}>
          <TextField
            fullWidth
            placeholder="Поиск по истории..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            size="small"
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <SearchIcon sx={{ mr: 1, color: 'action.active' }} />,
              endAdornment: searchTerm && (
                <IconButton size="small" onClick={clearSearch}>
                  <ClearIcon />
                </IconButton>
              )
            }}
          />
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={selectedTab} onChange={handleTabChange}>
              <Tab label={`Все (${filteredHistory.length})`} value="all" />
              <Tab label={`Парсинг (${parseHistory.length})`} value="parse" />
              <Tab label={`Поиск битых (${findBrokenHistory.length})`} value="find-broken" />
            </Tabs>
          </Box>
          
          {loading && !refreshing ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : history.length === 0 ? (
            <Alert severity="info">
              История пуста. Запустите обработку файлов, чтобы увидеть историю здесь.
            </Alert>
          ) : displayHistory.length === 0 ? (
            <Alert severity="warning">
              По вашему запросу ничего не найдено.
            </Alert>
          ) : (
            <List>
              {displayHistory.map((item) => (
                <React.Fragment key={item.id || item.taskId}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box display="flex" alignItems="center" width="100%">
                        <Box flex={1}>
                          <ListItemText
                            primary={
                              <Box display="flex" alignItems="center" gap={1}>
                                {getStatusIcon(item.status)}
                                {getTypeIcon(item.type)}
                                <Typography variant="subtitle1">
                                  {getTypeText(item.type)}
                                </Typography>
                                <Chip
                                  label={getStatusText(item.status)}
                                  size="small"
                                  color={
                                    item.status === 'completed' ? 'success' :
                                    item.status === 'failed' ? 'error' : 
                                    item.status === 'running' ? 'primary' : 'default'
                                  }
                                />
                                {hasLogs(item) && (
                                  <Chip
                                    label={`${getLogsCount(item)} логов`}
                                    size="small"
                                    variant="outlined"
                                    color="info"
                                  />
                                )}
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
                          {hasLogs(item) && (
                            <Tooltip title="Просмотреть логи">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  viewLogs(item)
                                }}
                                disabled={loadingLogs}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title="Информация о записи (консоль)">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation()
                                console.log('=== ИНФОРМАЦИЯ О ЗАПИСИ ===')
                                console.log('ID:', item.id || item.taskId)
                                console.log('Type:', item.type)
                                console.log('Status:', item.status)
                                console.log('Folder:', item.folderName)
                                console.log('Logs field:', item.logs)
                                console.log('Logs type:', typeof item.logs)
                                console.log('Logs is array:', Array.isArray(item.logs))
                                console.log('Result field:', item.result)
                                console.log('Full item:', item)
                              }}
                            >
                              <InfoIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Удалить из истории">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteItem(item.id || item.taskId)
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
                          <strong>ID задачи:</strong> {item.taskId || item.id}
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
                        {item.duration && (
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            <strong>Продолжительность:</strong> {item.duration}
                          </Typography>
                        )}
                        {item.error && (
                          <Alert severity="error" sx={{ mt: 1, mb: 1 }}>
                            <strong>Ошибка:</strong> {item.error}
                          </Alert>
                        )}
                        {item.result && (
                          <Box mt={1}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Результат:</strong>
                            </Typography>
                            {item.type === 'parse' && item.result.summary && (
                              <Paper variant="outlined" sx={{ p: 1, mt: 0.5, bgcolor: 'grey.50' }}>
                                <Typography variant="body2">
                                  <strong>Обработано файлов:</strong> {item.result.summary['Всего обработано'] || 0}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>UCA файлов:</strong> {item.result.summary['UCA файлы'] || 0}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Других файлов:</strong> {item.result.summary['Другое файлы'] || 0}
                                </Typography>
                                {item.result.structure && (
                                  <>
                                    <Typography variant="body2">
                                      <strong>Структура:</strong>
                                    </Typography>
                                    <Typography variant="body2" component="div" sx={{ pl: 1 }}>
                                      <div>📁 <strong>UCA:</strong> {item.result.structure.UCA}</div>
                                      <div>📁 <strong>Другое:</strong> {item.result.structure.Другое}</div>
                                    </Typography>
                                  </>
                                )}
                              </Paper>
                            )}
                            {item.type === 'find-broken' && (
                              <Paper variant="outlined" sx={{ p: 1, mt: 0.5, bgcolor: 'grey.50' }}>
                                <Typography variant="body2">
                                  <strong>Найдено битых файлов:</strong> {item.result.found || 0}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Обработано файлов:</strong> {item.result.processed || 0}
                                </Typography>
                                {item.result.target_folder && (
                                  <Typography variant="body2">
                                    <strong>Перемещены в:</strong> {item.result.target_folder}
                                  </Typography>
                                )}
                              </Paper>
                            )}
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
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">
              Логи обработки: {selectedTaskName}
            </Typography>
            <Box display="flex" alignItems="center" gap={1}>
              {loadingLogs && <CircularProgress size={20} />}
              <Chip 
                label={`${selectedLogs.length} записей`} 
                size="small" 
                color="info" 
                variant="outlined" 
              />
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ maxHeight: '60vh', overflow: 'auto', fontFamily: 'monospace' }}>
            {selectedLogs.length === 0 ? (
              <Alert severity="warning">
                Логи отсутствуют. Нажмите "Обновить с сервера" чтобы загрузить.
              </Alert>
            ) : (
              <Box>
                {selectedLogs.map((log, index) => (
                  <Box
                    key={index}
                    sx={{
                      py: 1,
                      px: 2,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      '&:hover': {
                        backgroundColor: 'action.hover'
                      },
                      backgroundColor: log.type === 'error' ? 'rgba(211, 47, 47, 0.1)' :
                                     log.type === 'warning' ? 'rgba(255, 152, 0, 0.1)' :
                                     log.type === 'success' ? 'rgba(56, 142, 60, 0.1)' : 'transparent'
                    }}
                  >
                    <Box display="flex" alignItems="flex-start" gap={2}>
                      <Typography 
                        variant="caption" 
                        color="text.secondary"
                        sx={{ minWidth: '70px', fontSize: '0.75rem' }}
                      >
                        {log.timestamp ? dayjs(log.timestamp).format('HH:mm:ss') : '--:--:--'}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          color: log.type === 'error' ? 'error.main' :
                                 log.type === 'warning' ? 'warning.main' :
                                 log.type === 'success' ? 'success.main' : 'text.primary',
                          wordBreak: 'break-word',
                          fontSize: '0.85rem',
                          fontFamily: 'monospace',
                          whiteSpace: 'pre-wrap',
                          flex: 1
                        }}
                      >
                        {log.message}
                      </Typography>
                      {log.type && log.type !== 'info' && (
                        <Chip 
                          label={log.type} 
                          size="small" 
                          sx={{ 
                            height: '20px',
                            fontSize: '0.7rem',
                            backgroundColor: log.type === 'error' ? 'error.light' :
                                           log.type === 'warning' ? 'warning.light' :
                                           log.type === 'success' ? 'success.light' : 'default'
                          }}
                        />
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => loadLogsFromServer(selectedTaskId)} 
            disabled={loadingLogs || !selectedTaskId}
            startIcon={<RefreshIcon />}
          >
            {loadingLogs ? 'Загрузка...' : 'Обновить с сервера'}
          </Button>
          <Button onClick={() => setViewDialogOpen(false)}>Закрыть</Button>
        </DialogActions>
      </Dialog> 
    </Dialog>
  )
}

export default History