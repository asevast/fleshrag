import { useState, useEffect, useCallback } from 'react'

interface IndexedFile {
  id: number
  path: string
  filename: string
  status: string
  file_type: string
  indexed_at: string | null
}

interface FileBrowserProps {
  onPreview?: (path: string, filename: string) => void
}

export default function FileBrowser({ onPreview }: FileBrowserProps) {
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [loading, setLoading] = useState(false)
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [filterType, setFilterType] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [searchPath, setSearchPath] = useState('')
  const limit = 50

  const fetchFiles = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      })
      if (filterType) params.append('file_types', filterType)
      if (filterStatus) params.append('status', filterStatus)
      if (searchPath) params.append('path_contains', searchPath)

      const res = await fetch(`/api/files?${params}`)
      if (!res.ok) throw new Error('Failed to fetch files')
      const data = await res.json()
      setFiles(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [skip, filterType, filterStatus, searchPath])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  const handleReset = () => {
    setSkip(0)
    setFilterType('')
    setFilterStatus('')
    setSearchPath('')
  }

  const statusColors: Record<string, string> = {
    indexed: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    empty: 'bg-gray-100 text-gray-800',
  }

  return (
    <div className="bg-white rounded shadow p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Файлы</h2>
        <button
          onClick={handleReset}
          className="text-sm text-blue-600 hover:underline"
        >
          Сбросить фильтры
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Поиск по пути..."
          value={searchPath}
          onChange={(e) => { setSearchPath(e.target.value); setSkip(0) }}
          className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setSkip(0) }}
          className="px-3 py-2 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">Все статусы</option>
          <option value="indexed">Проиндексировано</option>
          <option value="pending">В очереди</option>
          <option value="error">Ошибка</option>
          <option value="empty">Пусто</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setSkip(0) }}
          className="px-3 py-2 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">Все типы</option>
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
          <option value="xlsx">XLSX</option>
          <option value="pptx">PPTX</option>
          <option value="txt">TXT</option>
          <option value="md">MD</option>
          <option value="png">PNG</option>
          <option value="jpg">JPG</option>
          <option value="mp3">MP3</option>
          <option value="mp4">MP4</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-8">Загрузка...</div>
      ) : files.length === 0 ? (
        <div className="text-center text-gray-500 py-8">Нет файлов</div>
      ) : (
        <>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => onPreview?.(file.path, file.filename)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-blue-700 truncate">{file.filename}</div>
                    <div className="text-xs text-gray-500 truncate">{file.path}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {file.file_type} • {file.indexed_at ? new Date(file.indexed_at).toLocaleString('ru-RU') : '-'}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded ${statusColors[file.status] || 'bg-gray-100'}`}
                  >
                    {file.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-4">
            <button
              onClick={() => setSkip(Math.max(0, skip - limit))}
              disabled={skip === 0}
              className="px-4 py-2 border rounded text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              ← Назад
            </button>
            <span className="text-sm text-gray-600">
              {skip + 1} - {skip + files.length}
            </span>
            <button
              onClick={() => setSkip(skip + limit)}
              disabled={files.length < limit}
              className="px-4 py-2 border rounded text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              Вперёд →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
