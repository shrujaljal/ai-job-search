import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../api'
import { Card, Button, inputCls } from '../components/ui'

function useFirstName() {
  const { data } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const name = data?.candidate_name || ''
  return name && name !== 'Your Name' ? name.split(' ')[0] : ''
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
    const t = setInterval(() => setI((n) => (n + 1) % messages.length), 3800)
    return () => clearInterval(t)
  }, [messages.length])
  return (
    <div className="flex h-16 items-center justify-center rounded-2xl bg-gradient-to-r from-blue-700 to-indigo-600 px-6 text-center font-semibold text-white shadow-sm">
      <span key={i} className="animate-[fade_0.6s_ease]">{messages[i]}</span>
      <style>{`@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}`}</style>
    </div>
  )
}

function TodaysPlan({ name }: { name: string }) {
  const qc = useQueryClient()
  const { data: plan } = useQuery({ queryKey: ['plan'], queryFn: api.getPlan, retry: false })
  const save = useMutation({
    mutationFn: api.putPlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plan'] }),
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
          onClick={() => save.mutate({ date: today, plan: text.trim(), done: false })}>
          💪 Set my plan
        </Button>
      </Card>
    )
  }
  if (todays.done) {
    return (
      <Card>
        <h2 className="text-lg font-semibold">📋 Today's Plan</h2>
        <p className="mt-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          🎉 <b>You did it{who}!</b> <i>{todays.plan}</i> — so proud of you. Rest up and go again tomorrow. 🌟
        </p>
        <Button variant="ghost" className="mt-3"
          onClick={() => save.mutate({ ...todays, done: false })}>Edit today's plan</Button>
      </Card>
    )
  }
  return (
    <Card>
      <h2 className="text-lg font-semibold">📋 Today's Plan</h2>
      <p className="mt-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-900 dark:bg-blue-950 dark:text-blue-200">
        <b>Today's focus:</b> {todays.plan}
      </p>
      <p className="mt-2 text-sm text-slate-500">Break it into small steps and knock them out one by one. You can do this{who}! 💪🚀</p>
      <div className="mt-3 flex gap-2">
        <Button onClick={() => save.mutate({ ...todays, done: true })}>✅ Mark complete</Button>
        <Button variant="ghost" onClick={() => save.mutate({ date: '', plan: '', done: false })}>✏️ Change plan</Button>
      </div>
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Card className="text-center">
      <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
    </Card>
  )
}

const BAR_COLORS: Record<string, string> = {
  'To Apply': '#3b82f6', Applied: '#eab308', 'Phone Screen': '#f97316',
  Interview: '#a855f7', 'Final Round': '#ef4444', Offer: '#22c55e', Rejected: '#64748b',
}

export default function Dashboard() {
  const name = useFirstName()
  const { data } = useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard, retry: false })
  const chartData = (data?.statuses ?? []).map((s) => ({ status: s, count: data?.by_status[s] ?? 0 }))

  return (
    <div className="space-y-6">
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
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="Total tracked" value={data.total} />
            <Metric label="Applied" value={data.applied} />
            <Metric label="Interviewing" value={data.interviewing} />
            <Metric label="Offers" value={data.offers} />
          </div>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Pipeline by status</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="status" width={90} tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: 'rgba(148,163,184,0.1)' }} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
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
