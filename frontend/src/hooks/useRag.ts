import { useState, useCallback, useRef } from 'react'

interface Source {
  path: string
  filename: string
  snippet: string
  score: number
  rerank_score?: number
}

interface RagResult {
  sources: Source[]
  answer: string
  loading: boolean
  error: string
}

export function useRag() {
  const [result, setResult] = useState<RagResult>({
    sources: [],
    answer: '',
    loading: false,
    error: '',
  })
  const abortRef = useRef<() => void>(() => {})

  const ask = useCallback(async (query: string) => {
    setResult({ sources: [], answer: '', loading: true, error: '' })

    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: 5, stream: true }),
    })

    if (!response.body) {
      setResult(prev => ({ ...prev, loading: false }))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    abortRef.current = () => reader.cancel()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue
        // SSE формат: data: {json}
        const match = line.match(/^data:\s*(.+)$/)
        if (!match) continue
        const data = match[1].trim()

        if (data === '[DONE]') {
          setResult(prev => ({ ...prev, loading: false }))
          return
        }

        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'sources') {
            setResult(prev => ({ ...prev, sources: parsed.sources }))
          } else if (parsed.type === 'token') {
            setResult(prev => ({ ...prev, answer: prev.answer + parsed.content }))
          } else if (parsed.type === 'error') {
            setResult(prev => ({ ...prev, error: parsed.message, loading: false }))
          }
        } catch {
          // ignore parse errors
        }
      }
    }

    setResult(prev => ({ ...prev, loading: false }))
  }, [])

  const cancel = useCallback(() => {
    abortRef.current()
    setResult(prev => ({ ...prev, loading: false }))
  }, [])

  return { ...result, ask, cancel }
}

export default useRag