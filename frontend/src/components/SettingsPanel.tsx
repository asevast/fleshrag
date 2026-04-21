import { useState, useEffect, useCallback } from 'react'

interface Settings {
  llm_model: string
  embed_model: string
  chunk_size: number
  chunk_overlap: number
  top_k_search: number
  top_k_rerank: number
  index_paths: string[]
}

interface OllamaModel {
  name: string
  size: number
  digest: string
  modified_at: string
}

export default function SettingsPanel() {
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch('/api/settings')
      const data = await res.json()
      setSettings(data)
    } catch (e) {
      console.error(e)
    }
  }, [])

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch('/api/models')
      const data = await res.json()
      setOllamaModels(data.models || [])
    } catch (e) {
      console.error('Failed to fetch Ollama models:', e)
    }
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          llm_model: settings.llm_model,
          embed_model: settings.embed_model,
          chunk_size: settings.chunk_size,
          chunk_overlap: settings.chunk_overlap,
          top_k_search: settings.top_k_search,
          top_k_rerank: settings.top_k_rerank,
        }),
      })
      if (!res.ok) throw new Error('Failed to save settings')
      setMessage({ type: 'success', text: 'Настройки сохранены (требуется перезапуск для применения)' })
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    if (open) {
      fetchSettings()
      fetchModels()
    }
  }, [open, fetchSettings, fetchModels])

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 left-4 bg-gray-800 text-white px-4 py-2 rounded-full shadow-lg hover:bg-gray-700 z-50 text-sm"
      >
        ⚙️ Настройки
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 left-4 bg-white border rounded-lg shadow-xl z-50 w-96 max-h-[80vh] overflow-y-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">Настройки</h3>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
      </div>

      {message && (
        <div className={`mb-4 p-3 rounded text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">LLM модель</label>
          <select
            value={settings?.llm_model || ''}
            onChange={(e) => setSettings(s => s ? { ...s, llm_model: e.target.value } : null)}
            className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {ollamaModels.map(m => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
            <option value="qwen2.5:3b">qwen2.5:3b</option>
            <option value="phi4-mini:3.8b">phi4-mini:3.8b</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Embedding модель</label>
          <select
            value={settings?.embed_model || ''}
            onChange={(e) => setSettings(s => s ? { ...s, embed_model: e.target.value } : null)}
            className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {ollamaModels.filter(m => m.name.includes('embed')).map(m => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
            <option value="nomic-embed-text">nomic-embed-text</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Chunk size</label>
            <input
              type="number"
              value={settings?.chunk_size || 512}
              onChange={(e) => setSettings(s => s ? { ...s, chunk_size: parseInt(e.target.value) || 512 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={64}
              max={2048}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Chunk overlap</label>
            <input
              type="number"
              value={settings?.chunk_overlap || 64}
              onChange={(e) => setSettings(s => s ? { ...s, chunk_overlap: parseInt(e.target.value) || 64 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={0}
              max={512}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Top K (search)</label>
            <input
              type="number"
              value={settings?.top_k_search || 20}
              onChange={(e) => setSettings(s => s ? { ...s, top_k_search: parseInt(e.target.value) || 20 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={1}
              max={100}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Top K (rerank)</label>
            <input
              type="number"
              value={settings?.top_k_rerank || 5}
              onChange={(e) => setSettings(s => s ? { ...s, top_k_rerank: parseInt(e.target.value) || 5 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={1}
              max={50}
            />
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="text-xs text-gray-500 mb-2">
            Пути индексации: <code className="bg-gray-100 px-1 rounded">{settings?.index_paths.join(', ')}</code>
          </div>
          <p className="text-xs text-gray-400">
            Изменение путей требует редактирования .env и перезапуска контейнеров
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </div>
  )
}
