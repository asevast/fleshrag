import { useState, useEffect, useCallback } from 'react'

interface IndexStats {
  total: number
  indexed: number
  pending: number
  error: number
  empty: number
}

interface ErrorFile {
  path: string
  filename: string
  error_message: string | null
  indexed_at: string
}

interface IndexPath {
  path: string
  added_at: string
  file_count?: number
}

interface LogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
}

// Очистка ANSI-escape кодов из текста
const stripAnsiCodes = (text: string): string => {
  return text.replace(/\x1b\[[0-9;]*[mK]/g, '')
             .replace(/\x1b\[[0-9;]*[JHP]/g, '')
             .replace(/\x1b\[[0-9;]*[ABCD]/g, '')
             .replace(/\x1b\[[0-9;]*[fg]/g, '')
             .replace(/\x1b\[[0-9;]*[HL]/g, '')
             .replace(/\x1b\[[0-9;]*[SK]/g, '')
}

export default function IndexManager() {
  const [open, setOpen] = useState(false)
  const [stats, setStats] = useState<IndexStats | null>(null)
  const [errors, setErrors] = useState<ErrorFile[]>([])
  const [paths, setPaths] = useState<IndexPath[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [newPath, setNewPath] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'paths' | 'logs'>('overview')
  const [isIndexing, setIsIndexing] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/index/status')
      const data = await res.json()
      setStats(data.stats)
      setErrors(data.recent_errors || [])
      if (data.is_indexing !== undefined) {
        setIsIndexing(data.is_indexing)
      }
    } catch (e) {
      console.error(e)
    }
  }, [])

  const fetchPaths = useCallback(async () => {
    try {
      const res = await fetch('/api/index/paths')
      const data = await res.json()
      const indexPaths: string[] = data.paths || []
      setPaths(indexPaths.filter(Boolean).map((p: string) => ({ path: p, added_at: new Date().toISOString() })))
    } catch (e) {
      console.error(e)
    }
  }, [])

  const addLog = (message: string, level: LogEntry['level'] = 'info') => {
    setLogs(prev => [{
      timestamp: new Date().toISOString(),
      level,
      message
    }, ...prev].slice(0, 100))
  }

  const handleAddPath = async () => {
    if (!newPath.trim()) return
    
    try {
      const res = await fetch('/api/index/paths', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newPath.trim() })
      })
      
      if (res.ok) {
        addLog(`Добавлен путь: ${newPath}`, 'success')
        setNewPath('')
        fetchPaths()
        fetchStatus()
      } else {
        const error = await res.json()
        addLog(`Ошибка добавления пути: ${error.detail}`, 'error')
      }
    } catch (e: any) {
      addLog(`Ошибка: ${e.message}`, 'error')
    }
  }

  const handleRemovePath = async (path: string) => {
    try {
      const res = await fetch(`/api/index/paths/${encodeURIComponent(path)}`, {
        method: 'DELETE'
      })
      
      if (res.ok) {
        addLog(`Удалён путь: ${path}`, 'success')
        fetchPaths()
        fetchStatus()
      } else {
        const error = await res.json()
        addLog(`Ошибка удаления пути: ${error.detail}`, 'error')
      }
    } catch (e: any) {
      addLog(`Ошибка: ${e.message}`, 'error')
    }
  }

  const handleReindex = async () => {
    setLoading(true)
    addLog('Запущена полная переиндексация...', 'info')
    try {
      await fetch('/api/index/trigger', { method: 'POST' })
      addLog('Переиндексация запущена', 'success')
      setTimeout(() => fetchStatus(), 1000)
    } catch (e: any) {
      addLog(`Ошибка переиндексации: ${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleReindexPath = async (path: string) => {
    setLoading(true)
    addLog(`Запущена переиндексация пути: ${path}`, 'info')
    try {
      await fetch('/api/index/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths: [path] })
      })
      addLog(`Переиндексация пути запущена: ${path}`, 'success')
    } catch (e: any) {
      addLog(`Ошибка: ${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      fetchStatus()
      fetchPaths()
      const interval = setInterval(fetchStatus, 5000)
      return () => clearInterval(interval)
    }
  }, [open, fetchStatus, fetchPaths])

  const statCards = [
    { label: 'Всего файлов', value: stats?.total ?? 0, color: 'blue', icon: '📁' },
    { label: 'Проиндексировано', value: stats?.indexed ?? 0, color: 'green', icon: '✅' },
    { label: 'В очереди', value: stats?.pending ?? 0, color: 'yellow', icon: '⏳' },
    { label: 'Ошибки', value: stats?.error ?? 0, color: 'red', icon: '❌' },
    { label: 'Пустые', value: stats?.empty ?? 0, color: 'gray', icon: '📄' },
  ]

  const getColorClasses = (color: string) => {
    const classes: Record<string, string> = {
      blue: 'bg-blue-50 border-blue-200 text-blue-700',
      green: 'bg-green-50 border-green-200 text-green-700',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
      red: 'bg-red-50 border-red-200 text-red-700',
      gray: 'bg-gray-50 border-gray-200 text-gray-700',
    }
    return classes[color] || classes.gray
  }

  const getLogLevelClasses = (level: LogEntry['level']) => {
    const classes: Record<string, string> = {
      info: 'text-blue-600',
      warning: 'text-yellow-600',
      error: 'text-red-600',
      success: 'text-green-600',
    }
    return classes[level] || classes.info
  }

  const getLogLevelIcon = (level: LogEntry['level']) => {
    const icons: Record<string, string> = {
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌',
      success: '✅',
    }
    return icons[level] || icons.info
  }

  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); fetchStatus(); fetchPaths() }}
        className="fixed bottom-4 right-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-3 rounded-full shadow-lg hover:from-blue-700 hover:to-indigo-700 z-50 text-sm font-medium transition-all duration-200 hover:scale-105 flex items-center gap-2"
      >
        <span>📊</span>
        <span>Управление индексацией</span>
        {isIndexing && (
          <span className="flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-white opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
          </span>
        )}
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white border border-gray-200 rounded-2xl shadow-2xl z-50 w-[600px] max-h-[85vh] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-4 flex justify-between items-center">
        <div>
          <h3 className="font-bold text-lg text-white">Управление индексацией</h3>
          <p className="text-blue-100 text-xs mt-0.5">
            {isIndexing ? '⏳ Индексация в процессе...' : '✓ Система готова'}
          </p>
        </div>
        <button 
          onClick={() => setOpen(false)} 
          className="text-white/70 hover:text-white transition-colors text-xl"
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-gray-50">
        {[
          { id: 'overview', label: 'Обзор', icon: '📊' },
          { id: 'paths', label: 'Пути', icon: '📁' },
          { id: 'logs', label: 'Логи', icon: '📝' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-all duration-200 ${
              activeTab === tab.id
                ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className="mr-2">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-5">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              {statCards.map((stat) => (
                <div
                  key={stat.label}
                  className={`p-4 rounded-xl border-2 ${getColorClasses(stat.color)} transition-all duration-200 hover:scale-105`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{stat.icon}</span>
                    <span className="text-3xl font-bold">{stat.value}</span>
                  </div>
                  <div className="text-xs font-medium opacity-80">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Progress Bar */}
            {stats && stats.total > 0 && (
              <div className="bg-gray-100 rounded-full h-4 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-400 to-green-600 h-full transition-all duration-500 ease-out"
                  style={{ width: `${(stats.indexed / stats.total) * 100}%` }}
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={handleReindex}
                disabled={loading}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all duration-200 hover:shadow-lg flex items-center justify-center gap-2"
              >
                <span>🔄</span>
                {loading ? 'Запуск...' : 'Переиндексировать всё'}
              </button>
            </div>

            {/* Recent Errors */}
            {errors.length > 0 && (
              <div className="border border-red-200 rounded-xl p-4 bg-red-50">
                <h4 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                  <span>⚠️</span>
                  Последние ошибки ({errors.length})
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {errors.map((err, i) => (
                    <div
                      key={i}
                      className="text-xs bg-white p-2.5 rounded-lg border border-red-100"
                    >
                      <div className="font-medium text-red-700 truncate">{err.filename}</div>
                      <div className="text-red-600 text-xs mt-1 break-all">{err.error_message}</div>
                      <div className="text-red-400 text-xs mt-1">
                        {new Date(err.indexed_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Paths Tab */}
        {activeTab === 'paths' && (
          <div className="space-y-4">
            {/* Add Path Form */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddPath()}
                placeholder="/mnt/e или /home/user/documents"
                className="flex-1 px-4 py-2.5 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-sm"
              />
              <button
                onClick={handleAddPath}
                disabled={!newPath.trim()}
                className="px-5 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all duration-200 whitespace-nowrap"
              >
                ➕ Добавить
              </button>
            </div>

            {/* Quick Suggestions */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-gray-500">Быстро:</span>
              {['/mnt/e', '/mnt/d', '/mnt/c', '/home', '/'].map(path => (
                <button
                  key={path}
                  onClick={() => setNewPath(path)}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-xs text-gray-700 transition-all duration-200"
                >
                  {path}
                </button>
              ))}
            </div>

            {/* Paths List */}
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-700 text-sm">
                Индексируемые пути ({paths.length})
              </h4>
              {paths.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">
                  Нет добавленных путей
                </div>
              ) : (
                paths.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-200 hover:border-blue-300 transition-all duration-200"
                  >
                    <span className="text-xl">📁</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-800 text-sm truncate">{item.path}</div>
                    </div>
                    <button
                      onClick={() => handleReindexPath(item.path)}
                      className="px-3 py-1.5 text-xs bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-all font-medium"
                    >
                      🔄 Индексировать
                    </button>
                    <button
                      onClick={() => handleRemovePath(item.path)}
                      className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-all"
                      title="Удалить путь"
                    >
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Info */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700">
              <p className="flex items-start gap-2">
                <span>💡</span>
                <span>
                  Добавьте пути к папкам для индексации. Система автоматически игнорирует системные файлы, 
                  .git, node_modules, бинарные файлы и другие нечитаемые форматы.
                </span>
              </p>
            </div>
          </div>
        )}

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h4 className="font-semibold text-gray-700 text-sm">Журнал событий</h4>
              <button
                onClick={() => setLogs([])}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Очистить
              </button>
            </div>
            
            {logs.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                Нет записей в журнале
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[50vh] overflow-y-auto">
                {logs.map((log, i) => (
                  <div
                    key={i}
                    className={`text-xs p-2.5 rounded-lg border flex items-start gap-2 ${
                      log.level === 'error' ? 'bg-red-50 border-red-200' :
                      log.level === 'warning' ? 'bg-yellow-50 border-yellow-200' :
                      log.level === 'success' ? 'bg-green-50 border-green-200' :
                      'bg-blue-50 border-blue-200'
                    }`}
                  >
                    <span className="text-sm">{getLogLevelIcon(log.level)}</span>
                    <div className="flex-1 min-w-0">
                      <div className={`${getLogLevelClasses(log.level)} font-medium`}>
                        {stripAnsiCodes(log.message)}
                      </div>
                      <div className="text-gray-400 text-xs mt-0.5">
                        {new Date(log.timestamp).toLocaleTimeString('ru-RU')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
