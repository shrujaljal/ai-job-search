import { useEffect, useState } from 'react'
import { Field, inputCls } from '../components/ui'
import { Section, SaveBar } from './parts'
import { useSettings } from './useSettings'
import type { Settings } from '../api'

export function Account() {
  const { settings, save } = useSettings()
  const [draft, setDraft] = useState<Settings | null>(null)
  useEffect(() => { if (settings && !draft) setDraft(settings) }, [settings, draft])
  if (!draft) return <p className="text-sm text-slate-500">Loading…</p>

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)
  const set = (k: keyof Settings, v: string) => setDraft({ ...draft, [k]: v })

  return (
    <Section title="Account" desc="Basic details used across the app and on your résumé.">
      <Field label="Display name (used to greet you)">
        <input className={inputCls} value={draft.username} onChange={(e) => set('username', e.target.value)}
          placeholder="e.g. Shrujal" />
      </Field>
      <Field label="Full name (used on the résumé header / PDF filename)">
        <input className={inputCls} value={draft.candidate_name} onChange={(e) => set('candidate_name', e.target.value)}
          placeholder="e.g. Shrujal Agarwal" />
      </Field>
      <Field label="Output folder for generated résumés (leave blank for the default)">
        <input className={inputCls} value={draft.output_dir} onChange={(e) => set('output_dir', e.target.value)}
          placeholder="e.g. C:\Users\you\JobApplications" />
      </Field>
      <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess}
        onSave={() => save.mutate(draft)} />
    </Section>
  )
}
