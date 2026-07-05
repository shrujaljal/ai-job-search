import { useState } from 'react'
import { Card } from '../components/ui'
import { Account } from '../settings/Account'
import { Appearance } from '../settings/Appearance'
import { AI } from '../settings/AI'
import { ProfileEditor } from '../settings/Profile'

function Soon({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">Editor coming next in Phase 3.</p>
    </div>
  )
}

const SECTIONS = [
  { key: 'account', label: '👤 Account', el: <Account /> },
  { key: 'appearance', label: '🎨 Appearance', el: <Appearance /> },
  { key: 'ai', label: '🤖 AI & Providers', el: <AI /> },
  { key: 'profile', label: '📇 Profile', el: <ProfileEditor /> },
  { key: 'rules', label: '🎯 Scoring Rules', el: <Soon title="Scoring Rules" /> },
  { key: 'content', label: '📄 Résumé Content', el: <Soon title="Résumé Content" /> },
  { key: 'templates', label: '🧩 Templates', el: <Soon title="Templates" /> },
]

export default function Settings() {
  const [sec, setSec] = useState('account')
  const active = SECTIONS.find((s) => s.key === sec) ?? SECTIONS[0]

  return (
    <div className="grid gap-6 md:grid-cols-[200px_1fr]">
      <Card className="h-fit p-2">
        <nav className="space-y-1">
          {SECTIONS.map((s) => (
            <button key={s.key} onClick={() => setSec(s.key)}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                s.key === sec
                  ? 'font-medium text-white'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
              style={s.key === sec ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' } : undefined}>
              {s.label}
            </button>
          ))}
        </nav>
      </Card>
      <Card>{active.el}</Card>
    </div>
  )
}
