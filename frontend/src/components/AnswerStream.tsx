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
      <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Ошибка: {error}
      </div>
    )
  }

  return (
    <div className="mt-6 space-y-4">
      {sources.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold">Источники:</h2>
          <div className="space-y-3">
            {sources.map((s, i) => (
              <div
                key={i}
                className="soft-card cursor-pointer rounded-[22px] p-4 transition hover:border-[rgba(26,116,122,0.45)]"
                onClick={() => onPreview?.(s.path, s.filename)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium text-[rgb(var(--brand-strong))]">{s.filename}</div>
                    <div className="truncate text-xs text-[rgb(var(--muted))]">{s.path}</div>
                  </div>
                  <div className="ml-2 text-right text-xs text-[rgb(var(--muted))]">
                    <div>score: {s.score.toFixed(3)}</div>
                    {s.rerank_score !== undefined && (
                      <div className="text-[rgb(var(--success))]">rerank: {s.rerank_score.toFixed(3)}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {answer && (
        <div ref={contentRef} className="soft-card max-h-[60vh] overflow-y-auto rounded-[26px] p-5">
          <h2 className="font-semibold mb-2 text-lg">Ответ:</h2>
          <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--text))] md:text-[15px]">
            {answer}
            {loading && (
              <span className="ml-1 inline-block h-5 w-2 animate-pulse bg-[rgb(var(--brand))]" />
            )}
          </p>
        </div>
      )}

      {!answer && !loading && !error && (
        <div className="rounded-[24px] border border-dashed border-[rgba(207,190,165,0.7)] bg-white/55 p-8 text-center text-[rgb(var(--muted))]">
          Задайте вопрос, чтобы получить ответ на основе содержимого файлов
        </div>
      )}
    </div>
  )
}
