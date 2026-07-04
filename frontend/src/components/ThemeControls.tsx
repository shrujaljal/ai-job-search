import { ACCENTS, useTheme } from '../theme'

const DOT: Record<string, string> = {
  violet: '#7c6cf0', emerald: '#10b981', sky: '#0ea5e9', rose: '#f43f5e', amber: '#f59e0b',
}

export function ThemeControls() {
  const { mode, accent, toggleMode, setAccent } = useTheme()
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5">
        {ACCENTS.map((a) => (
          <button key={a} onClick={() => setAccent(a)} title={a}
            className={`h-4 w-4 rounded-full transition ${accent === a ? 'ring-2 ring-offset-2 ring-offset-transparent' : 'opacity-70 hover:opacity-100'}`}
            style={{ background: DOT[a], boxShadow: accent === a ? `0 0 0 2px ${DOT[a]}55` : undefined }} />
        ))}
      </div>
      <button onClick={toggleMode} title="Toggle theme"
        className="themed flex h-9 w-9 items-center justify-center rounded-xl border border-slate-300 bg-white/70 text-base hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:hover:bg-slate-800">
        {mode === 'dark' ? '☀️' : '🌙'}
      </button>
    </div>
  )
}
