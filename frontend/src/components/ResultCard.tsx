interface Props {
  result: {
    path: string
    filename: string
    snippet: string
    score: number
    page?: number
  }
}

export default function ResultCard({ result }: Props) {
  return (
    <div className="p-4 bg-white rounded shadow hover:shadow-md transition">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-blue-700">{result.filename}</h3>
        <span className="text-xs text-gray-500">score: {result.score.toFixed(3)}</span>
      </div>
      <p className="text-sm text-gray-600 mb-2 line-clamp-3">{result.snippet}</p>
      <div className="text-xs text-gray-400">{result.path}{result.page ? ` (стр. ${result.page})` : ''}</div>
    </div>
  )
}
