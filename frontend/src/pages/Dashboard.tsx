import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../api'
import { Card, Button, inputCls } from '../components/ui'
import { Mascot } from '../components/Mascot'

function useFirstName() {
  const { data } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const u = (data?.username as string) || ''
  const c = data?.candidate_name || ''
  if (u) return u
  if (c && c !== 'Your Name') return c.split(' ')[0]
  return ''
}

function Carousel({ name }: { name: string }) {
  const who = name ? `, ${name}` : ''
  const messages = useMemo(() => [
    `The light is just around the corner${who} — keep going. 💡`,
    `Every application is a step closer. You've got this${who}! 💪`,
    `Rejection is redirection. The right role is coming${who}. 🌟`,
    `Your breakthrough is one 'yes' away. Keep showing up${who}. 🚀`,
    `Progress over perfection — you're doing great${who}. 🌱`,
    `You are the best${who} — believe it and keep pushing. 🏆`,
  ], [who])
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % messages.length), 4200)
    return () => clearInterval(t)
  }, [messages.length])
  return (
    <div className="relative h-16 overflow-hidden rounded-2xl px-6 text-white shadow-sm"
      style={{ background: 'linear-gradient(120deg, var(--accent), var(--accent-2))' }}>
      <AnimatePresence mode="wait">
        <motion.div key={i}
          initial={{ opacity: 0, y: 20, filter: 'blur(4px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          exit={{ opacity: 0, y: -20, filter: 'blur(4px)' }}
          transition={{ duration: 0.5 }}
          className="absolute inset-0 flex items-center justify-center text-center font-semibold">
          {messages[i]}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function TodaysPlan({ name }: { name: string }) {
  const qc = useQueryClient()
  const { data: plan } = useQuery({ queryKey: ['plan'], queryFn: api.getPlan, retry: false })
  const save = useMutation({
    mutationFn: api.putPlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plan', 'dashboard'] }),
  })
  const [text, setText] = useState('')
  const today = new Date().toISOString().slice(0, 10)
  const todays = plan?.date === today ? plan : {}
  const who = name ? ` ${name}` : ''

  if (!todays.plan) {
    return (
      <Card>
        <h2 className="text-lg font-semibold">📋 Today's Plan</h2>
        <p className="mt-1 text-sm text-slate-500">What's your plan for today{who}? Set a clear, achievable target.</p>
        <textarea className={`${inputCls} mt-3`} rows={2} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Apply to 5 target roles, follow up with 2 recruiters, tailor 3 resumes." />
        <Button className="mt-3" disabled={!text.trim() || save.isPending}
          onClick={() => save.mutate({ date: today, plan: text.trim(), done: false })}>💪 Set my plan</Button>
      </Card>
    )
  }
  if (todays.done) {
    return (
      <Card>
        <h2 className="text-lg font-semibold">📋 Today's Plan</h2>
        <p className="mt-2 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          🎉 <b>You did it{who}!</b> <i>{todays.plan}</i> — so proud of you. Rest up and go again tomorrow. 🌟
        </p>
        <Button variant="ghost" className="mt-3" onClick={() => save.mutate({ ...todays, done: false })}>Edit today's plan</Button>
      </Card>
    )
  }
  return (
    <Card>
      <h2 className="text-lg font-semibold">📋 Today's Plan</h2>
      <p className="mt-2 rounded-xl p-3 text-sm" style={{ background: 'var(--accent-soft)' }}><b>Today's focus:</b> {todays.plan}</p>
      <p className="mt-2 text-sm text-slate-500">Break it into small steps and knock them out one by one. You can do this{who}! 💪🚀</p>
      <div className="mt-3 flex gap-2">
        <Button onClick={() => save.mutate({ ...todays, done: true })}>✅ Mark complete</Button>
        <Button variant="ghost" onClick={() => save.mutate({ date: '', plan: '', done: false })}>✏️ Change plan</Button>
      </div>
    </Card>
  )
}

function Metric({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <Card className="text-center">
      <div className="text-3xl font-bold">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </Card>
  )
}

const BAR_COLORS: Record<string, string> = {
  'To Apply': '#3b82f6', Applied: '#eab308', 'Phone Screen': '#f97316',
  Interview: '#a855f7', 'Final Round': '#ef4444', Offer: '#22c55e', Rejected: '#94a3b8',
}

export default function Dashboard() {
  const name = useFirstName()
  const { data } = useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard, retry: false })
  const streak = data?.streak?.current ?? 0
  const chartData = (data?.statuses ?? []).map((s) => ({ status: s, count: data?.by_status[s] ?? 0 }))

  return (
    <div className="space-y-6">
      <Card><Mascot name={name} streak={streak} /></Card>
      <Carousel name={name} />
      <TodaysPlan name={name} />

      {!data || data.total === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            No applications tracked yet. Tailor a résumé and add it to the tracker, or add entries in the Tracker tab.
          </p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Metric label="Total" value={data.total} />
            <Metric label="Applied" value={data.applied} />
            <Metric label="Interviewing" value={data.interviewing} />
            <Metric label="Offers" value={data.offers} />
            <Metric label="Streak" value={`${streak}🔥`} hint={`best ${data.streak?.longest ?? 0}`} />
          </div>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Pipeline by status</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="status" width={90} tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: 'rgba(148,163,184,0.1)' }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} animationDuration={700}>
                  {chartData.map((d) => <Cell key={d.status} fill={BAR_COLORS[d.status] ?? '#3b82f6'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </>
      )}
    </div>
  )
}
