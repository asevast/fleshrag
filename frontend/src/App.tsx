import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bot,
  FolderTree,
  LibraryBig,
  MessagesSquare,
  PanelsTopLeft,
  Search,
  Settings2,
  Sparkles,
} from 'lucide-react'

import SearchBar from './components/SearchBar'
import ResultCard from './components/ResultCard'
import FilePreview from './components/FilePreview'
import FileBrowser from './components/FileBrowser'
import AdminConsole from './components/AdminConsole'
import AnswerStream from './components/AnswerStream'
import SettingsPanel from './components/SettingsPanel'
import StatusPanel from './components/StatusPanel'
import IndexManager from './components/IndexManager'
import ConversationList from './components/ConversationList'
import ConversationDetail from './components/ConversationDetail'
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

function App() {
  const [results, setResults] = useState<Result[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'search' | 'ask' | 'conversations' | 'admin'>('search')
  const [showBrowser, setShowBrowser] = useState(false)
  const [previewFile, setPreviewFile] = useState<{ path: string; filename: string } | null>(null)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const rag = useRag()

  const handleSearch = async (query: string, filters?: SearchFilters) => {
    setLoading(true)
    setResults([])
    setLastQuery(query)
    try {
      if (mode === 'search') {
        const res = await fetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k: 10, filters }),
        })
        if (!res.ok) throw new Error('Search failed')
        const data = await res.json()
        setResults(data)
      } else {
        await rag.ask(query)
      }
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleNewConversation = async () => {
    try {
      const res = await fetch('/api/conversations', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setSelectedConversationId(data.id)
        setMode('conversations')
      }
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }

  const handleSendMessage = async (query: string) => {
    if (!selectedConversationId) return

    try {
      const res = await fetch(`/api/conversations/${selectedConversationId}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, stream: false }),
      })
      if (!res.ok) throw new Error('Failed to send message')
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  const handleExportConversation = async (id: number) => {
    try {
      const res = await fetch(`/api/export/conversation/${id}`)
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `conversation_${id}.md`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export conversation:', error)
    }
  }

  const activeLoading = mode === 'search' ? loading : rag.loading
  const resultSummary = useMemo(() => {
    if (showBrowser) return 'Indexed file library'
    if (mode === 'search') return `${results.length} результатов`
    if (mode === 'ask') return `${rag.sources.length} источников`
    if (mode === 'admin') return 'Provider, budget and services'
    return selectedConversationId ? `Диалог #${selectedConversationId}` : 'История диалогов'
  }, [mode, rag.sources.length, results.length, selectedConversationId, showBrowser])

  const tabs = [
    { id: 'search', label: 'Search', icon: Search, description: 'Hybrid retrieval across indexed files' },
    { id: 'ask', label: 'Ask', icon: Bot, description: 'Grounded generation with streamed answer' },
    { id: 'conversations', label: 'Dialogs', icon: MessagesSquare, description: 'Saved sessions, history and export' },
    { id: 'files', label: 'Library', icon: LibraryBig, description: 'Inspect indexed folders and previews' },
    { id: 'admin', label: 'Admin', icon: PanelsTopLeft, description: 'Budget, provider runtime and operations' },
  ] as const

  return (
    <div className="app-shell">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <motion.header
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel overflow-hidden rounded-[32px]"
        >
          <div className="grid gap-6 p-6 md:grid-cols-[1.45fr_0.95fr] md:p-8">
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(207,190,165,0.55)] bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-[rgb(var(--muted))]">
                <Sparkles className="h-3.5 w-3.5 text-[rgb(var(--brand))]" />
                FleshRAG Control Deck
              </div>
              <div className="space-y-3">
                <h1 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] md:text-6xl">
                  Multimodal RAG для локального knowledge space
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-[rgb(var(--muted))] md:text-base">
                  Единый рабочий экран для поиска, grounded answer generation, просмотра файлов и операционного контроля индексации.
                </p>
              </div>
              <div className="flex flex-wrap gap-3 text-sm">
                <div className="soft-card rounded-2xl px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Mode</div>
                  <div className="mt-1 font-semibold">{showBrowser ? 'library' : mode}</div>
                </div>
                <div className="soft-card rounded-2xl px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Context</div>
                  <div className="mt-1 font-semibold">{resultSummary}</div>
                </div>
                <div className="soft-card rounded-2xl px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">State</div>
                  <div className="mt-1 font-semibold">{activeLoading ? 'Processing' : 'Ready'}</div>
                </div>
              </div>
            </div>

            <div className="rounded-[28px] border border-[rgba(207,190,165,0.55)] bg-[rgba(255,255,255,0.68)] p-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Workspace</div>
                  <div className="mt-2 text-2xl font-semibold">Search + Ops</div>
                </div>
                <div className="rounded-2xl bg-[rgba(199,89,48,0.12)] p-3 text-[rgb(var(--brand))]">
                  <FolderTree className="h-6 w-6" />
                </div>
              </div>
              <div className="mt-6 grid gap-3">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  const active = showBrowser ? tab.id === 'files' : mode === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => {
                        if (tab.id === 'files') {
                          setShowBrowser(true)
                          setMode('search')
                        } else {
                          setShowBrowser(false)
                          setMode(tab.id)
                          if (tab.id !== 'conversations') setSelectedConversationId(null)
                        }
                      }}
                      className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                        active
                          ? 'border-[rgb(var(--brand))] bg-[rgba(199,89,48,0.1)]'
                          : 'border-[rgba(207,190,165,0.4)] bg-white/70 hover:bg-white'
                      }`}
                    >
                      <span className={`rounded-xl p-2 ${active ? 'bg-[rgb(var(--brand))] text-white' : 'bg-[rgba(26,116,122,0.1)] text-[rgb(var(--accent))]'}`}>
                        <Icon className="h-4 w-4" />
                      </span>
                      <span>
                        <span className="block font-semibold">{tab.label}</span>
                        <span className="mt-1 block text-xs leading-5 text-[rgb(var(--muted))]">{tab.description}</span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </motion.header>

        <div className="grid gap-6 lg:grid-cols-[1.7fr_0.72fr]">
          <motion.main
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
            className="glass-panel min-h-[720px] rounded-[32px] p-5 md:p-6"
          >
            {showBrowser ? (
              <FileBrowser onPreview={(path, filename) => setPreviewFile({ path, filename })} />
            ) : mode === 'admin' ? (
              <AdminConsole />
            ) : mode === 'conversations' ? (
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.92fr_1.3fr]">
                <div className="soft-card rounded-[28px] p-4">
                  <ConversationList
                    onSelect={(id) => { setSelectedConversationId(id); setMode('conversations') }}
                    onNew={handleNewConversation}
                    onDelete={(id) => {
                      if (selectedConversationId === id) setSelectedConversationId(null)
                    }}
                    onExport={handleExportConversation}
                    selectedId={selectedConversationId || undefined}
                  />
                </div>
                <div className="soft-card rounded-[28px] p-4">
                  {selectedConversationId ? (
                    <ConversationDetail
                      conversationId={selectedConversationId}
                      onSend={handleSendMessage}
                      onPreview={(path, filename) => setPreviewFile({ path, filename })}
                    />
                  ) : (
                    <div className="flex min-h-[420px] items-center justify-center rounded-[24px] border border-dashed border-[rgba(207,190,165,0.8)] bg-[rgba(255,255,255,0.5)] p-8 text-center text-sm text-[rgb(var(--muted))]">
                      Выберите диалог слева или создайте новый, чтобы вести RAG-сессию с сохранённой историей.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                <SearchBar onSearch={handleSearch} loading={activeLoading} />

                {mode === 'ask' && (
                  <AnswerStream
                    answer={rag.answer}
                    sources={rag.sources}
                    loading={rag.loading}
                    error={rag.error}
                    onPreview={(path, filename) => setPreviewFile({ path, filename })}
                  />
                )}

                {mode === 'search' && (
                  <div className="mt-6 space-y-4">
                    {results.map((result, index) => (
                      <ResultCard
                        key={`${result.path}-${index}`}
                        result={result}
                        query={lastQuery}
                        onPreview={(path, filename) => setPreviewFile({ path, filename })}
                      />
                    ))}
                    {!loading && results.length === 0 && lastQuery && (
                      <div className="rounded-[24px] border border-dashed border-[rgba(207,190,165,0.7)] bg-white/60 p-8 text-center text-sm text-[rgb(var(--muted))]">
                        По этому запросу пока нет результатов. Попробуйте расширить формулировку или снять часть фильтров.
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </motion.main>

          <motion.aside
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.12 }}
            className="space-y-4"
          >
            <div className="glass-panel rounded-[28px] p-5">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-[rgba(26,116,122,0.12)] p-3 text-[rgb(var(--accent))]">
                  <Settings2 className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Operations</div>
                  <div className="text-lg font-semibold">Admin widgets</div>
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-[rgb(var(--muted))]">
                Временный операционный блок. Текущие панели настроек и индексирования сохранены до полной сборки выделенной Admin Console по ТЗ v2.
              </p>
            </div>

            <div className="grid gap-4">
              <div className="soft-card rounded-[28px] p-5">
                <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Intent</div>
                <div className="mt-2 text-lg font-semibold">
                  {showBrowser ? 'Browse indexed space' : mode === 'ask' ? 'Grounded answer generation' : mode === 'conversations' ? 'Saved sessions and export' : mode === 'admin' ? 'Operations and budget monitoring' : 'Hybrid retrieval'}
                </div>
              </div>
              <div className="soft-card rounded-[28px] p-5">
                <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Last query</div>
                <div className="mt-2 text-sm leading-6 text-[rgb(var(--text))]">
                  {lastQuery || 'Ещё не было поискового запроса в текущей сессии.'}
                </div>
              </div>
              <div className="soft-card rounded-[28px] p-5">
                <div className="flex items-center gap-2 text-[rgb(var(--success))]">
                  <Sparkles className="h-4 w-4" />
                  <span className="text-xs uppercase tracking-[0.18em]">Roadmap</span>
                </div>
                <div className="mt-2 text-sm leading-6 text-[rgb(var(--muted))]">
                  Следующий интерфейсный шаг: полноценный отдельный `/admin` surface, live logs и service management через Docker-aware backend.
                </div>
              </div>
            </div>
          </motion.aside>
        </div>
      </div>

      {previewFile && (
        <FilePreview
          path={previewFile.path}
          filename={previewFile.filename}
          onClose={() => setPreviewFile(null)}
        />
      )}

      <SettingsPanel />
      <StatusPanel />
      <IndexManager />
    </div>
  )
}

export default App
