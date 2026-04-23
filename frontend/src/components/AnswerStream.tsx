import { useEffect, useRef } from 'react'

interface Source {
  path: string
  filename: string
  snippet: string
  score: number
  rerank_score?: number
}

interface Props {
  answer: string
  sources: Source[]
  loading: boolean
  error: string
  onPreview?: (path: string, filename: string) => void
}

export default function AnswerStream({ answer, sources, loading, error, onPreview }: Props) {
  const contentRef = useRef<HTMLDivElement>(null)

  // Автопрокрутка вниз при обновлении ответа
  useEffect(() => {
    if (contentRef.current && loading) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [answer, loading])

  if (error) {
    return (
      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
        Ошибка: {error}
      </div>
    )
  }

  return (
    <div className="mt-6 space-y-4">
      {sources.length > 0 && (
        <div>
          <h2 className="font-semibold mb-3 text-lg">Источники:</h2>
          <div className="space-y-3">
            {sources.map((s, i) => (
              <div
                key={i}
                className="p-3 bg-white rounded border hover:shadow-sm transition cursor-pointer"
                onClick={() => onPreview?.(s.path, s.filename)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-blue-700 truncate">{s.filename}</div>
                    <div className="text-xs text-gray-500 truncate">{s.path}</div>
                  </div>
                  <div className="text-xs text-gray-400 text-right ml-2">
                    <div>score: {s.score.toFixed(3)}</div>
                    {s.rerank_score !== undefined && (
                      <div className="text-green-600">rerank: {s.rerank_score.toFixed(3)}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {answer && (
        <div ref={contentRef} className="p-4 bg-white rounded shadow max-h-[60vh] overflow-y-auto">
          <h2 className="font-semibold mb-2 text-lg">Ответ:</h2>
          <p className="whitespace-pre-wrap text-gray-800">
            {answer}
            {loading && (
              <span className="inline-block w-2 h-5 ml-1 bg-blue-600 animate-pulse" />
            )}
          </p>
        </div>
      )}

      {!answer && !loading && !error && (
        <div className="p-8 text-center text-gray-500 bg-gray-50 rounded">
          Задайте вопрос, чтобы получить ответ на основе содержимого файлов
        </div>
      )}
    </div>
  )
}
