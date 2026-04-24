import { useEffect, useState } from 'react'

import AdminConsole from './components/AdminConsole'
import AnswerStream from './components/AnswerStream'
import ConversationDetail from './components/ConversationDetail'
import ConversationList from './components/ConversationList'
import FileBrowser from './components/FileBrowser'
import FilePreview from './components/FilePreview'
import ResultCard from './components/ResultCard'
import SearchBar from './components/SearchBar'
import { useRag } from './hooks/useRag'

interface Result {
  path: string
  filename: string
  snippet: string
  score: number
  page?: number
  rerank_score?: number
  file_type?: string
}

interface SearchFilters {
  file_types?: string[]
  date_after?: string
  date_before?: string
  path_contains?: string
}

type View = 'search' | 'ask' | 'library' | 'dialogs' | 'admin'

const tabs: Array<{ id: View; label: string; hint: string }> = [
  { id: 'search', label: 'Search', hint: 'Гибридный поиск по индексу' },
  { id: 'ask', label: 'Ask', hint: 'Ответ с источниками и стримингом' },
  { id: 'library', label: 'Library', hint: 'Просмотр индексированных файлов' },
  { id: 'dialogs', label: 'Dialogs', hint: 'История RAG-сессий' },
  { id: 'admin', label: 'Admin', hint: 'Провайдер, статус и бюджет' },
]

