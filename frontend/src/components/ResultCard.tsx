import { highlightText } from '../utils/highlight'

interface Props {
  result: {
    path: string
    filename: string
    snippet: string
    score: number
    page?: number
    rerank_score?: number
    file_type?: string
  }
  onPreview?: (path: string, filename: string) => void
  query?: string
}

export default function ResultCard({ result, onPreview, query }: Props) {
  const highlightedSnippet = query ? highlightText(result.snippet, query) : result.snippet

  return (
    <div className="soft-card rounded-[24px] p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_32px_rgba(83,56,40,0.12)]">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-[rgb(var(--brand-strong))]">{result.filename}</h3>
          {result.file_type && (
            <span className="rounded-full bg-[rgba(26,116,122,0.1)] px-2.5 py-1 text-xs text-[rgb(var(--accent))]">
              {result.file_type}
            </span>
          )}
        </div>
        <div className="text-right text-xs text-[rgb(var(--muted))]">
          <div>qdrant: {result.score.toFixed(3)}</div>
          {result.rerank_score !== undefined && (
            <div className="text-[rgb(var(--success))]">rerank: {result.rerank_score.toFixed(3)}</div>
          )}
        </div>
      </div>
      <p 
        className="mb-3 line-clamp-3 text-sm leading-6 text-[rgb(var(--muted))]"
        dangerouslySetInnerHTML={{ __html: highlightedSnippet }}
      />
      <div className="flex justify-between items-center">
        <div className="truncate text-xs text-[rgb(var(--muted))] opacity-80">
          {result.path}{result.page ? ` (стр. ${result.page})` : ''}
        </div>
        {onPreview && (
          <button
            onClick={() => onPreview(result.path, result.filename)}
            className="ml-2 shrink-0 rounded-full border border-[rgba(207,190,165,0.7)] px-3 py-1 text-xs font-medium text-[rgb(var(--brand))] transition hover:bg-[rgba(199,89,48,0.08)]"
          >
            Просмотр
          </button>
        )}
      </div>
    </div>
  )
}
