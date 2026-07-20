import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, Button, Field, inputCls, ScoreBar, TierBadge, Spinner } from '../components/ui'
import { ResultCard } from '../components/ResultCard'
import type { Job, SearchResponse, TailorResult } from '../types'

function RolesInput({ roles, setRoles }: { roles: string[]; setRoles: (r: string[]) => void }) {
  const [text, setText] = useState('')
  const add = () => {
    const v = text.trim()
    if (v && !roles.includes(v)) setRoles([...roles, v])
    setText('')
  }
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {roles.map((r) => (
          <span key={r} className="flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            {r}
            <button className="text-blue-500 hover:text-blue-800" onClick={() => setRoles(roles.filter((x) => x !== r))}>×</button>
          </span>
        ))}
      </div>
      <input className={`${inputCls} mt-2`} value={text} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
        placeholder="Type a role and press Enter (e.g. Operations Analyst)" />
    </div>
  )
}

export default function Search() {
  const [roles, setRoles] = useState<string[]>([])
  const [location, setLocation] = useState('')
  const [datePosted, setDatePosted] = useState('any')
  const [jobType, setJobType] = useState('any')
  const [pages, setPages] = useState(1)
  const [queued, setQueued] = useState<Set<string>>(new Set())
  const [hideBlocked, setHideBlocked] = useState(true)
  const [tailorResults, setTailorResults] = useState<TailorResult[]>([])
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const usingAi = Boolean(settings.data?.llm.enabled)

  const search = useMutation<SearchResponse, Error>({
    mutationFn: () => api.search({ roles, location, date_posted: datePosted, job_type: jobType, pages }),
    onSuccess: () => { setQueued(new Set()); setTailorResults([]) },
  })

  const jobs = search.data?.jobs ?? []
  const visible = jobs.filter((j) => !(hideBlocked && j.blocked))
  const key = (j: Job) => `${j.title}@@${j.company}`

  const tailor = useMutation<TailorResult[], Error>({
    mutationFn: async () => {
      const picks = jobs.filter((j) => queued.has(key(j)))
      const out: TailorResult[] = []
      for (const j of picks) {
        out.push(await api.tailor({
          company: j.company, role: j.title, jd_text: j.jd_text || '',
          job_id: j.id || j.url || '', location: j.location || '',
        }))
      }
      return out
    },
    onSuccess: setTailorResults,
  })

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold">Search & Tailor</h1>

      <Card className="space-y-4">
        <Field label="Roles"><RolesInput roles={roles} setRoles={setRoles} /></Field>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Field label="Location"><input className={inputCls} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="California" /></Field>
          <Field label="Date posted">
            <select className={inputCls} value={datePosted} onChange={(e) => setDatePosted(e.target.value)}>
              <option value="any">Any time</option><option value="day">Past 24h</option>
              <option value="week">Past week</option><option value="month">Past month</option>
            </select>
          </Field>
          <Field label="Job type">
            <select className={inputCls} value={jobType} onChange={(e) => setJobType(e.target.value)}>
              <option value="any">Any</option><option value="fulltime">Full-time</option>
              <option value="internship">Internship</option><option value="contract">Contract</option>
            </select>
          </Field>
          <Field label="Pages"><input type="number" min={1} max={5} className={inputCls} value={pages} onChange={(e) => setPages(Number(e.target.value))} /></Field>
        </div>
        <div className="flex items-center gap-3">
          <Button disabled={roles.length === 0 || search.isPending} onClick={() => search.mutate()}>Search Jobs</Button>
          {search.isPending && <Spinner label="Scraping, reading JDs, and scoring…" />}
        </div>
        {search.isError && <p className="text-sm text-red-600">{search.error.message}</p>}
      </Card>

      {search.data && (
        <>
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>
              {search.data.counts.total} jobs · scored on JD: {search.data.counts.scored_on_jd}/{search.data.counts.total}
              {search.data.counts.blocked > 0 && ` · ${search.data.counts.blocked} sponsorship-blocked`}
            </span>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={hideBlocked} onChange={(e) => setHideBlocked(e.target.checked)} />
              Hide sponsorship-blocked
            </label>
          </div>

          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-3 py-2">Queue</th><th className="px-3 py-2">Fit</th><th className="px-3 py-2">Tier</th>
                  <th className="px-3 py-2">Title</th><th className="px-3 py-2">Company</th>
                  <th className="px-3 py-2">Why</th><th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {visible.map((j) => (
                  <tr key={key(j)} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={queued.has(key(j))}
                        onChange={(e) => {
                          const s = new Set(queued)
                          if (e.target.checked) s.add(key(j))
                          else s.delete(key(j))
                          setQueued(s)
                        }} />
                    </td>
                    <td className="px-3 py-2"><ScoreBar score={j.score} /></td>
                    <td className="px-3 py-2"><TierBadge tier={j.tier} /></td>
                    <td className="px-3 py-2 font-medium">{j.title}</td>
                    <td className="px-3 py-2">{j.company}</td>
                    <td className="max-w-md px-3 py-2 text-xs text-slate-500">{j.reason}</td>
                    <td className="px-3 py-2 text-right">
                      {j.url && <a href={j.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">Open</a>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="flex items-center gap-3">
            <Button disabled={queued.size === 0 || tailor.isPending} onClick={() => tailor.mutate()}>
              🎯 Tailor Selected Resumes ({queued.size})
            </Button>
            {tailor.isPending && <Spinner label={usingAi ? 'AI tailoring against verified profile facts...' : 'Applying rule-based tailoring...'} />}
          </div>
        </>
      )}

      {tailorResults.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Tailored Resumes</h2>
          {tailorResults.map((r, i) => <ResultCard key={i} r={r} />)}
        </div>
      )}
    </div>
  )
}
