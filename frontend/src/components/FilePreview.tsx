import { useState, useEffect } from 'react'

interface Props {
  path: string
  filename: string
  onClose: () => void
}

export default function FilePreview({ path, filename, onClose }: Props) {
  const [content, setContent] = useState<string | null>(null)
  const [isImage, setIsImage] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const ext = filename.split('.').pop()?.toLowerCase() || ''
    const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico']

    if (imageExts.includes(ext)) {
      setIsImage(true)
      setLoading(false)
      return
    }

    fetch(`/api/files/preview?path=${encodeURIComponent(path)}`)
      .then(async res => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || 'Ошибка загрузки')
        }
        return res.text()
      })
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(e => {
        setError(e.message)
        setLoading(false)
      })
  }, [path, filename])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="glass-panel flex max-h-[85vh] w-full max-w-4xl flex-col rounded-[30px]">
        <div className="flex items-center justify-between border-b border-[rgba(207,190,165,0.45)] px-5 py-4">
          <h3 className="truncate pr-4 text-lg font-semibold text-[rgb(var(--text))]">{filename}</h3>
          <button onClick={onClose} className="text-xl text-[rgb(var(--muted))] transition hover:text-[rgb(var(--brand))]">✕</button>
        </div>

        <div className="flex-1 overflow-auto p-4 min-h-[200px]">
          {loading && <div className="py-8 text-center text-[rgb(var(--muted))]">Загрузка...</div>}
          {error && <div className="text-center text-red-600 py-8">{error}</div>}
          {isImage && (
            <img
              src={`/api/files/preview?path=${encodeURIComponent(path)}`}
              alt={filename}
              className="max-w-full max-h-[60vh] mx-auto object-contain"
            />
          )}
          {content !== null && !isImage && (
            <pre className="whitespace-pre-wrap rounded-[24px] bg-[rgba(246,237,224,0.8)] p-4 font-mono text-sm text-[rgb(var(--text))]">
              {content}
            </pre>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[rgba(207,190,165,0.45)] px-5 py-3 text-xs text-[rgb(var(--muted))]">
          <span className="truncate">{path}</span>
          <a
            href={`/api/files/download?path=${encodeURIComponent(path)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-4 shrink-0 rounded-full border border-[rgba(207,190,165,0.7)] px-3 py-1.5 font-medium text-[rgb(var(--brand))] transition hover:bg-[rgba(199,89,48,0.08)]"
          >
            Открыть файл
          </a>
        </div>
      </div>
    </div>
  )
}
