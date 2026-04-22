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
  const [fileTypes, setFileTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [skip, setSkip] = useState(0)
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

  useEffect(() => {
    fetch('/api/files/types')
      .then((res) => res.json())
      .then((data) => setFileTypes(Array.isArray(data) ? data : []))
      .catch((error) => console.error('Failed to load file types:', error))
  }, [])

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
    <div className="soft-card rounded-[28px] p-5">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold">Файлы</h2>
          <p className="mt-1 text-sm text-[rgb(var(--muted))]">
            Просмотр индексированного пространства с фильтрами по статусу, типу и пути.
          </p>
        </div>
        <button
          onClick={handleReset}
          className="rounded-full border border-[rgba(207,190,165,0.6)] px-3 py-1.5 text-sm text-[rgb(var(--brand))] transition hover:bg-[rgba(199,89,48,0.08)]"
        >
          Сбросить фильтры
        </button>
      </div>

      <div className="mb-4 flex flex-col gap-2 lg:flex-row">
        <input
          type="text"
          placeholder="Поиск по пути..."
          value={searchPath}
          onChange={(e) => { setSearchPath(e.target.value); setSkip(0) }}
          className="flex-1 rounded-2xl border border-[rgba(207,190,165,0.6)] bg-white px-4 py-3 text-sm outline-none transition focus:border-[rgb(var(--accent))]"
        />
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setSkip(0) }}
          className="rounded-2xl border border-[rgba(207,190,165,0.6)] bg-white px-4 py-3 text-sm outline-none transition focus:border-[rgb(var(--accent))]"
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
          className="rounded-2xl border border-[rgba(207,190,165,0.6)] bg-white px-4 py-3 text-sm outline-none transition focus:border-[rgb(var(--accent))]"
        >
          <option value="">Все типы</option>
          {fileTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="py-8 text-center text-[rgb(var(--muted))]">Загрузка...</div>
      ) : files.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-[rgba(207,190,165,0.7)] bg-white/55 py-8 text-center text-[rgb(var(--muted))]">
          Нет файлов по текущим фильтрам
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className="cursor-pointer rounded-[22px] border border-[rgba(207,190,165,0.45)] bg-white/80 p-4 transition hover:border-[rgba(26,116,122,0.45)] hover:bg-white"
                onClick={() => onPreview?.(file.path, file.filename)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium text-[rgb(var(--brand-strong))]">{file.filename}</div>
                    <div className="truncate text-xs text-[rgb(var(--muted))]">{file.path}</div>
                    <div className="mt-1 text-xs text-[rgb(var(--muted))] opacity-80">
                      {file.file_type} • {file.indexed_at ? new Date(file.indexed_at).toLocaleString('ru-RU') : '-'}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs ${statusColors[file.status] || 'bg-gray-100'}`}
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
              className="rounded-full border border-[rgba(207,190,165,0.6)] px-4 py-2 text-sm transition hover:bg-white disabled:opacity-50"
            >
              ← Назад
            </button>
            <span className="text-sm text-[rgb(var(--muted))]">
              {skip + 1} - {skip + files.length}
            </span>
            <button
              onClick={() => setSkip(skip + limit)}
              disabled={files.length < limit}
              className="rounded-full border border-[rgba(207,190,165,0.6)] px-4 py-2 text-sm transition hover:bg-white disabled:opacity-50"
            >
              Вперёд →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
