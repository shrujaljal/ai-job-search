import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Health } from './api'
import Dashboard from './pages/Dashboard'
import Tracker from './pages/Tracker'
import Search from './pages/Search'
import PasteJD from './pages/PasteJD'
import { Card } from './components/ui'

const PAGES = [
  { key: 'dashboard', label: '📊 Dashboard', el: <Dashboard /> },
  { key: 'tracker', label: '🗂️ Tracker', el: <Tracker /> },
  { key: 'search', label: '🔍 Search & Tailor', el: <Search /> },
  { key: 'paste', label: '📝 Paste JD', el: <PasteJD /> },
  { key: 'settings', label: '⚙️ Settings', el: (
    <Card><h1 className="text-xl font-semibold">Settings</h1>
      <p className="mt-2 text-sm text-slate-500">Coming in Phase 3 — edit your profile, scoring rules, résumé content, templates, and AI provider here.</p>
    </Card>
  ) },
]

function ConnectionBadge() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['health'], queryFn: () => api.health(), retry: false })
  const [dot, label] = isLoading ? ['bg-amber-400', 'connecting…']
    : isError ? ['bg-red-500', 'backend offline']
    : ['bg-emerald-500', `backend v${(data as Health)?.version}`]
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${dot}`} />{label}
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('dashboard')
  const active = PAGES.find((p) => p.key === page) ?? PAGES[0]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <div className="flex">
        <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:block">
          <div className="mb-6 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-700 font-bold text-white">J</div>
            <span className="font-semibold">Job Application Agent</span>
          </div>
          <nav className="space-y-1">
            {PAGES.map((p) => (
              <button key={p.key} onClick={() => setPage(p.key)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                  p.key === page
                    ? 'bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}>{p.label}</button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-6 md:p-8">
          <div className="mb-6 flex items-center justify-end"><ConnectionBadge /></div>
          <div className="mx-auto max-w-5xl">{active.el}</div>
        </main>
      </div>
    </div>
  )
}
