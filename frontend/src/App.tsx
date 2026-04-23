import { useState } from 'react'
import SearchBar from './components/SearchBar'
import ResultCard from './components/ResultCard'
import FilePreview from './components/FilePreview'
import FileBrowser from './components/FileBrowser'
import AnswerStream from './components/AnswerStream'
import SettingsPanel from './components/SettingsPanel'
import StatusPanel from './components/StatusPanel'
import { useRag } from './hooks/useRag'

interface Result {
  path: string
  filename: string
  snippet: string
  score: number
  page?: number
  rerank_score?: number
  file_type?: string
}

interface SearchFilters {
  file_types?: string[]
  date_after?: string
  date_before?: string
  path_contains?: string
}

function App() {
  const [results, setResults] = useState<Result[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'search' | 'ask'>('search')
  const [showBrowser, setShowBrowser] = useState(false)
  const [previewFile, setPreviewFile] = useState<{ path: string; filename: string } | null>(null)
  const rag = useRag()

  const handleSearch = async (query: string, filters?: SearchFilters) => {
    setLoading(true)
    setResults([])
    setLastQuery(query)
    try {
      if (mode === 'search') {
        const res = await fetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k: 10, filters }),
        })
        if (!res.ok) throw new Error('Search failed')
        const data = await res.json()
        setResults(data)
      } else {
        await rag.ask(query)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const activeLoading = mode === 'search' ? loading : rag.loading

  return (
    <div className="min-h-screen p-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-center">Multimodal RAG</h1>
      
      <div className="flex justify-center gap-2 mb-4">
        <button
          onClick={() => { setMode('search'); setShowBrowser(false) }}
          className={`px-4 py-2 rounded ${mode === 'search' && !showBrowser ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Поиск
        </button>
        <button
          onClick={() => { setMode('ask'); setShowBrowser(false) }}
          className={`px-4 py-2 rounded ${mode === 'ask' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Вопрос-ответ
        </button>
        <button
          onClick={() => { setShowBrowser(!showBrowser); setMode('search') }}
          className={`px-4 py-2 rounded ${showBrowser ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Файлы
        </button>
      </div>

      {showBrowser ? (
        <FileBrowser onPreview={(path, filename) => setPreviewFile({ path, filename })} />
      ) : (
        <>
          <SearchBar onSearch={handleSearch} loading={activeLoading} />

          {mode === 'ask' && (
            <AnswerStream
              answer={rag.answer}
              sources={rag.sources}
              loading={rag.loading}
              error={rag.error}
              onPreview={(path, filename) => setPreviewFile({ path, filename })}
            />
          )}

          {mode === 'search' && (
            <div className="mt-6 space-y-4">
              {results.map((r, i) => (
                <ResultCard
                  key={i}
                  result={r}
                  query={lastQuery}
                  onPreview={(path, filename) => setPreviewFile({ path, filename })}
                />
              ))}
            </div>
          )}
        </>
      )}

      {previewFile && (
        <FilePreview
          path={previewFile.path}
          filename={previewFile.filename}
          onClose={() => setPreviewFile(null)}
        />
      )}

      <SettingsPanel />
      <StatusPanel />
    </div>
  )
}

export default App
