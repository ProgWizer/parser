// utils/history.js
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
    return true
  } catch (error) {
    console.error('Ошибка сохранения истории:', error)
    return false
  }
}

export const updateHistoryItem = (taskId, updates) => {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    const itemIndex = history.findIndex(item => item.taskId === taskId)
    
    if (itemIndex !== -1) {
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