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
    <div>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Введите запрос..."
          className="flex-1 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`px-4 py-2 rounded border ${hasFilters ? 'bg-blue-100 border-blue-300' : 'bg-gray-100'}`}
          title="Фильтры"
        >
          🔧
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '...' : 'Искать'}
        </button>
      </form>

      {showFilters && (
        <div className="p-4 bg-gray-50 rounded border mb-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-sm">Фильтры</h3>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs text-blue-600 hover:underline">
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
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
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
                  className="w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Дата до</label>
                <input
                  type="date"
                  value={dateBefore}
                  onChange={(e) => setDateBefore(e.target.value)}
                  className="w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                className="w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
