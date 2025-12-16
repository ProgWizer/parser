import { v4 as uuidv4 } from 'uuid'

const HISTORY_KEY = 'fileProcessorHistory'
const MAX_HISTORY_ITEMS = 100

export const saveToHistory = (taskData) => {
  try {
    const existingHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    
    const historyItem = {
      id: uuidv4(),
      taskId: taskData.taskId,
      type: taskData.type || 'unknown',
      path: taskData.path,
      folderName: taskData.folderName,
      startTime: taskData.startTime || new Date().toISOString(),
      status: taskData.status || 'running',
      logs: taskData.logs || [],
      allLogs: taskData.allLogs || [], // Все логи с бэкенда
      result: taskData.result || null,
      error: taskData.error || null,
      savedAt: new Date().toISOString()
    }
    
    const newHistory = [historyItem, ...existingHistory]
    
    if (newHistory.length > MAX_HISTORY_ITEMS) {
      newHistory.length = MAX_HISTORY_ITEMS
    }
    
    localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory))
    
    console.log('Сохранено в историю:', historyItem)
    return historyItem.id
  } catch (error) {
    console.error('Ошибка сохранения истории:', error)
    return null
  }
}

export const updateHistoryItem = (taskId, updates) => {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    const itemIndex = history.findIndex(item => item.taskId === taskId)
    
    if (itemIndex !== -1) {
      // Если обновляем логи, сохраняем все (не только новые)
      if (updates.logs && updates.logs.length > 0) {
        const existingLogs = history[itemIndex].logs || []
        const existingMessages = new Set(existingLogs.map(l => l.message))
        const newLogs = updates.logs.filter(l => !existingMessages.has(l.message))
        updates.logs = [...existingLogs, ...newLogs]
      }
      
      history[itemIndex] = {
        ...history[itemIndex],
        ...updates,
        updatedAt: new Date().toISOString()
      }
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
      console.log('Обновлена запись истории:', history[itemIndex])
    }
    
    return itemIndex !== -1
  } catch (error) {
    console.error('Ошибка обновления истории:', error)
    return false
  }
}

export const saveCompleteLogsToHistory = (taskId, backendLogs = []) => {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    const itemIndex = history.findIndex(item => item.taskId === taskId)
    
    if (itemIndex !== -1) {
      // Объединяем логи фронтенда и бэкенда
      const existingLogs = history[itemIndex].logs || []
      const allLogs = [...backendLogs, ...existingLogs]
      
      // Убираем дубликаты по сообщению
      const uniqueLogs = []
      const seenMessages = new Set()
      
      for (const log of allLogs) {
        if (!seenMessages.has(log.message)) {
          seenMessages.add(log.message)
          uniqueLogs.push(log)
        }
      }
      
      // Сортируем по timestamp
      uniqueLogs.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
        return timeA - timeB
      })
      
      history[itemIndex] = {
        ...history[itemIndex],
        logs: uniqueLogs,
        allLogs: backendLogs, // Сохраняем оригинальные логи с бэкенда
        updatedAt: new Date().toISOString()
      }
      
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
      console.log('Сохранены полные логи в историю для задачи:', taskId)
      return true
    }
    
    return false
  } catch (error) {
    console.error('Ошибка сохранения полных логов:', error)
    return false
  }
}

export const getHistory = () => {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch (error) {
    console.error('Ошибка получения истории:', error)
    return []
  }
}

export const clearHistory = () => {
  localStorage.removeItem(HISTORY_KEY)
}

export const exportHistory = () => {
  const history = getHistory()
  return JSON.stringify(history, null, 2)
}

export const deleteFromHistory = (id) => {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    const newHistory = history.filter(item => item.id !== id)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory))
    return true
  } catch (error) {
    console.error('Ошибка удаления из истории:', error)
    return false
  }
}