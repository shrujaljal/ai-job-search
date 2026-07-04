import type { ReactNode, ButtonHTMLAttributes } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}>
      {children}
    </div>
  )
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger'
}
export function Button({ variant = 'primary', className = '', ...props }: BtnProps) {
  const styles = {
    primary: 'bg-blue-700 text-white hover:bg-blue-800 disabled:bg-slate-300 dark:disabled:bg-slate-700',
    ghost: 'border border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }[variant]
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  )
}

const TIER_COLORS: Record<string, string> = {
  Strong: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  Good: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  Moderate: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  Weak: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  Blocked: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
}
export function TierBadge({ tier }: { tier: string }) {
  const cls = TIER_COLORS[tier] ?? TIER_COLORS.Weak
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{tier}</span>
}

export function ScoreBar({ score }: { score: number }) {
  const color = score >= 75 ? 'bg-emerald-500' : score >= 60 ? 'bg-blue-500'
    : score >= 45 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={`h-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-6 text-xs tabular-nums text-slate-500">{score}</span>
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
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
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'
