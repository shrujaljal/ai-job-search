import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ACCENTS, useTheme } from '../theme'

const DOT: Record<string, string> = {
  violet: '#7c6cf0', emerald: '#10b981', sky: '#0ea5e9', rose: '#f43f5e', amber: '#f59e0b',
}

export function ThemeControls() {
  const { mode, accent, toggleMode, setAccent } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} title="Theme"
        className="themed flex h-9 items-center gap-2 rounded-xl border border-slate-300 bg-white/70 px-2.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:hover:bg-slate-800">
        <span className="h-3.5 w-3.5 rounded-full" style={{ background: DOT[accent] }} />
        <span>{mode === 'dark' ? '🌙' : '☀️'}</span>
        <span className="text-slate-400">▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="themed absolute right-0 z-20 mt-2 w-52 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Appearance</div>
            <div className="mb-3 grid grid-cols-2 gap-1">
              {(['light', 'dark'] as const).map((m) => (
                <button key={m} onClick={() => { if (mode !== m) toggleMode() }}
                  className={`rounded-lg px-3 py-1.5 text-sm capitalize transition ${
                    mode === m ? 'text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`}
                  style={mode === m ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' } : undefined}>
                  {m === 'dark' ? '🌙 Dark' : '☀️ Light'}
                </button>
              ))}
            </div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Accent</div>
            <div className="flex items-center gap-2">
              {ACCENTS.map((a) => (
                <button key={a} onClick={() => setAccent(a)} title={a}
                  className={`h-6 w-6 rounded-full transition hover:scale-110 ${accent === a ? 'ring-2 ring-offset-2 ring-offset-white dark:ring-offset-slate-900' : ''}`}
                  style={{ background: DOT[a], boxShadow: accent === a ? `0 0 0 2px ${DOT[a]}` : undefined }} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
