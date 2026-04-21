import { useState } from 'react'
import SearchBar from './components/SearchBar'
import ResultCard from './components/ResultCard'

interface Result {
  path: string
  filename: string
  snippet: string
  score: number
  page?: number
}

function App() {
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'search' | 'ask'>('search')
  const [answer, setAnswer] = useState('')

  const handleSearch = async (query: string) => {
    setLoading(true)
    setResults([])
    setAnswer('')
    try {
      if (mode === 'search') {
        const res = await fetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k: 10 }),
        })
        const data = await res.json()
        setResults(data)
      } else {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k: 5 }),
        })
        const data = await res.json()
        setAnswer(data.answer?.answer || '')
        setResults(data.answer?.sources || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-center">Multimodal RAG</h1>
      <div className="flex justify-center gap-2 mb-4">
        <button
          onClick={() => setMode('search')}
          className={`px-4 py-2 rounded ${mode === 'search' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Поиск
        </button>
        <button
          onClick={() => setMode('ask')}
          className={`px-4 py-2 rounded ${mode === 'ask' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Вопрос-ответ
        </button>
      </div>
      <SearchBar onSearch={handleSearch} loading={loading} />
      {answer && (
        <div className="mt-6 p-4 bg-white rounded shadow">
          <h2 className="font-semibold mb-2">Ответ:</h2>
          <p className="whitespace-pre-wrap">{answer}</p>
        </div>
      )}
      <div className="mt-6 space-y-4">
        {results.map((r, i) => (
          <ResultCard key={i} result={r} />
        ))}
      </div>
    </div>
  )
}

export default App
