import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { api, type OnboardingPayload, type OnboardingStatus } from '../api'
import { Button, Field, inputCls } from './ui'
import { Toggle } from '../settings/parts'

const STEPS = ['Profile', 'Targets', 'Output', 'AI']

export function Onboarding({ status }: { status: OnboardingStatus }) {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState<OnboardingPayload>(() => ({ ...status.defaults }))
  const [locations, setLocations] = useState(status.defaults.preferred_locations.join(', '))
  const selected = useMemo(() => new Set(draft.target_roles), [draft.target_roles])

  const complete = useMutation({
    mutationFn: () => api.completeOnboarding({
      ...draft,
      preferred_locations: locations.split(',').map((item) => item.trim()).filter(Boolean),
    }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['onboarding'] }),
        qc.invalidateQueries({ queryKey: ['settings'] }),
        qc.invalidateQueries({ queryKey: ['config'] }),
      ])
    },
  })

  const set = <K extends keyof OnboardingPayload,>(key: K, value: OnboardingPayload[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))
  const canContinue = step !== 0 || Boolean(draft.full_name.trim())
  const canFinish = draft.target_roles.length > 0 && Boolean(draft.full_name.trim())

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="themed min-w-0 w-full max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-900 sm:max-w-3xl">
        <header className="border-b border-slate-200 px-5 py-5 dark:border-slate-800 sm:px-8">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg font-bold text-white"
              style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>J</div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold">Set up Job Application Agent</h1>
              <p className="break-words text-sm text-slate-500">Configure the facts and targets used to score and tailor roles.</p>
            </div>
          </div>
          <ol className="mt-5 grid grid-cols-4 gap-2" aria-label="Setup progress">
            {STEPS.map((label, index) => (
              <li key={label}>
                <div className={`h-1.5 rounded-full ${index <= step ? '' : 'bg-slate-200 dark:bg-slate-700'}`}
                  style={index <= step ? { background: 'var(--accent)' } : undefined} />
                <span className={`mt-1.5 block text-xs ${index === step ? 'font-semibold text-slate-800 dark:text-white' : 'text-slate-400'}`}>{label}</span>
              </li>
            ))}
          </ol>
        </header>

        <div className="min-h-[390px] px-5 py-6 sm:px-8">
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }} transition={{ duration: 0.18 }}>
              {step === 0 && (
                <div className="space-y-5">
                  <div><h2 className="text-xl font-semibold">Your profile</h2><p className="mt-1 text-sm text-slate-500">These details become résumé facts. You can add experience and education in Settings afterward.</p></div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Full name"><input autoFocus className={inputCls} value={draft.full_name} onChange={(e) => set('full_name', e.target.value)} placeholder="Your full name" /></Field>
                    <Field label="Display name"><input className={inputCls} value={draft.display_name} onChange={(e) => set('display_name', e.target.value)} placeholder="First name or preferred name" /></Field>
                    <Field label="Location"><input className={inputCls} value={draft.location} onChange={(e) => set('location', e.target.value)} placeholder="City, State or country" /></Field>
                    <Field label="Work authorization"><input className={inputCls} value={draft.work_authorization} onChange={(e) => set('work_authorization', e.target.value)} placeholder="e.g. OPT through 2027" /></Field>
                  </div>
                  <Toggle checked={draft.needs_sponsorship} onChange={(value) => set('needs_sponsorship', value)} label="I need employment visa sponsorship" />
                </div>
              )}

              {step === 1 && (
                <div className="space-y-5">
                  <div><h2 className="text-xl font-semibold">Job targets</h2><p className="mt-1 text-sm text-slate-500">Selected role families receive highest scoring priority.</p></div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {status.role_families.map((family) => {
                      const checked = selected.has(family.name)
                      return (
                        <label key={family.name} className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm ${checked ? 'border-transparent text-white' : 'border-slate-200 dark:border-slate-700'}`}
                          style={checked ? { background: 'var(--accent)' } : undefined}>
                          <input type="checkbox" className="h-4 w-4" checked={checked} onChange={() => set('target_roles', checked
                            ? draft.target_roles.filter((name) => name !== family.name)
                            : [...draft.target_roles, family.name])} />
                          {family.name}
                        </label>
                      )
                    })}
                  </div>
                  {draft.target_roles.length === 0 && <p className="text-sm text-rose-600">Choose at least one role family.</p>}
                  <div className="grid gap-4 sm:grid-cols-[1fr_180px]">
                    <Field label="Preferred locations (comma-separated)"><input className={inputCls} value={locations} onChange={(e) => setLocations(e.target.value)} placeholder="California, New York, Remote" /></Field>
                    <Field label="Maximum experience requested"><input type="number" min={0} max={30} className={inputCls} value={draft.max_years_experience} onChange={(e) => set('max_years_experience', Number(e.target.value))} /></Field>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-5">
                  <div><h2 className="text-xl font-semibold">Generated files</h2><p className="mt-1 text-sm text-slate-500">Choose where tailored DOCX and PDF files are stored.</p></div>
                  <Field label="Output folder">
                    <input autoFocus className={inputCls} value={draft.output_dir} onChange={(e) => set('output_dir', e.target.value)} placeholder="Leave blank for ~/JobApplications" />
                  </Field>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
                    Files are organized into company and role folders. The built-in résumé template is active; custom DOCX templates can be uploaded later in Settings.
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-5">
                  <div><h2 className="text-xl font-semibold">AI-assisted tailoring</h2><p className="mt-1 text-sm text-slate-500">Optional. The offline rule-based engine remains available and is always the fallback.</p></div>
                  <Toggle checked={draft.ai_enabled} onChange={(value) => set('ai_enabled', value)} label="Enable AI-assisted tailoring" />
                  {draft.ai_enabled && (
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Field label="Provider"><select className={inputCls} value={draft.ai_provider} onChange={(e) => {
                        const provider = e.target.value as 'claude' | 'openai'
                        setDraft((current) => ({ ...current, ai_provider: provider, ai_model: provider === 'claude' ? 'claude-sonnet-5' : 'gpt-4o' }))
                      }}><option value="claude">Anthropic (Claude)</option><option value="openai">OpenAI</option></select></Field>
                      <Field label="Model"><input className={inputCls} value={draft.ai_model} onChange={(e) => set('ai_model', e.target.value)} /></Field>
                      <div className="sm:col-span-2"><Field label="API key"><input type="password" className={inputCls} value={draft.ai_api_key} onChange={(e) => set('ai_api_key', e.target.value)} placeholder="Stored only on this computer" /></Field></div>
                    </div>
                  )}
                  {!draft.ai_enabled && <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-950 dark:text-slate-300">You can enable Claude or OpenAI later under Settings. Search, scoring, and résumé generation work without an API key.</p>}
                  {complete.isError && <p className="text-sm text-rose-600">{complete.error.message}</p>}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <footer className="flex items-center justify-between border-t border-slate-200 px-5 py-4 dark:border-slate-800 sm:px-8">
          <Button variant="ghost" disabled={step === 0 || complete.isPending} onClick={() => setStep((value) => value - 1)}>Back</Button>
          {step < STEPS.length - 1
            ? <Button disabled={!canContinue || (step === 1 && draft.target_roles.length === 0)} onClick={() => setStep((value) => value + 1)}>Continue</Button>
            : <Button disabled={!canFinish || complete.isPending} onClick={() => complete.mutate()}>{complete.isPending ? 'Saving setup...' : 'Finish setup'}</Button>}
        </footer>
      </section>
    </main>
  )
}
