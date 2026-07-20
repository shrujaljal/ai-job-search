import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, Button, Field, inputCls, Spinner } from '../components/ui'
import { ResultCard } from '../components/ResultCard'
import type { TailorResult } from '../types'

export default function PasteJD() {
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [jd, setJd] = useState('')
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const usingAi = Boolean(settings.data?.llm.enabled)

  const tailor = useMutation<TailorResult, Error>({
    mutationFn: () => api.tailor({ company, role, jd_text: jd, enforce_sponsorship: false }),
  })

  const disabled = !company.trim() || !role.trim() || !jd.trim() || tailor.isPending

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold">Tailor from a Pasted JD</h1>
      <p className="text-sm text-slate-500">
        For a role you found elsewhere. Paste the description, add the company and title, and generate a tailored résumé.
      </p>

      <Card className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Company"><input className={inputCls} value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Stripe" /></Field>
          <Field label="Role / Job title"><input className={inputCls} value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Strategy & Operations Manager" /></Field>
        </div>
        <Field label="Job description">
          <textarea className={inputCls} rows={10} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the full job description here…" />
        </Field>
        <div className="flex items-center gap-3">
          <Button disabled={disabled} onClick={() => tailor.mutate()}>🎯 Generate Tailored Resume</Button>
          {tailor.isPending && <Spinner label={usingAi ? 'AI is matching the JD to verified profile facts...' : 'Applying rule-based tailoring...'} />}
        </div>
        {tailor.isError && <p className="text-sm text-red-600">{tailor.error.message}</p>}
      </Card>

      {tailor.data && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Tailored Resume</h2>
          <ResultCard r={tailor.data} />
        </div>
      )}
    </div>
  )
}
