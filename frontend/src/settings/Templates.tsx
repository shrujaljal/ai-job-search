import { useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type ResumeTemplate } from '../api'
import { Button } from '../components/ui'
import { Section } from './parts'

function fmtBytes(size: number) {
  if (!size) return 'Built in'
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function TokenPill({ children, tone = 'slate' }: { children: string; tone?: 'slate' | 'rose' | 'emerald' }) {
  const cls = tone === 'rose'
    ? 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
    : tone === 'emerald'
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
      : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>
}

function TemplateRow({ item, onActivate, onDelete, busy }: {
  item: ResumeTemplate
  onActivate: (id: string) => void
  onDelete: (id: string) => void
  busy?: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold">{item.name}</h2>
            {item.active && <TokenPill tone="emerald">Active</TokenPill>}
            {item.builtin && <TokenPill>Default</TokenPill>}
            {!item.valid && <TokenPill tone="rose">Missing tokens</TokenPill>}
          </div>
          <p className="mt-1 text-sm text-slate-500">{fmtBytes(item.size)}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" disabled={busy || item.active || !item.valid} onClick={() => onActivate(item.id)}>
            Use
          </Button>
          {!item.builtin && (
            <Button variant="danger" disabled={busy} onClick={() => onDelete(item.id)}>
              Delete
            </Button>
          )}
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {item.missing_tokens.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-rose-400">Missing required</div>
            <div className="flex flex-wrap gap-1.5">
              {item.missing_tokens.map((t) => <TokenPill key={t} tone="rose">{`{{${t}}}`}</TokenPill>)}
            </div>
          </div>
        )}
        {item.recognized_tokens.length > 0 && !item.builtin && (
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Found tokens</div>
            <div className="flex flex-wrap gap-1.5">
              {item.recognized_tokens.map((t) => <TokenPill key={t}>{`{{${t}}}`}</TokenPill>)}
            </div>
          </div>
        )}
        {item.unknown_tokens.length > 0 && (
          <p className="text-sm text-amber-600">
            Unknown tokens will be left blank: {item.unknown_tokens.map((t) => `{{${t}}}`).join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}

export function Templates() {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['templates'], queryFn: api.listTemplates, retry: false })
  const invalidate = () => qc.invalidateQueries({ queryKey: ['templates'] })

  const upload = useMutation({
    mutationFn: api.uploadTemplate,
    onSuccess: invalidate,
  })
  const activate = useMutation({
    mutationFn: api.setActiveTemplate,
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
  })
  const remove = useMutation({
    mutationFn: api.deleteTemplate,
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const busy = upload.isPending || activate.isPending || remove.isPending
  const error = q.error || upload.error || activate.error || remove.error

  return (
    <Section title="Templates"
      desc="Use the built-in resume design or upload a DOCX template with placeholder tokens. Uploaded templates are stored locally.">
      <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-base font-semibold">Upload DOCX template</h2>
            <p className="mt-1 text-sm text-slate-500">
              Required tokens: {q.data?.required_tokens.map((t) => `{{${t}}}`).join(', ') || 'loading...'}
            </p>
          </div>
          <div className="flex gap-2">
            <input ref={inputRef} className="hidden" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) upload.mutate(file)
                e.currentTarget.value = ''
              }} />
            <Button disabled={busy} onClick={() => inputRef.current?.click()}>
              {upload.isPending ? 'Uploading...' : 'Upload .docx'}
            </Button>
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{(error as Error).message}</p>}
      </div>

      {q.isLoading ? (
        <p className="text-sm text-slate-500">Loading templates...</p>
      ) : (
        <div className="space-y-3">
          {(q.data?.templates ?? []).map((item) => (
            <TemplateRow key={item.id} item={item} busy={busy}
              onActivate={(id) => activate.mutate(id)}
              onDelete={(id) => {
                if (confirm('Delete this uploaded template?')) remove.mutate(id)
              }} />
          ))}
        </div>
      )}

      <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300">
        Optional tokens: {q.data?.known_tokens.filter((t) => !q.data?.required_tokens.includes(t)).map((t) => `{{${t}}}`).join(', ') || 'loading...'}
      </div>
    </Section>
  )
}
