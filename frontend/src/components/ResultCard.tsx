import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { Card, Button } from './ui'
import type { TailorResult } from '../types'

export function ResultCard({ r }: { r: TailorResult }) {
  const qc = useQueryClient()
  const add = useMutation({
    mutationFn: () => api.addApplication({
      company: r.company, role: r.role, status: 'To Apply',
      notes: r.family ? `Resume tailored (${r.family})` : '',
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications', 'dashboard'] }),
  })

  if (r.blocked) {
    return (
      <Card className="border-red-200 dark:border-red-900">
        <p className="text-sm text-red-700 dark:text-red-300">
          ⛔ <b>{r.company} — {r.role}</b>: skipped — no sponsorship for you ({r.block_reason}).
          Verify in the posting before ruling it out.
        </p>
      </Card>
    )
  }
  if (!r.ok) {
    return <Card className="border-red-200"><p className="text-sm text-red-600">❌ {r.company} — {r.role}: failed.</p></Card>
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold">✅ {r.company} — {r.role}</h3>
          <p className="text-sm text-slate-500">Role family: {r.family}</p>
        </div>
        {add.isSuccess
          ? <span className="text-sm font-medium text-emerald-600">✓ In tracker</span>
          : <Button variant="ghost" disabled={add.isPending} onClick={() => add.mutate()}>➕ Add to Tracker</Button>}
      </div>

      {r.out_dir && <p className="mt-2 text-xs text-slate-500">Saved to <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">{r.out_dir}</code></p>}
      {r.sponsorship_warning && <p className="mt-2 text-sm text-amber-600">⚠️ Sponsorship note: {r.sponsorship_warning}</p>}
      {r.exp_warning && <p className="mt-1 text-sm text-amber-600">⚠️ {r.exp_warning}</p>}
      {r.pdf_error && <p className="mt-1 text-sm text-amber-600">PDF not created (install LibreOffice or MS Word). The DOCX is saved.</p>}
      {r.warnings && r.warnings.length > 0 && <p className="mt-1 text-xs text-slate-500">Trimmed to one page: {r.warnings.join('; ')}</p>}

      <div className="mt-3 flex gap-2">
        {r.docx_path && <a className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800" href={api.downloadUrl(r.docx_path)}>⬇️ DOCX</a>}
        {r.pdf_path && <a className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800" href={api.downloadUrl(r.pdf_path)}>⬇️ PDF</a>}
      </div>
    </Card>
  )
}