function App() {
  const [view, setView] = useState<View>('search')
  const [results, setResults] = useState<Result[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [previewFile, setPreviewFile] = useState<{ path: string; filename: string } | null>(null)
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null)
  const [conversationRefreshKey, setConversationRefreshKey] = useState(0)
  const rag = useRag()

  const handleSearch = async (query: string, filters?: SearchFilters) => {
    setLastQuery(query)

    if (view === 'ask') {
      try {
        await rag.ask(query)
      } catch (error) {
        console.error('Ask error:', error)
      }
      return
    }

    setSearchLoading(true)
    setResults([])
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 10, filters }),
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }
      setResults(await response.json())
    } catch (error) {
      console.error('Search error:', error)
      // Показываем ошибку через пустой результат
      setResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  const createConversation = async () => {
    try {
      const response = await fetch('/api/conversations?title=Новый диалог', { method: 'POST' })
      if (!response.ok) {
        throw new Error('Conversation creation failed')
      }
      const data = await response.json()
      setActiveConversationId(data.id)
      setConversationRefreshKey((value) => value + 1)
      setView('dialogs')
    } catch (error) {
      console.error(error)
    }
  }

  const sendConversationMessage = async (query: string) => {
    let conversationId = activeConversationId
    if (!conversationId) {
      const response = await fetch('/api/conversations?title=Новый диалог', { method: 'POST' })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Conversation creation failed')
      }
      const data = await response.json()
      conversationId = data.id
      setActiveConversationId(conversationId)
    }

    const response = await fetch(`/api/conversations/${conversationId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, stream: false }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      // Если есть ошибка в ответе, используем её
      if (errorData.error) {
        // Бэкенд вернул ошибку как часть ответа (не HTTPException)
        return { answer: errorData.error, sources: [] }
      }
      throw new Error(errorData.detail || 'Conversation ask failed')
    }

    const result = await response.json()
    // Если бэкенд вернул ошибку в теле ответа
    if (result.error) {
      throw new Error(result.error)
    }
    
    setConversationRefreshKey((value) => value + 1)
    return result
  }

  useEffect(() => {
    if (view === 'dialogs' && activeConversationId === null) {
      createConversation()
    }
  }, [view])

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-[32px] border border-stone-200 bg-white px-6 py-8 shadow-sm">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="text-xs uppercase tracking-[0.3em] text-teal-700">FleshRAG MVP</div>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-stone-900">Multimodal workspace for search, grounded answers and operations</h1>
              <p className="mt-3 text-sm leading-6 text-stone-600">
                Один экран для поиска, вопрос-ответа, библиотеки, диалогов и runtime-управления. Текущий shell приведён к фактическим backend endpoint&apos;ам.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label="Search results" value={String(results.length)} hint={lastQuery ? `last query: ${lastQuery}` : 'гибридный retrieval'} />
              <StatCard label="Ask mode" value={rag.loading ? 'streaming' : 'ready'} hint={rag.sources.length ? `${rag.sources.length} sources` : 'grounded answer'} />
              <StatCard label="Dialogs" value={activeConversationId ? `#${activeConversationId}` : 'new'} hint="RAG history and export" />
            </div>
          </div>
        </header>

        <nav className="mt-6 grid gap-3 md:grid-cols-5">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setView(tab.id)}
              className={`rounded-[24px] border px-4 py-4 text-left transition ${
                view === tab.id
                  ? 'border-teal-700 bg-teal-700 text-white shadow-sm'
                  : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-100'
              }`}
            >
              <div className="text-sm font-semibold">{tab.label}</div>
              <div className={`mt-1 text-xs ${view === tab.id ? 'text-teal-50' : 'text-stone-500'}`}>{tab.hint}</div>
            </button>
          ))}
        </nav>

        <main className="mt-6">
          {(view === 'search' || view === 'ask') && (
            <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
              <SearchBar onSearch={handleSearch} loading={view === 'search' ? searchLoading : rag.loading} />

              {view === 'search' && (
                <div className="mt-6 space-y-4">
                  {results.length === 0 && !searchLoading ? (
                    <EmptyState
                      title="Поиск пока пуст"
                      description="Запустите запрос, чтобы получить релевантные фрагменты, файл и превью по клику."
                    />
                  ) : (
                    results.map((result, index) => (
                      <ResultCard
                        key={`${result.path}-${index}`}
                        result={result}
                        query={lastQuery}
                        onPreview={(path, filename) => setPreviewFile({ path, filename })}
                      />
                    ))
                  )}
                </div>
              )}

              {view === 'ask' && (
                <AnswerStream
                  answer={rag.answer}
                  sources={rag.sources}
                  loading={rag.loading}
                  error={rag.error}
                  onPreview={(path, filename) => setPreviewFile({ path, filename })}
                />
              )}
            </section>
          )}

          {view === 'library' && (
            <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
              <FileBrowser onPreview={(path, filename) => setPreviewFile({ path, filename })} />
            </section>
          )}

          {view === 'dialogs' && (
            <section className="grid gap-6 xl:grid-cols-[360px_1fr]">
              <ConversationList
                key={conversationRefreshKey}
                selectedId={activeConversationId ?? undefined}
                onSelect={setActiveConversationId}
                onNew={createConversation}
                onDelete={(id) => {
                  if (activeConversationId === id) {
                    setActiveConversationId(null)
                  }
                  setConversationRefreshKey((value) => value + 1)
                }}
                onExport={() => undefined}
              />

              {activeConversationId ? (
                <ConversationDetail
                  key={activeConversationId + conversationRefreshKey}
                  conversationId={activeConversationId}
                  onSend={sendConversationMessage}
                  onPreview={(path, filename) => setPreviewFile({ path, filename })}
                />
              ) : (
                <div className="rounded-[32px] border border-dashed border-stone-300 bg-white p-8 shadow-sm">
                  <EmptyState
                    title="Диалог не выбран"
                    description="Создайте новый диалог или выберите существующий слева, чтобы продолжить работу в контексте истории."
                  />
                </div>
              )}
            </section>
          )}

          {view === 'admin' && <AdminConsole />}
        </main>
      </div>

      {previewFile && (
        <FilePreview
          path={previewFile.path}
          filename={previewFile.filename}
          onClose={() => setPreviewFile(null)}
        />
      )}
    </div>
  )
}

function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-[24px] border border-stone-200 bg-stone-50 px-4 py-4">
      <div className="text-xs uppercase tracking-[0.18em] text-stone-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-stone-900">{value}</div>
      <div className="mt-1 text-xs text-stone-500">{hint}</div>
    </div>
  )
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[24px] border border-dashed border-stone-300 bg-stone-50 px-6 py-10 text-center">
      <div className="text-lg font-semibold text-stone-800">{title}</div>
      <div className="mt-2 text-sm leading-6 text-stone-500">{description}</div>
    </div>
  )
}

export default App
