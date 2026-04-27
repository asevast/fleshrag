import { useState, useEffect } from 'react'

interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

interface Props {
  onSelect: (id: number) => void
  onNew: () => void
  onDelete: (id: number) => void
  onExport: (id: number) => void
  selectedId?: number
}

export default function ConversationList({ onSelect, onNew, onDelete, onExport, selectedId }: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [bulkDeleting, setBulkDeleting] = useState(false)

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Удалить этот диалог?')) return
    
    try {
      const res = await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== id))
        if (selectedId === id) {
          onNew()
        }
        onDelete(id)
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return
    if (!confirm(`Удалить выбранные диалоги (${selectedIds.length})?`)) return
    
    setBulkDeleting(true)
    try {
      const response = await fetch('/api/conversations/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedIds }),
      })
      
      if (response.ok) {
        setConversations(prev => prev.filter(c => !selectedIds.includes(c.id)))
        setSelectedIds([])
      } else {
        // Fallback: удаляем по одному
        for (const id of selectedIds) {
          try {
            await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
          } catch (e) {
            console.error('Failed to delete conversation:', id, e)
          }
        }
        setConversations(prev => prev.filter(c => !selectedIds.includes(c.id)))
        setSelectedIds([])
      }
    } catch (e) {
      console.error('Failed to bulk delete conversations:', e)
    } finally {
      setBulkDeleting(false)
    }
  }

  const toggleSelect = (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const selectAll = () => {
    setSelectedIds(conversations.map(c => c.id))
  }

  const deselectAll = () => {
    setSelectedIds([])
  }

  const handleExport = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await fetch(`/api/export/conversation/${id}`)
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `conversation_${id}.md`
        a.click()
        URL.revokeObjectURL(url)
        onExport(id)
      }
    } catch (e) {
      console.error('Failed to export conversation:', e)
    }
  }

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/conversations')
      if (res.ok) {
        const data = await res.json()
        setConversations(data)
      }
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Диалоги</h2>
        <div className="flex gap-2">
          {selectedIds.length > 0 && (
            <>
              <button
                onClick={deselectAll}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm"
              >
                Снять выбор
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm disabled:opacity-50"
              >
                {bulkDeleting ? 'Удаление...' : `Удалить (${selectedIds.length})`}
              </button>
            </>
          )}
          <button
            onClick={onNew}
            className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
          >
            + Новый
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-500">Загрузка...</div>
      ) : conversations.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          Нет диалогов. Создайте новый!
        </div>
      ) : (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedIds.length === conversations.length}
              onChange={(e) => e.target.checked ? selectAll() : deselectAll()}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="text-xs text-gray-500">
              {selectedIds.length > 0 ? `Выбрано: ${selectedIds.length}` : 'Выберите диалоги для удаления'}
            </span>
          </div>
          <div className="space-y-2">
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`p-3 rounded-lg cursor-pointer border-2 transition-all ${
                  selectedId === conv.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-transparent hover:border-gray-300'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(conv.id)}
                      onClick={(e) => toggleSelect(conv.id, e)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{conv.title}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {conv.message_count} сообщений • {new Date(conv.updated_at).toLocaleString('ru-RU')}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <button
                      onClick={(e) => handleExport(conv.id, e)}
                      className="p-1 text-gray-600 hover:text-blue-600"
                      title="Экспорт в Markdown"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => handleDelete(conv.id, e)}
                      className="p-1 text-gray-600 hover:text-red-600"
                      title="Удалить"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
