import type { ReactNode } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { Activity, BadgeDollarSign, Cpu, Database, Gauge, RefreshCw, ServerCog, Zap } from 'lucide-react'

interface AdminStatus {
  provider: string
  models: {
    llm: string
    embed: string
    rerank?: string | null
  }
  index: {
    is_indexing: boolean
    stats: {
      total: number
      indexed: number
      pending: number
      error: number
      empty: number
    }
  }
  services: Array<{
    name: string
    status: string
    detail: string
  }>
  timestamp: string
}

interface BudgetStats {
  daily_limit_usd: number
  today_cost_usd: number
  today_ratio: number
  last_7_days: Array<{
    day: string
    cost_usd: number
    input_tok: number
    output_tok: number
  }>
  breakdown: Array<{
    op_type: string
    cost_usd: number
    input_tok: number
    output_tok: number
  }>
}

interface ConnectionTest {
  status: string
  provider: string
  latency_ms: number
  llm_model: string
  embed_model: string
}

interface AdminSettings {
  active_provider: 'cloud' | 'local'
}

export default function AdminConsole() {
  const [status, setStatus] = useState<AdminStatus | null>(null)
  const [budget, setBudget] = useState<BudgetStats | null>(null)
  const [connection, setConnection] = useState<ConnectionTest | null>(null)
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [switching, setSwitching] = useState(false)
  const [reindexing, setReindexing] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [statusRes, budgetRes, settingsRes] = await Promise.all([
        fetch('/api/admin/status'),
        fetch('/api/admin/budget/stats'),
        fetch('/api/admin/settings'),
      ])
      const [statusData, budgetData, settingsData] = await Promise.all([statusRes.json(), budgetRes.json(), settingsRes.json()])
      setStatus(statusData)
      setBudget(budgetData)
      setSettings(settingsData)
    } catch (error) {
      console.error('Failed to load admin console:', error)
    } finally {
      setLoading(false)
    }
  }

  const runConnectionTest = async () => {
    setTesting(true)
    try {
      const response = await fetch('/api/admin/models/test', { method: 'POST' })
      if (!response.ok) throw new Error('Connection test failed')
      setConnection(await response.json())
    } catch (error) {
      console.error(error)
      setConnection(null)
    } finally {
      setTesting(false)
    }
  }

  const switchProvider = async (provider: 'cloud' | 'local') => {
    setSwitching(true)
    setNotice(null)
    try {
      const response = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_provider: provider }),
      })
      if (!response.ok) throw new Error('Provider switch failed')
      const data = await response.json()
      setSettings(data)
      setNotice(`Провайдер переключен на ${provider}`)
      await load()
    } catch (error) {
      console.error(error)
      setNotice('Не удалось переключить провайдера')
    } finally {
      setSwitching(false)
    }
  }

  const triggerReindex = async () => {
    setReindexing(true)
    setNotice(null)
    try {
      const response = await fetch('/api/admin/index/reindex-all', { method: 'POST' })
      if (!response.ok) throw new Error('Reindex failed')
      const data = await response.json()
      setNotice(`Переиндексация поставлена в очередь для ${data.count} путей`)
      await load()
    } catch (error) {
      console.error(error)
      setNotice('Не удалось запустить переиндексацию')
    } finally {
      setReindexing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const weekMax = useMemo(() => {
    if (!budget?.last_7_days.length) return 1
    return Math.max(...budget.last_7_days.map((item) => item.cost_usd), 0.01)
  }, [budget])

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 rounded-[28px] border border-[rgba(207,190,165,0.55)] bg-white/70 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">Admin Console</div>
          <h2 className="mt-2 text-2xl font-semibold">Operations, budget and provider runtime</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[rgb(var(--muted))]">
            Выделенная зона управления провайдером, индексом и расходом токенов. Это промежуточная console-версия поверх новых admin endpoint'ов.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => switchProvider(settings?.active_provider === 'cloud' ? 'local' : 'cloud')}
            disabled={switching}
            className="rounded-2xl border border-[rgba(207,190,165,0.7)] bg-white px-4 py-3 text-sm font-medium text-[rgb(var(--accent))] transition hover:bg-[rgba(26,116,122,0.08)] disabled:opacity-60"
          >
            {switching ? 'Switching...' : settings?.active_provider === 'cloud' ? 'Switch to local' : 'Switch to cloud'}
          </button>
          <button
            onClick={triggerReindex}
            disabled={reindexing}
            className="rounded-2xl border border-[rgba(207,190,165,0.7)] bg-white px-4 py-3 text-sm font-medium text-[rgb(var(--brand))] transition hover:bg-[rgba(199,89,48,0.08)] disabled:opacity-60"
          >
            {reindexing ? 'Queueing...' : 'Reindex all'}
          </button>
          <button
            onClick={runConnectionTest}
            disabled={testing}
            className="rounded-2xl border border-[rgba(207,190,165,0.7)] bg-white px-4 py-3 text-sm font-medium text-[rgb(var(--brand))] transition hover:bg-[rgba(199,89,48,0.08)] disabled:opacity-60"
          >
            {testing ? 'Проверка...' : 'Test connection'}
          </button>
          <button
            onClick={load}
            disabled={loading}
            className="rounded-2xl bg-[rgb(var(--brand))] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[rgb(var(--brand-strong))] disabled:opacity-60"
          >
            {loading ? 'Обновление...' : 'Refresh'}
          </button>
        </div>
      </div>

      {notice && (
        <div className="rounded-[24px] border border-[rgba(207,190,165,0.55)] bg-[rgba(255,255,255,0.74)] px-4 py-3 text-sm text-[rgb(var(--muted))]">
          {notice}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Provider"
          value={status?.provider || '...'}
          icon={<ServerCog className="h-5 w-5" />}
          caption={status?.models.llm || 'LLM model pending'}
        />
        <MetricCard
          title="Today spend"
          value={`$${(budget?.today_cost_usd || 0).toFixed(3)}`}
          icon={<BadgeDollarSign className="h-5 w-5" />}
          caption={`limit $${(budget?.daily_limit_usd || 1).toFixed(2)}`}
        />
        <MetricCard
          title="Indexed files"
          value={String(status?.index.stats.indexed || 0)}
          icon={<Database className="h-5 w-5" />}
          caption={`${status?.index.stats.total || 0} total`}
        />
        <MetricCard
          title="Pending jobs"
          value={String(status?.index.stats.pending || 0)}
          icon={<RefreshCw className="h-5 w-5" />}
          caption={status?.index.is_indexing ? 'indexing in progress' : 'queue idle'}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="soft-card rounded-[28px] p-5">
          <div className="flex items-center gap-2">
            <Gauge className="h-5 w-5 text-[rgb(var(--accent))]" />
            <h3 className="text-lg font-semibold">Budget overview</h3>
          </div>
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="text-[rgb(var(--muted))]">Daily usage</span>
              <span className="font-medium">{Math.round((budget?.today_ratio || 0) * 100)}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-[rgba(207,190,165,0.25)]">
              <div
                className={`h-full rounded-full ${((budget?.today_ratio || 0) > 0.8) ? 'bg-red-500' : 'bg-[rgb(var(--success))]'}`}
                style={{ width: `${Math.min((budget?.today_ratio || 0) * 100, 100)}%` }}
              />
            </div>
          </div>

          <div className="mt-6 grid gap-3">
            {(budget?.last_7_days || []).map((item) => (
              <div key={item.day} className="grid grid-cols-[88px_1fr_76px] items-center gap-3">
                <div className="text-xs text-[rgb(var(--muted))]">{item.day}</div>
                <div className="h-2 overflow-hidden rounded-full bg-[rgba(207,190,165,0.22)]">
                  <div
                    className="h-full rounded-full bg-[rgb(var(--accent))]"
                    style={{ width: `${(item.cost_usd / weekMax) * 100}%` }}
                  />
                </div>
                <div className="text-right text-xs font-medium">${item.cost_usd.toFixed(3)}</div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {(budget?.breakdown || []).map((item) => (
              <div key={item.op_type} className="rounded-2xl border border-[rgba(207,190,165,0.4)] bg-white/70 p-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--muted))]">{item.op_type}</div>
                <div className="mt-2 text-xl font-semibold">${item.cost_usd.toFixed(3)}</div>
                <div className="mt-2 text-xs text-[rgb(var(--muted))]">
                  in: {item.input_tok.toLocaleString()} tok
                </div>
                <div className="text-xs text-[rgb(var(--muted))]">
                  out: {item.output_tok.toLocaleString()} tok
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-5">
          <div className="soft-card rounded-[28px] p-5">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-[rgb(var(--brand))]" />
              <h3 className="text-lg font-semibold">Runtime models</h3>
            </div>
            <div className="mt-4 space-y-3 text-sm">
              <RuntimeRow label="LLM" value={status?.models.llm || '...'} />
              <RuntimeRow label="Embed" value={status?.models.embed || '...'} />
              <RuntimeRow label="Rerank" value={status?.models.rerank || 'fallback/local'} />
              <RuntimeRow label="Timestamp" value={status?.timestamp || '...'} />
            </div>
            {connection && (
              <div className="mt-4 rounded-2xl border border-[rgba(50,122,88,0.3)] bg-[rgba(50,122,88,0.08)] p-4 text-sm">
                <div className="font-medium text-[rgb(var(--success))]">Connection OK</div>
                <div className="mt-1 text-[rgb(var(--muted))]">
                  {connection.provider} · {connection.latency_ms} ms
                </div>
              </div>
            )}
          </div>

          <div className="soft-card rounded-[28px] p-5">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-[rgb(var(--accent))]" />
              <h3 className="text-lg font-semibold">Services</h3>
            </div>
            <div className="mt-4 space-y-3">
              {(status?.services || []).map((service) => (
                <div key={service.name} className="flex items-start justify-between rounded-2xl border border-[rgba(207,190,165,0.4)] bg-white/65 p-4">
                  <div>
                    <div className="font-medium">{service.name}</div>
                    <div className="mt-1 text-xs text-[rgb(var(--muted))]">{service.detail}</div>
                  </div>
                  <div className="rounded-full bg-[rgba(50,122,88,0.1)] px-3 py-1 text-xs font-semibold text-[rgb(var(--success))]">
                    {service.status}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="soft-card rounded-[28px] p-5">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-[rgb(var(--brand))]" />
              <h3 className="text-lg font-semibold">Index health</h3>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <HealthCell label="Total" value={status?.index.stats.total || 0} />
              <HealthCell label="Indexed" value={status?.index.stats.indexed || 0} />
              <HealthCell label="Errors" value={status?.index.stats.error || 0} />
              <HealthCell label="Empty" value={status?.index.stats.empty || 0} />
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function MetricCard({ title, value, caption, icon }: { title: string; value: string; caption: string; icon: ReactNode }) {
  return (
    <div className="soft-card rounded-[24px] p-5">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--muted))]">{title}</div>
        <div className="text-[rgb(var(--brand))]">{icon}</div>
      </div>
      <div className="mt-3 text-3xl font-semibold">{value}</div>
      <div className="mt-2 text-xs text-[rgb(var(--muted))]">{caption}</div>
    </div>
  )
}

function RuntimeRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[rgba(207,190,165,0.35)] pb-2">
      <span className="text-[rgb(var(--muted))]">{label}</span>
      <span className="max-w-[60%] truncate text-right font-medium">{value}</span>
    </div>
  )
}

function HealthCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-[rgba(207,190,165,0.4)] bg-white/70 p-4">
      <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--muted))]">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  )
}
