import type { ReactNode, ButtonHTMLAttributes } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`themed rounded-2xl border border-slate-200/70 bg-white/80 p-6 shadow-sm backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900/70 ${className}`}>
      {children}
    </div>
  )
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' }
export function Button({ variant = 'primary', className = '', style, ...props }: BtnProps) {
  const base = 'rounded-xl px-4 py-2 text-sm font-semibold transition active:scale-[.97] disabled:cursor-not-allowed disabled:opacity-50'
  if (variant === 'primary') {
    return (
      <button
        className={`${base} text-white shadow-sm hover:brightness-110 ${className}`}
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))', ...style }}
        {...props}
      />
    )
  }
  const styles = variant === 'danger'
    ? 'bg-rose-500 text-white hover:bg-rose-600'
    : 'border border-slate-300 bg-white/70 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-200 dark:hover:bg-slate-800'
  return <button className={`${base} ${styles} ${className}`} style={style} {...props} />
}

const TIER_COLORS: Record<string, string> = {
  Strong: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  Good: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  Moderate: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  Weak: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  Blocked: 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
}
export function TierBadge({ tier }: { tier: string }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TIER_COLORS[tier] ?? TIER_COLORS.Weak}`}>{tier}</span>
}

export function ScoreBar({ score }: { score: number }) {
  const color = score >= 75 ? 'bg-emerald-500' : score >= 60 ? 'bg-sky-500'
    : score >= 45 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={`h-full rounded-full ${color} transition-[width] duration-500`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-6 text-xs font-medium tabular-nums text-slate-500">{score}</span>
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300" style={{ borderTopColor: 'var(--accent)' }} />
      {label}
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-600 dark:text-slate-300">{label}</span>
      {children}
    </label>
  )
}

export const inputCls =
  'w-full rounded-xl border border-slate-300 bg-white/80 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-transparent focus:ring-2 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100 focus:ring-[var(--ring)]'
