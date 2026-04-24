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
    <div className="p-4 bg-white rounded shadow hover:shadow-md transition">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-blue-700">{result.filename}</h3>
          {result.file_type && (
            <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-600">
              {result.file_type}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 text-right">
          <div>qdrant: {result.score.toFixed(3)}</div>
          {result.rerank_score !== undefined && (
            <div className="text-green-600">rerank: {result.rerank_score.toFixed(3)}</div>
          )}
        </div>
      </div>
      <p 
        className="text-sm text-gray-600 mb-2 line-clamp-3"
        dangerouslySetInnerHTML={{ __html: highlightedSnippet }}
      />
      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-400 truncate">
          {result.path}{result.page ? ` (стр. ${result.page})` : ''}
        </div>
        {onPreview && (
          <button
            onClick={() => onPreview(result.path, result.filename)}
            className="text-xs text-blue-600 hover:text-blue-800 hover:underline ml-2 shrink-0"
          >
            Просмотр
          </button>
        )}
      </div>
    </div>
  )
}
