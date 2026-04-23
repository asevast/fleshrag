import { useState, useEffect } from 'react'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    filename: string
    path: string
    snippet: string
    score: number
    rerank_score?: number
  }>
  created_at: string
}

interface ConversationDetail {
  id: number
  title: string | null
  created_at: string
  updated_at: string
  messages: Message[]
}

interface Props {
  conversationId: number
  onSend: (query: string) => Promise<void>
  onPreview: (path: string, filename: string) => void
}

export default function ConversationDetail({ conversationId, onSend, onPreview }: Props) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadConversation()
  }, [conversationId])

  const loadConversation = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/conversations/${conversationId}`)
      if (res.ok) {
        const data = await res.json()
        setConversation(data)
        setMessages(data.messages || [])
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || sending) return
    
    const query = input.trim()
    setInput('')
    setSending(true)
    
    // Optimistically add user message
    const tempId = Date.now()
    const userMsg: Message = {
      id: tempId,
      role: 'user',
      content: query,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    
    try {
      await onSend(query)
      await loadConversation() // Reload to get saved messages with sources
    } catch (e) {
      console.error('Failed to send message:', e)
      // Remove temp message on error
      setMessages(prev => prev.filter(m => m.id !== tempId))
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="text-center py-8 text-gray-500">Загрузка диалога...</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md flex flex-col h-[calc(100vh-200px)]">
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">
          {conversation?.title || `Диалог #${conversationId}`}
        </h2>
        <div className="text-xs text-gray-500 mt-1">
          {messages.length} сообщений
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            Начните диалог, задав первый вопрос
          </div>
        ) : (
          messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
                
                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className={`mt-3 pt-3 border-t ${
                    msg.role === 'user' ? 'border-blue-500' : 'border-gray-300'
                  }`}>
                    <div className="text-xs font-medium mb-2">
                      Источники:
                    </div>
                    <div className="space-y-2">
                      {msg.sources.map((src, i) => (
                        <div
                          key={i}
                          className="text-xs cursor-pointer hover:underline"
                          onClick={() => onPreview(src.path, src.filename)}
                        >
                          <div className="font-medium">{src.filename}</div>
                          <div className="opacity-75 truncate">{src.path}</div>
                          <div className="opacity-75 italic">Score: {src.score?.toFixed(3)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Введите вопрос..."
            className="flex-1 border rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? '...' : '→'}
          </button>
        </div>
      </div>
    </div>
  )
}
