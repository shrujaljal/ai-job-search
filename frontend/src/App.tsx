import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { api, type Health } from './api'
import { ThemeControls } from './components/ThemeControls'
import { Card } from './components/ui'
import Dashboard from './pages/Dashboard'
import Tracker from './pages/Tracker'
import Search from './pages/Search'
import PasteJD from './pages/PasteJD'

const PAGES = [
  { key: 'dashboard', label: 'Dashboard', icon: '📊', el: <Dashboard /> },
  { key: 'tracker', label: 'Tracker', icon: '🗂️', el: <Tracker /> },
  { key: 'search', label: 'Search & Tailor', icon: '🔍', el: <Search /> },
  { key: 'paste', label: 'Paste JD', icon: '📝', el: <PasteJD /> },
  {
    key: 'settings', label: 'Settings', icon: '⚙️', el: (
      <Card><h1 className="text-xl font-semibold">Settings</h1>
        <p className="mt-2 text-sm text-slate-500">Coming in Phase 3 — edit your profile, scoring rules, résumé content, templates, and AI provider here.</p>
      </Card>
    ),
  },
]

function useUsername() {
  const { data } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const u = (data?.username as string) || ''
  const c = data?.candidate_name || ''
  if (u) return u
  if (c && c !== 'Your Name') return c.split(' ')[0]
  return 'there'
}

function ConnectionDot() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['health'], queryFn: () => api.health(), retry: false })
  const cls = isLoading ? 'bg-amber-400' : isError ? 'bg-red-500' : 'bg-emerald-500'
  const title = isError ? 'backend offline' : `backend v${(data as Health)?.version ?? '…'}`
  return <span title={title} className={`inline-block h-2.5 w-2.5 rounded-full ${cls}`} />
}

function StreakPill() {
  const { data } = useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard, retry: false })
  const s = data?.streak?.current ?? 0
  if (!s) return null
  return (
    <div className="flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
      🔥 {s} day{s > 1 ? 's' : ''}
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('dashboard')
  const active = PAGES.find((p) => p.key === page) ?? PAGES[0]
  const username = useUsername()

  return (
    <div className="min-h-screen">
      <header className="themed sticky top-0 z-10 border-b border-slate-200/60 bg-white/70 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/60">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl font-bold text-white shadow-sm"
              style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>J</div>
            <span className="font-semibold">Job Application Agent</span>
          </div>
          <span className="hidden text-sm text-slate-400 sm:inline">·</span>
          <span className="hidden text-sm text-slate-500 sm:inline dark:text-slate-400">Hi, <b className="text-slate-700 dark:text-slate-200">{username}</b> 👋</span>
          <div className="ml-auto flex items-center gap-3">
            <StreakPill />
            <ThemeControls />
            <ConnectionDot />
          </div>
        </div>

        {/* Top tabs */}
        <div className="mx-auto max-w-6xl px-2">
          <nav className="no-scrollbar flex gap-1 overflow-x-auto overflow-y-hidden">
            {PAGES.map((p) => {
              const on = p.key === page
              return (
                <button key={p.key} onClick={() => setPage(p.key)}
                  className={`relative whitespace-nowrap rounded-t-lg px-4 pb-3 pt-2.5 text-sm font-medium transition ${on ? 'text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}>
                  <span className="mr-1.5">{p.icon}</span>{p.label}
                  {on && (
                    <motion.span layoutId="tab-underline"
                      className="absolute inset-x-2 bottom-0 h-0.5 rounded-full"
                      style={{ background: 'linear-gradient(90deg, var(--accent), var(--accent-2))' }} />
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <AnimatePresence mode="wait">
          <motion.div key={page}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
            {active.el}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
