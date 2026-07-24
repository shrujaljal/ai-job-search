import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { Button, Card, EmptyState, ErrorState, Field, inputCls, ScoreBar, Spinner, TierBadge } from '../components/ui'
import type { CompanySource, TargetCompanyJob, TargetCompanyResponse } from '../types'

interface TargetCompanyConfig {
  sites: CompanySource[]
  recent_days: number
  minimum_fit_score: number
}

const emptySource = (): CompanySource => ({ name: '', url: '', enabled: true })
const jobKey = (job: TargetCompanyJob) => job.url || `${job.company}@@${job.title}`

export default function TargetCompanies() {
  const queryClient = useQueryClient()
  const saved = useQuery({
    queryKey: ['target-companies'],
    queryFn: () => api.getConfig<TargetCompanyConfig>('target_companies'),
  })
  const [sites, setSites] = useState<CompanySource[]>([])
  const [draft, setDraft] = useState<CompanySource>(emptySource)
  const [recentDays, setRecentDays] = useState(14)
  const [relevantOnly, setRelevantOnly] = useState(true)
  const [tracked, setTracked] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!saved.data) return
    setSites(saved.data.sites ?? [])
    setRecentDays(saved.data.recent_days ?? 14)
    setRelevantOnly((saved.data.minimum_fit_score ?? 45) > 0)
  }, [saved.data])

  const payload = {
    sites,
    recent_days: recentDays,
    minimum_fit_score: relevantOnly ? 45 : 0,
  }
  const search = useMutation<TargetCompanyResponse, Error>({
    mutationFn: () => api.searchTargetCompanies(payload),
    onSuccess: (data) => {
      setTracked(new Set(data.jobs.filter((job) => job.tracked).map(jobKey)))
      queryClient.invalidateQueries({ queryKey: ['target-companies'] })
    },
  })
  const save = useMutation({
    mutationFn: () => api.putConfig('target_companies', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['target-companies'] }),
  })
  const addToTracker = useMutation({
    mutationFn: (job: TargetCompanyJob) => api.addApplication({
      company: job.company,
      role: job.title,
      location: job.location ?? '',
      url: job.url ?? '',
      status: 'To Apply',
    }),
    onSuccess: (_row, job) => {
      setTracked((current) => new Set(current).add(jobKey(job)))
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
    },
  })

  const addSource = () => {
    const name = draft.name.trim()
    const url = draft.url.trim()
    if (!name || !url) return
    setSites((current) => [...current, { name, url, enabled: true }])
    setDraft(emptySource())
  }

  if (saved.isLoading) return <Spinner label="Loading company sources..." />
  if (saved.isError) return <ErrorState message={saved.error.message} onRetry={() => saved.refetch()} />

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-2xl font-semibold">Target Company Jobs</h1>
        <div className="flex w-full gap-2 sm:w-auto">
          <Button variant="ghost" disabled={save.isPending} onClick={() => save.mutate()}>Save sources</Button>
          <Button disabled={!sites.some((site) => site.enabled) || search.isPending} onClick={() => search.mutate()}>
            Search companies
          </Button>
        </div>
      </div>

      <section className="space-y-3">
        {sites.map((site, index) => (
          <Card key={`${site.url}-${index}`} className="grid gap-3 p-4 md:grid-cols-[auto_1fr_2fr_auto] md:items-center">
            <input
              type="checkbox"
              aria-label={`Enable ${site.name}`}
              checked={site.enabled}
              onChange={(event) => setSites((current) => current.map((item, i) => (
                i === index ? { ...item, enabled: event.target.checked } : item
              )))}
            />
            <input
              aria-label="Company name"
              className={inputCls}
              value={site.name}
              onChange={(event) => setSites((current) => current.map((item, i) => (
                i === index ? { ...item, name: event.target.value } : item
              )))}
            />
            <input
              aria-label="Career site URL"
              className={inputCls}
              value={site.url}
              onChange={(event) => setSites((current) => current.map((item, i) => (
                i === index ? { ...item, url: event.target.value } : item
              )))}
            />
            <Button variant="danger" onClick={() => setSites((current) => current.filter((_, i) => i !== index))}>
              Remove
            </Button>
          </Card>
        ))}

        <div className="grid gap-3 rounded-lg border border-dashed border-slate-300 p-4 dark:border-slate-700 md:grid-cols-[1fr_2fr_auto] md:items-end">
          <Field label="Company">
            <input className={inputCls} value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Company name" />
          </Field>
          <Field label="Career site">
            <input className={inputCls} type="url" value={draft.url}
              onChange={(event) => setDraft({ ...draft, url: event.target.value })} placeholder="https://..." />
          </Field>
          <Button variant="ghost" disabled={!draft.name.trim() || !draft.url.trim()} onClick={addSource}>Add company</Button>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-6 rounded-lg border-y border-slate-200 py-3 text-sm dark:border-slate-800">
        <label className="flex items-center gap-3">
          <span className="font-medium">Posted within</span>
          <input type="range" min={1} max={60} value={recentDays}
            onChange={(event) => setRecentDays(Number(event.target.value))} />
          <span className="w-16 tabular-nums text-slate-500">{recentDays} days</span>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={relevantOnly}
            onChange={(event) => setRelevantOnly(event.target.checked)} />
          Relevant roles only
        </label>
        {search.isPending && <Spinner label="Reading career sites..." />}
      </div>

      {save.isSuccess && <p className="text-sm text-emerald-600">Sources saved.</p>}
      {save.isError && <p className="text-sm text-rose-600">{save.error.message}</p>}
      {search.isError && <ErrorState message={search.error.message} />}
      {search.data?.errors.map((error) => (
        <p key={error.name} className="text-sm text-amber-700 dark:text-amber-300">
          {error.name}: {error.message}
        </p>
      ))}

      {search.data && (
        <>
          <p className="text-sm text-slate-500">
            {search.data.counts.total} roles from {search.data.counts.sources} sources
            {' '}· {search.data.counts.applied} already applied · {search.data.counts.tracked} tracked
          </p>
          {search.data.jobs.length === 0 ? (
            <EmptyState title="No matching roles found"
              description="Try a wider date range, include all fit scores, or verify the career-site URLs." />
          ) : (
            <Card className="overflow-x-auto p-0">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Fit</th>
                    <th className="px-3 py-2">Role</th>
                    <th className="px-3 py-2">Company</th>
                    <th className="px-3 py-2">Location</th>
                    <th className="px-3 py-2">Posted</th>
                    <th className="px-3 py-2">Tracker</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {search.data.jobs.map((job) => {
                    const isTracked = tracked.has(jobKey(job))
                    return (
                      <tr key={jobKey(job)} className="border-t border-slate-100 dark:border-slate-800">
                        <td className="px-3 py-3">
                          <ScoreBar score={job.score} />
                          <div className="mt-1"><TierBadge tier={job.tier} /></div>
                        </td>
                        <td className="max-w-xs px-3 py-3 font-medium">{job.title}</td>
                        <td className="px-3 py-3">{job.company}</td>
                        <td className="px-3 py-3 text-slate-500">{job.location || 'Not listed'}</td>
                        <td className="px-3 py-3 text-slate-500">
                          {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : 'Date unavailable'}
                        </td>
                        <td className="px-3 py-3">
                          {job.already_applied ? (
                            <span className="font-semibold text-emerald-600">{job.application_status}</span>
                          ) : isTracked ? (
                            <span className="font-medium text-sky-600">{job.application_status || 'To Apply'}</span>
                          ) : (
                            <Button variant="ghost" disabled={addToTracker.isPending}
                              onClick={() => addToTracker.mutate(job)}>Track</Button>
                          )}
                        </td>
                        <td className="px-3 py-3 text-right">
                          {job.url && (
                            <a href={job.url} target="_blank" rel="noreferrer"
                              className="font-medium text-blue-600 hover:underline">
                              {job.already_applied ? 'View again' : 'Open'}
                            </a>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
