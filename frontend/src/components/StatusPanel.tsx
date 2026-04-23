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

interface AdminStatus {
  provider: string
  models: {
    llm: string
    embed: string
    rerank?: string | null
  }
}

export default function StatusPanel() {
  const [open, setOpen] = useState(false)
  const [stats, setStats] = useState<IndexStats | null>(null)
  const [errors, setErrors] = useState<ErrorFile[]>([])
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const [indexRes, adminRes] = await Promise.all([
        fetch('/api/index/status'),
        fetch('/api/admin/status'),
      ])
      const indexData = await indexRes.json()
      const adminData = await adminRes.json()
      setStats(indexData.stats)
      setErrors(indexData.recent_errors || [])
      setAdminStatus(adminData)
    } catch (e) {
      console.error(e)
    }
  }, [])

  const triggerReindex = async () => {
    setLoading(true)
    try {
      await fetch('/api/index/trigger', { method: 'POST' })
      setTimeout(() => fetchStatus(), 500)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); fetchStatus() }}
        className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-full shadow-lg hover:bg-gray-700 z-50 text-sm"
      >
        📊 Статус индексации
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white border rounded-lg shadow-xl z-50 w-96 max-h-[80vh] overflow-y-auto p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-lg">Статус индексации</h3>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
      </div>

      {adminStatus && (
        <div className="mb-4 rounded border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
          <div className="font-medium">Provider: {adminStatus.provider}</div>
          <div className="mt-1">LLM: {adminStatus.models.llm}</div>
          <div>Embed: {adminStatus.models.embed}</div>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
          <div className="bg-blue-50 p-2 rounded text-center">
            <div className="text-2xl font-bold text-blue-700">{stats.total}</div>
            <div className="text-gray-600">Всего файлов</div>
          </div>
          <div className="bg-green-50 p-2 rounded text-center">
            <div className="text-2xl font-bold text-green-700">{stats.indexed}</div>
            <div className="text-gray-600">Проиндексировано</div>
          </div>
          <div className="bg-yellow-50 p-2 rounded text-center">
            <div className="text-2xl font-bold text-yellow-700">{stats.pending}</div>
            <div className="text-gray-600">В очереди</div>
          </div>
          <div className="bg-red-50 p-2 rounded text-center">
            <div className="text-2xl font-bold text-red-700">{stats.error}</div>
            <div className="text-gray-600">Ошибки</div>
          </div>
        </div>
      )}

      <button
        onClick={triggerReindex}
        disabled={loading}
        className="w-full mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
      >
        {loading ? 'Запуск...' : '🔄 Запустить переиндексацию'}
      </button>

      {errors.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2 text-red-700">Последние ошибки:</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {errors.map((err, i) => (
              <div key={i} className="text-xs bg-red-50 p-2 rounded border border-red-100">
                <div className="font-medium truncate">{err.filename}</div>
                <div className="text-red-600 truncate">{err.error_message}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
