import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Stack,
  LinearProgress,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import FolderIcon from '@mui/icons-material/Folder'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import DescriptionIcon from '@mui/icons-material/Description'
import DataObjectIcon from '@mui/icons-material/DataObject'
import ExpandLess from '@mui/icons-material/ExpandLess'
import ExpandMore from '@mui/icons-material/ExpandMore'
import LogViewer from '../components/LogViewer'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Parser() {
  const [selectedFolder, setSelectedFolder] = useState('')
  const [availableFolders, setAvailableFolders] = useState([])
  const [expandedFolders, setExpandedFolders] = useState({})
  const [taskId, setTaskId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadFolders()
  }, [])

  const loadFolders = async () => {
    try {
      setRefreshing(true)
      const response = await axios.get(`${API_URL}/api/folders`)

      // Получаем все папки (включая вложенные)
      const folders = response.data.folders || []
      
      // Фильтруем чтобы показывать только папки с .txt файлами или вложенными папками
      const filteredFolders = folders.filter(folder => 
        folder.files_count > 0 || (folder.subfolders && folder.subfolders.length > 0)
      )

      setAvailableFolders(filteredFolders)

      if (filteredFolders.length > 0 && !selectedFolder) {
        // Выбираем первую папку по умолчанию
        const firstFolder = findFirstFolderWithFiles(filteredFolders)
        if (firstFolder) {
          setSelectedFolder(firstFolder.path)
        }
      }

    } catch (err) {
      console.error('Ошибка загрузки папок:', err)
      setError('Не удалось загрузить список папок')
    } finally {
      setRefreshing(false)
    }
  }

  // Рекурсивно ищем первую папку с файлами
  const findFirstFolderWithFiles = (folders) => {
    for (const folder of folders) {
      if (folder.files_count > 0) {
        return folder
      }
      if (folder.subfolders && folder.subfolders.length > 0) {
        const found = findFirstFolderWithFiles(folder.subfolders)
        if (found) return found
      }
    }
    return null
  }

  // Рекурсивно рендерим папки
  const renderFolderTree = (folders, level = 0) => {
    return folders.map((folder) => (
      <React.Fragment key={folder.path}>
        <ListItem 
          sx={{ 
            pl: level * 2 + 2,
            backgroundColor: selectedFolder === folder.path ? 'action.selected' : 'transparent',
            borderRadius: 1,
            mb: 0.5
          }}
          disablePadding
        >
          <ListItemButton 
            onClick={() => handleFolderSelect(folder)}
            selected={selectedFolder === folder.path}
            disabled={folder.files_count === 0 && (!folder.subfolders || folder.subfolders.length === 0)}
          >
            <ListItemIcon>
              <FolderIcon color={selectedFolder === folder.path ? "primary" : "inherit"} />
            </ListItemIcon>
            <ListItemText 
              primary={
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Typography variant="body1">{folder.name}</Typography>
                  {folder.files_count > 0 && (
                    <Chip 
                      label={`${folder.files_count} файлов`} 
                      size="small" 
                      color={selectedFolder === folder.path ? "primary" : "secondary"}
                      variant={selectedFolder === folder.path ? "filled" : "outlined"}
                    />
                  )}
                </Stack>
              }
              secondary={
                folder.files_count === 0 && folder.subfolders && folder.subfolders.length > 0 
                  ? `${folder.subfolders.length} вложенных папок` 
                  : null
              }
            />
            {folder.subfolders && folder.subfolders.length > 0 && (
              <IconButton 
                size="small"
                onClick={(e) => {
                  e.stopPropagation()
                  handleToggleFolder(folder.path)
                }}
              >
                {expandedFolders[folder.path] ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            )}
          </ListItemButton>
        </ListItem>
        
        {folder.subfolders && folder.subfolders.length > 0 && (
          <Collapse in={expandedFolders[folder.path]} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {renderFolderTree(folder.subfolders, level + 1)}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    ))
  }

  const handleFolderSelect = (folder) => {
    setSelectedFolder(folder.path)
  }

  const handleToggleFolder = (folderPath) => {
    setExpandedFolders(prev => ({
      ...prev,
      [folderPath]: !prev[folderPath]
    }))
  }

  const startParsing = async () => {
    if (!selectedFolder) {
      setError('Пожалуйста, выберите папку')
      return
    }

    setLoading(true)
    setError('')
    setLogs([])
    setTaskId(null)

    try {
      const response = await axios.post(`${API_URL}/api/parse-files`, {
        path: selectedFolder
      }, {
        timeout: 60000
      })

      setTaskId(response.data.task_id)
      setLogs([{
        message: `🚀 Парсинг запущен. Папка: ${getFolderName(selectedFolder)}`,
        type: 'info'
      }])

      pollLogs(response.data.task_id)

    } catch (err) {
      console.error('Ошибка запуска парсинга:', err)
      setError(err.response?.data?.detail || err.message || 'Ошибка запуска парсинга')
      setLoading(false)
    }
  }

  const pollLogs = async (id) => {
    const poll = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/task/${id}/logs`, {
          timeout: 15000
        })

        const newLogs = response.data.logs
        const taskStatus = response.data.status

        if (newLogs && newLogs.length > 0) {
          setLogs(prev => {
            const existingMessages = new Set(prev.map(l => l.message))
            const filtered = newLogs.filter(l => !existingMessages.has(l.message))
            return [...prev, ...filtered]
          })
        }

        if (taskStatus === 'running') {
          setTimeout(poll, 1500)
        } else if (taskStatus === 'completed') {
          setLogs(prev => [...prev, {
            message: '✅ Парсинг завершен успешно!',
            type: 'success'
          }])
          setLoading(false)
          setTimeout(loadFolders, 1000)
        } else if (taskStatus === 'failed') {
          setLoading(false)
          setLogs(prev => [...prev, {
            message: '❌ Парсинг завершен с ошибкой',
            type: 'error'
          }])
        }

      } catch (err) {
        console.error('Ошибка опроса:', err)
        if (err.code === 'ECONNABORTED') {
          setTimeout(poll, 2000)
        } else {
          setLoading(false)
          setError('Ошибка связи с сервером')
        }
      }
    }

    poll()
  }

  const getFolderName = (path) => {
    // Ищем папку в дереве
    const findFolder = (folders, targetPath) => {
      for (const folder of folders) {
        if (folder.path === targetPath) return folder
        if (folder.subfolders) {
          const found = findFolder(folder.subfolders, targetPath)
          if (found) return found
        }
      }
      return null
    }
    
    const folder = findFolder(availableFolders, path)
    return folder ? folder.name : path.split(/[\\/]/).pop() || path
  }

  const getSelectedFolderInfo = () => {
    const findFolder = (folders, targetPath) => {
      for (const folder of folders) {
        if (folder.path === targetPath) return folder
        if (folder.subfolders) {
          const found = findFolder(folder.subfolders, targetPath)
          if (found) return found
        }
      }
      return null
    }
    
    return findFolder(availableFolders, selectedFolder)
  }

  const clearLogs = () => {
    setLogs([])
  }

  const expandAllFolders = () => {
    const allPaths = []
    const collectPaths = (folders) => {
      folders.forEach(folder => {
        if (folder.subfolders && folder.subfolders.length > 0) {
          allPaths.push(folder.path)
          collectPaths(folder.subfolders)
        }
      })
    }
    collectPaths(availableFolders)
    
    const newExpanded = {}
    allPaths.forEach(path => {
      newExpanded[path] = true
    })
    setExpandedFolders(newExpanded)
  }

  const collapseAllFolders = () => {
    setExpandedFolders({})
  }

  const folderInfo = getSelectedFolderInfo()

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Парсер файлов
      </Typography>

      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Выбор папки для парсинга
        </Typography>

        {refreshing && (
          <LinearProgress sx={{ mb: 2 }} />
        )}

        <Box sx={{ mb: 3 }}>
          <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <Grid item xs={12}>
              <FormControl fullWidth disabled={loading || refreshing}>
                <InputLabel>Выбранная папка</InputLabel>
                <Select
                  value={selectedFolder}
                  onChange={(e) => setSelectedFolder(e.target.value)}
                  label="Выбранная папка"
                  renderValue={(value) => {
                    const folderName = getFolderName(value)
                    return (
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <FolderIcon fontSize="small" />
                        <Typography>{folderName}</Typography>
                      </Stack>
                    )
                  }}
                >
                  <MenuItem value="" disabled>
                    {refreshing ? 'Загрузка папок...' : 'Выберите папку'}
                  </MenuItem>
                  {availableFolders.map((folder) => (
                    <MenuItem key={folder.path} value={folder.path}>
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <FolderIcon fontSize="small" />
                        <Typography>{folder.name}</Typography>
                        {folder.files_count > 0 && (
                          <Chip label={folder.files_count} size="small" color="secondary" />
                        )}
                      </Stack>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, maxHeight: 300, overflow: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Структура папок:
              </Typography>
              <Box>
                <Button size="small" onClick={expandAllFolders} sx={{ mr: 1 }}>
                  Развернуть все
                </Button>
                <Button size="small" onClick={collapseAllFolders}>
                  Свернуть все
                </Button>
              </Box>
            </Box>
            
            {availableFolders.length === 0 ? (
              <Alert severity="info">
                {refreshing ? 'Загрузка структуры папок...' : 'Папки не найдены'}
              </Alert>
            ) : (
              <List dense>
                {renderFolderTree(availableFolders)}
              </List>
            )}
          </Paper>
        </Box>

        {folderInfo && (
          <Alert
            severity="info"
            icon={<FolderOpenIcon />}
            sx={{ mb: 3 }}
          >
            <Typography variant="body1" fontWeight="medium">
              Выбрана папка: {folderInfo.name}
            </Typography>
            <Typography variant="body2">
              .txt файлов: {folderInfo.files_count || 0}
              {folderInfo.subfolders && folderInfo.subfolders.length > 0 && (
                <>, вложенных папок: {folderInfo.subfolders.length}</>
              )}
            </Typography>
          </Alert>
        )}

        {/* Кнопки управления */}
        <Box sx={{ mt: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
            onClick={startParsing}
            disabled={loading || refreshing || !selectedFolder}
            size="large"
            sx={{ minWidth: 200 }}
          >
            {loading ? 'Парсинг...' : 'Запустить парсинг'}
          </Button>

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadFolders}
            disabled={loading || refreshing}
            sx={{ height: '40px' }}
          >
            Обновить список
          </Button>

          <Button
            variant="outlined"
            color="secondary"
            onClick={clearLogs}
            disabled={loading}
            sx={{ height: '40px' }}
          >
            Очистить логи
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <strong>Ошибка:</strong> {error}
          </Alert>
        )}

        {taskId && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <strong>ID задачи:</strong> {taskId}
          </Alert>
        )}
      </Paper>

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Логи парсинга
            </Typography>
            <Tooltip title="Очистить логи">
              <IconButton onClick={clearLogs} size="small" disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <LogViewer logs={logs} />
        </CardContent>
      </Card>

      <Paper elevation={1} sx={{ p: 2, mt: 3, bgcolor: '#f5f5f5' }}>
        <Typography variant="body2" color="text.secondary">
          <strong>📋 Функционал парсера:</strong>
          <ul style={{ marginTop: 8, marginBottom: 8, paddingLeft: 20 }}>
            <li>Поддержка вложенных папок и древовидной структуры</li>
            <li>Автоматическое определение UCA и УльтраЗвук файлов</li>
            <li>Сортировка UCA файлов по категориям: Density, Strength, Cement</li>
            <li>Сохранение результатов в Excel формате</li>
            <li>Создание структурированных папок для результатов</li>
          </ul>

          <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip icon={<DataObjectIcon />} label="UCA файлы" size="small" color="primary" variant="outlined" />
            <Chip icon={<DescriptionIcon />} label="Текстовые файлы" size="small" color="secondary" variant="outlined" />
            <Chip label="Excel экспорт" size="small" variant="outlined" />
            <Chip label="Древовидная структура" size="small" variant="outlined" />
          </Box>
        </Typography>
      </Paper>
    </Box>
  )
}

export default Parser