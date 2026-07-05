import { useState, type ReactNode } from 'react'
import { inputCls } from '../components/ui'

/** A list of sub-objects with add / remove and a custom row renderer. */
export function Repeater<T>({ items, onChange, empty, addLabel, render }: {
  items: T[]
  onChange: (v: T[]) => void
  empty: () => T
  addLabel: string
  render: (item: T, update: (patch: Partial<T>) => void, idx: number) => ReactNode
}) {
  const update = (i: number, patch: Partial<T>) =>
    onChange(items.map((it, j) => (j === i ? { ...it, ...patch } : it)))
  const remove = (i: number) => onChange(items.filter((_, j) => j !== i))
  return (
    <div className="space-y-3">
      {items.map((it, i) => (
        <div key={i} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <div className="mb-2 flex justify-end">
            <button onClick={() => remove(i)} className="text-xs text-rose-500 hover:text-rose-700">Remove</button>
          </div>
          {render(it, (patch) => update(i, patch), i)}
        </div>
      ))}
      <button onClick={() => onChange([...items, empty()])}
        className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
        + {addLabel}
      </button>
    </div>
  )
}

/** Editable list of bullet strings (multiline rows). */
export function BulletList({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="space-y-2">
      {value.map((b, i) => (
        <div key={i} className="flex gap-2">
          <textarea className={`${inputCls} min-h-[2.5rem]`} rows={2} value={b}
            onChange={(e) => onChange(value.map((x, j) => (j === i ? e.target.value : x)))} />
          <button onClick={() => onChange(value.filter((_, j) => j !== i))}
            className="shrink-0 self-start rounded-lg px-2 py-2 text-rose-500 hover:text-rose-700">✕</button>
        </div>
      ))}
      <button onClick={() => onChange([...value, ''])}
        className="text-sm text-slate-500 hover:underline">+ Add bullet</button>
    </div>
  )
}

/** Chips input for a list of short strings (honors, families, etc.). */
export function TagList({ value, onChange, placeholder }: {
  value: string[]; onChange: (v: string[]) => void; placeholder?: string
}) {
  const [text, setText] = useState('')
  const add = () => { const v = text.trim(); if (v && !value.includes(v)) onChange([...value, v]); setText('') }
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {value.map((t) => (
          <span key={t} className="flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700 dark:bg-slate-800 dark:text-slate-200">
            {t}
            <button className="text-slate-400 hover:text-rose-500" onClick={() => onChange(value.filter((x) => x !== t))}>×</button>
          </span>
        ))}
      </div>
      <input className={`${inputCls} mt-2`} value={text} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
        placeholder={placeholder ?? 'Type and press Enter'} />
    </div>
  )
}

export function Sub({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="mb-3 block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</span>
      {children}
    </label>
  )
}
