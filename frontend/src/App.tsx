import { useQuery } from '@tanstack/react-query'
import { apiGet, type Health, type Settings } from './api'

const NAV = ['Dashboard', 'Tracker', 'Search & Tailor', 'Paste JD', 'Settings']

function ConnectionBadge() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<Health>('/health'),
    retry: false,
  })
  const [dot, label] = isLoading
    ? ['bg-amber-400', 'connecting…']
    : isError
      ? ['bg-red-500', 'backend offline']
      : ['bg-emerald-500', `backend v${data?.version}`]
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${dot}`} />
      {label}
    </div>
  )
}

export default function App() {
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => apiGet<Settings>('/config/settings'),
    retry: false,
  })

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <div className="flex">
        {/* Sidebar */}
        <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:block">
          <div className="mb-6 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-700 font-bold text-white">
              J
            </div>
            <span className="font-semibold">Job Application Agent</span>
          </div>
          <nav className="space-y-1">
            {NAV.map((item, i) => (
              <button
                key={item}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                  i === 0
                    ? 'bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
              >
                {item}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main */}
        <main className="flex-1 p-8">
          <header className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">Dashboard</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {settings?.candidate_name
                  ? `Welcome, ${settings.candidate_name}`
                  : 'Local workflow tool'}
              </p>
            </div>
            <ConnectionBadge />
          </header>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-lg font-semibold">V2.0 — Phase 0 scaffolding ✅</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-400">
              The React front end and FastAPI back end are wired together and the
              configuration store is live. From here we build the config-driven
              scoring/résumé core, then the pages, Settings, and multi-provider LLM
              tailoring.
            </p>
            <ul className="mt-4 space-y-1 text-sm text-slate-600 dark:text-slate-400">
              <li>• React + Vite + TypeScript + Tailwind</li>
              <li>• FastAPI backend with config read / write / reset</li>
              <li>• Editable config: profile, rules, résumé content, settings</li>
            </ul>
          </div>
        </main>
      </div>
    </div>
  )
}
