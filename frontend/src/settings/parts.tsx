import type { ReactNode } from 'react'
import { Button } from '../components/ui'

export function Section({ title, desc, children }: { title: string; desc?: string; children: ReactNode }) {
  return (
    <div>
      <h1 className="text-xl font-semibold">{title}</h1>
      {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
      <div className="mt-5 space-y-5">{children}</div>
    </div>
  )
}

export function SaveBar({ onSave, saving, saved, dirty }: {
  onSave: () => void; saving?: boolean; saved?: boolean; dirty?: boolean
}) {
  return (
    <div className="flex items-center gap-3 pt-2">
      <Button onClick={onSave} disabled={saving || !dirty}>{saving ? 'Saving…' : 'Save changes'}</Button>
      {saved && !dirty && <span className="text-sm text-emerald-600">✓ Saved</span>}
      {dirty && <span className="text-sm text-amber-600">Unsaved changes</span>}
    </div>
  )
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button type="button" onClick={() => onChange(!checked)}
      className="flex items-center gap-3 text-sm font-medium text-slate-700 dark:text-slate-200">
      <span className={`relative h-6 w-11 rounded-full transition ${checked ? '' : 'bg-slate-300 dark:bg-slate-700'}`}
        style={checked ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' } : undefined}>
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? 'left-[22px]' : 'left-0.5'}`} />
      </span>
      {label}
    </button>
  )
}
