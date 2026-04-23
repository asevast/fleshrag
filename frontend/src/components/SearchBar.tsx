import { useState, useEffect } from 'react'

interface Props {
  onSearch: (query: string, filters?: SearchFilters) => void
  loading: boolean
}

interface SearchFilters {
  file_types?: string[]
  date_after?: string
  date_before?: string
  path_contains?: string
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [fileTypes, setFileTypes] = useState<string[]>([])
  const [availableTypes, setAvailableTypes] = useState<string[]>([])
  const [dateAfter, setDateAfter] = useState('')
  const [dateBefore, setDateBefore] = useState('')
  const [pathContains, setPathContains] = useState('')

  useEffect(() => {
    fetch('/api/files/types')
      .then(res => res.json())
      .then(types => setAvailableTypes(types))
      .catch(console.error)
  }, [])

  const toggleFileType = (type: string) => {
    setFileTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    
    const filters: SearchFilters = {}
    if (fileTypes.length > 0) filters.file_types = fileTypes
    if (dateAfter) filters.date_after = dateAfter
    if (dateBefore) filters.date_before = dateBefore
    if (pathContains) filters.path_contains = pathContains
    
    onSearch(query.trim(), Object.keys(filters).length > 0 ? filters : undefined)
  }

  const clearFilters = () => {
    setFileTypes([])
    setDateAfter('')
    setDateBefore('')
    setPathContains('')
  }

  const hasFilters = fileTypes.length > 0 || dateAfter || dateBefore || pathContains

  return (
    <div className="soft-card rounded-[28px] p-4 md:p-5">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 lg:flex-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Спросите о содержимом файлов, коде, заметках, документах..."
          className="min-h-14 flex-1 rounded-2xl border border-[rgba(207,190,165,0.6)] bg-white/80 px-5 py-3 text-sm outline-none transition focus:border-[rgb(var(--accent))] focus:ring-4 focus:ring-[rgba(26,116,122,0.12)]"
        />
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`rounded-2xl border px-4 py-3 text-sm font-medium transition ${hasFilters ? 'border-[rgb(var(--accent))] bg-[rgba(26,116,122,0.1)] text-[rgb(var(--accent))]' : 'border-[rgba(207,190,165,0.6)] bg-white/70 text-[rgb(var(--muted))] hover:bg-white'}`}
            title="Фильтры"
          >
            Filters
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-2xl bg-[rgb(var(--brand))] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[rgb(var(--brand-strong))] disabled:opacity-50"
          >
            {loading ? 'Поиск...' : 'Запустить'}
          </button>
        </div>
      </form>

      {showFilters && (
        <div className="mt-4 rounded-[24px] border border-[rgba(207,190,165,0.55)] bg-[rgba(246,237,224,0.7)] p-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-sm">Фильтры</h3>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs text-[rgb(var(--brand))] hover:underline">
                Сбросить
              </button>
            )}
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Типы файлов</label>
              <div className="flex flex-wrap gap-2">
                {availableTypes.map(type => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => toggleFileType(type)}
                    className={`px-2 py-1 text-xs rounded border ${
                      fileTypes.includes(type)
                        ? 'border-[rgb(var(--brand))] bg-[rgb(var(--brand))] text-white'
                        : 'border-[rgba(207,190,165,0.7)] bg-white text-[rgb(var(--muted))] hover:bg-[rgba(255,255,255,0.92)]'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Дата после</label>
                <input
                  type="date"
                  value={dateAfter}
                  onChange={(e) => setDateAfter(e.target.value)}
                  className="w-full rounded-xl border border-[rgba(207,190,165,0.6)] bg-white px-3 py-2 text-sm outline-none focus:border-[rgb(var(--accent))]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Дата до</label>
                <input
                  type="date"
                  value={dateBefore}
                  onChange={(e) => setDateBefore(e.target.value)}
                  className="w-full rounded-xl border border-[rgba(207,190,165,0.6)] bg-white px-3 py-2 text-sm outline-none focus:border-[rgb(var(--accent))]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Путь содержит</label>
              <input
                type="text"
                value={pathContains}
                onChange={(e) => setPathContains(e.target.value)}
                placeholder="/documents/"
                className="w-full rounded-xl border border-[rgba(207,190,165,0.6)] bg-white px-3 py-2 text-sm outline-none focus:border-[rgb(var(--accent))]"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
