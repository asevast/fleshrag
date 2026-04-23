import { useState, useEffect, useCallback } from 'react'

interface Settings {
  active_provider: 'cloud' | 'local'
  llm_model: string
  embed_model: string
  rerank_model?: string | null
  llm_temperature: number
  llm_max_tokens: number
  chunk_size: number
  chunk_overlap: number
  top_k_search: number
  top_k_rerank: number
  index_paths: string[]
}

interface ModelsCatalog {
  active_provider: 'cloud' | 'local'
  cloud: { llm: string[]; embed: string[]; rerank: string[] }
  local: { llm: string[]; embed: string[]; rerank: string[] }
}

export default function SettingsPanel() {
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [catalog, setCatalog] = useState<ModelsCatalog | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/settings')
      const data = await res.json()
      setSettings(data)
    } catch (e) {
      console.error(e)
    }
  }, [])

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/models/catalog')
      const data = await res.json()
      setCatalog(data)
    } catch (e) {
      console.error('Failed to fetch model catalog:', e)
    }
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          active_provider: settings.active_provider,
          llm_model: settings.llm_model,
          embed_model: settings.embed_model,
          rerank_model: settings.rerank_model,
          llm_temperature: settings.llm_temperature,
          llm_max_tokens: settings.llm_max_tokens,
          chunk_size: settings.chunk_size,
          chunk_overlap: settings.chunk_overlap,
          top_k_search: settings.top_k_search,
          top_k_rerank: settings.top_k_rerank,
        }),
      })
      if (!res.ok) throw new Error('Failed to save settings')
      const updated = await res.json()
      setSettings(updated)
      setMessage({ type: 'success', text: 'Настройки сохранены и применены для новых запросов' })
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

  const activeModels = settings && catalog ? catalog[settings.active_provider] : null

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
          <label className="block text-xs font-medium text-gray-600 mb-1">Провайдер</label>
          <div className="grid grid-cols-2 gap-2">
            {(['cloud', 'local'] as const).map((provider) => (
              <button
                key={provider}
                onClick={() => setSettings((s) => s ? {
                  ...s,
                  active_provider: provider,
                  llm_model: catalog?.[provider].llm[0] || s.llm_model,
                  embed_model: catalog?.[provider].embed[0] || s.embed_model,
                  rerank_model: catalog?.[provider].rerank[0] || s.rerank_model,
                } : null)}
                className={`rounded border px-3 py-2 text-sm ${
                  settings?.active_provider === provider ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 text-gray-700'
                }`}
              >
                {provider === 'cloud' ? '☁ Cloud' : '⚙ Local'}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">LLM модель</label>
          <select
            value={settings?.llm_model || ''}
            onChange={(e) => setSettings(s => s ? { ...s, llm_model: e.target.value } : null)}
            className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {(activeModels?.llm || []).map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Embedding модель</label>
          <select
            value={settings?.embed_model || ''}
            onChange={(e) => setSettings(s => s ? { ...s, embed_model: e.target.value } : null)}
            className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {(activeModels?.embed || []).map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Temperature</label>
            <input
              type="number"
              step="0.1"
              value={settings?.llm_temperature ?? 0.3}
              onChange={(e) => setSettings(s => s ? { ...s, llm_temperature: parseFloat(e.target.value) || 0.3 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={0}
              max={2}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Max tokens</label>
            <input
              type="number"
              value={settings?.llm_max_tokens ?? 1000}
              onChange={(e) => setSettings(s => s ? { ...s, llm_max_tokens: parseInt(e.target.value) || 1000 } : null)}
              className="w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              min={64}
              max={8192}
            />
          </div>
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
