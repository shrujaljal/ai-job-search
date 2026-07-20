import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { Card, Button, EmptyState, ErrorState, PageLoading, inputCls } from '../components/ui'
import { STATUSES, type Application } from '../types'

function AddForm() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({ company: '', role: '', location: '', url: '', status: 'To Apply', notes: '' })
  const add = useMutation({
    mutationFn: api.addApplication,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['applications'] }); setF({ company: '', role: '', location: '', url: '', status: 'To Apply', notes: '' }); setOpen(false) },
  })
  if (!open) return <Button variant="ghost" onClick={() => setOpen(true)}>+ Add application</Button>
  return (
    <Card>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <input className={inputCls} placeholder="Company" value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })} />
        <input className={inputCls} placeholder="Role" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} />
        <input className={inputCls} placeholder="Location" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} />
        <input className={inputCls} placeholder="Job URL" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} />
        <select className={inputCls} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input className={inputCls} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
      </div>
      {add.isError && <p className="mt-2 text-sm text-red-600">{(add.error as Error).message}</p>}
      <div className="mt-3 flex gap-2">
        <Button disabled={!f.company || !f.role || add.isPending} onClick={() => add.mutate(f)}>Add</Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </Card>
  )
}

function Row({ app }: { app: Application }) {
  const qc = useQueryClient()
  const patch = useMutation({
    mutationFn: (fields: Partial<Application>) => api.patchApplication(app.id, fields),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications', 'dashboard'] }),
  })
  const del = useMutation({
    mutationFn: () => api.deleteApplication(app.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications', 'dashboard'] }),
  })
  return (
    <tr className="border-t border-slate-100 dark:border-slate-800">
      <td className="px-3 py-2 font-medium">{app.company}</td>
      <td className="px-3 py-2">{app.role}</td>
      <td className="px-3 py-2">
        <select className={`${inputCls} py-1`} value={app.status}
          onChange={(e) => patch.mutate({ status: e.target.value })}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </td>
      <td className="px-3 py-2 text-slate-500">{app.location}</td>
      <td className="px-3 py-2 text-slate-500">{app.date_added}</td>
      <td className="px-3 py-2">
        <input className={`${inputCls} py-1`} defaultValue={app.notes}
          onBlur={(e) => { if (e.target.value !== app.notes) patch.mutate({ notes: e.target.value }) }} />
      </td>
      <td className="px-3 py-2 text-right">
        {app.url && <a href={app.url} target="_blank" rel="noreferrer" className="mr-3 text-blue-600 hover:underline">Open</a>}
        <button className="text-red-500 hover:text-red-700" onClick={() => del.mutate()} title="Delete">🗑</button>
      </td>
    </tr>
  )
}

function exportCsv(apps: Application[]) {
  const cols = ['company', 'role', 'status', 'location', 'date_added', 'url', 'notes'] as const
  const rows = [cols.join(','), ...apps.map((a) => cols.map((c) => `"${String(a[c] ?? '').replace(/"/g, '""')}"`).join(','))]
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = 'applications.csv'; link.click()
  URL.revokeObjectURL(url)
}

export default function Tracker() {
  const applications = useQuery({ queryKey: ['applications'], queryFn: api.listApplications, retry: false })
  const apps = applications.data ?? []
  if (applications.isLoading) return <PageLoading label="Loading applications..." />
  if (applications.isError) return <ErrorState message={applications.error.message} onRetry={() => applications.refetch()} />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Application Tracker</h1>
        {apps.length > 0 && <Button variant="ghost" onClick={() => exportCsv(apps)}>⬇️ Export CSV</Button>}
      </div>
      <AddForm />
      {apps.length === 0 ? (
        <EmptyState title="No applications yet" description="Add a role manually above or tailor a résumé and send it here from the result." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-3 py-2">Company</th><th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Status</th><th className="px-3 py-2">Location</th>
                <th className="px-3 py-2">Added</th><th className="px-3 py-2">Notes</th><th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>{apps.map((a) => <Row key={a.id} app={a} />)}</tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
