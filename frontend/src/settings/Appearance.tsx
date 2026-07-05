import { ACCENTS, useTheme, type Accent } from '../theme'
import { Section } from './parts'
import { Card } from '../components/ui'

const DOT: Record<Accent, string> = {
  violet: '#7c6cf0', emerald: '#10b981', sky: '#0ea5e9', rose: '#f43f5e', amber: '#f59e0b',
}

export function Appearance() {
  const { mode, accent, toggleMode, setAccent } = useTheme()
  return (
    <Section title="Appearance" desc="Personalize the look. Saved to this browser.">
      <Card>
        <div className="text-sm font-medium text-slate-600 dark:text-slate-300">Theme</div>
        <div className="mt-3 grid max-w-xs grid-cols-2 gap-2">
          {(['light', 'dark'] as const).map((m) => (
            <button key={m} onClick={() => { if (mode !== m) toggleMode() }}
              className={`rounded-xl px-4 py-3 text-sm capitalize transition ${mode === m ? 'text-white' : 'border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'}`}
              style={mode === m ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' } : undefined}>
              {m === 'dark' ? '🌙 Dark' : '☀️ Light'}
            </button>
          ))}
        </div>
      </Card>
      <Card>
        <div className="text-sm font-medium text-slate-600 dark:text-slate-300">Accent color</div>
        <div className="mt-3 flex flex-wrap gap-3">
          {ACCENTS.map((a) => (
            <button key={a} onClick={() => setAccent(a)}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm capitalize transition ${accent === a ? 'border-transparent text-white' : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'}`}
              style={accent === a ? { background: DOT[a] } : undefined}>
              <span className="h-3.5 w-3.5 rounded-full" style={{ background: DOT[a] }} />{a}
            </button>
          ))}
        </div>
      </Card>
    </Section>
  )
}
