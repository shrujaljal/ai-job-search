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
  const [customRole, setCustomRole] = useState('')
  const [cancelOpen, setCancelOpen] = useState(false)
  const selected = useMemo(() => new Set(draft.target_roles), [draft.target_roles])
  const knownRoles = useMemo(
    () => new Map(status.role_families.map((family) => [family.name.toLowerCase(), family.name])),
    [status.role_families],
  )
  const customTargets = useMemo(
    () => draft.target_roles.filter((role) => !knownRoles.has(role.toLowerCase())),
    [draft.target_roles, knownRoles],
  )

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
  const cancel = useMutation({
    mutationFn: api.cancelOnboarding,
    onSuccess: () => window.location.reload(),
  })

  const set = <K extends keyof OnboardingPayload,>(key: K, value: OnboardingPayload[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))
  const addCustomRole = () => {
    const role = customRole.replace(/\s+/g, ' ').trim()
    if (!role || draft.target_roles.length >= 20) return
    const existing = draft.target_roles.find((item) => item.toLowerCase() === role.toLowerCase())
    if (!existing) {
      const knownName = knownRoles.get(role.toLowerCase())
      set('target_roles', [...draft.target_roles, knownName ?? role])
    }
    setCustomRole('')
  }
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
                  {cancel.isError && <p className="text-sm text-rose-600">{cancel.error.message}</p>}
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
                  <div>
                    <Field label="Add your own target role">
                      <div className="flex gap-2">
                        <input className={inputCls} value={customRole}
                          onChange={(event) => setCustomRole(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                              event.preventDefault()
                              addCustomRole()
                            }
                          }}
                          maxLength={100} placeholder="e.g. Customer Experience Strategy" />
                        <Button type="button" variant="ghost"
                          disabled={!customRole.trim() || draft.target_roles.length >= 20}
                          onClick={addCustomRole}>Add role</Button>
                      </div>
                    </Field>
                    {customTargets.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2" aria-label="Custom target roles">
                        {customTargets.map((role) => (
                          <span key={role}
                            className="flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1.5 text-sm text-sky-800 dark:bg-sky-950 dark:text-sky-200">
                            {role}
                            <button type="button" title={`Remove ${role}`} aria-label={`Remove ${role}`}
                              className="text-base leading-none text-sky-600 hover:text-rose-600"
                              onClick={() => set('target_roles', draft.target_roles.filter((item) => item !== role))}>
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  {draft.target_roles.length === 0 && <p className="text-sm text-rose-600">Choose or add at least one target role.</p>}
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
                    Files are organized into company and role folders. Upload a master resume in Settings -&gt; Profile to set its section order and headings.
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
                        const provider = e.target.value
                        const models: Record<string, string> = {
                          openrouter: 'openrouter/free',
                          groq: 'openai/gpt-oss-20b',
                          ollama: 'gpt-oss:20b',
                          openai: 'gpt-4o',
                          claude: 'claude-sonnet-5',
                        }
                        setDraft((current) => ({ ...current, ai_provider: provider, ai_model: models[provider] }))
                      }}>
                        <optgroup label="Free options">
                          <option value="openrouter">OpenRouter Free</option>
                          <option value="groq">Groq Free Tier</option>
                          <option value="ollama">Ollama Local</option>
                        </optgroup>
                        <optgroup label="Paid options">
                          <option value="openai">OpenAI</option>
                          <option value="claude">Anthropic Claude</option>
                        </optgroup>
                      </select></Field>
                      <Field label="Model"><input className={inputCls} value={draft.ai_model} onChange={(e) => set('ai_model', e.target.value)} /></Field>
                      {draft.ai_provider !== 'ollama' && <div className="sm:col-span-2"><Field label="API key"><input type="password" className={inputCls} value={draft.ai_api_key} onChange={(e) => set('ai_api_key', e.target.value)} placeholder="Stored only on this computer" /></Field></div>}
                    </div>
                  )}
                  {!draft.ai_enabled && <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-950 dark:text-slate-300">You can enable a free hosted tier, local Ollama, or a paid provider later under Settings. Search, scoring, and resume generation work without an API key.</p>}
                  {complete.isError && <p className="text-sm text-rose-600">{complete.error.message}</p>}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <footer className="flex items-center justify-between border-t border-slate-200 px-5 py-4 dark:border-slate-800 sm:px-8">
          {step === 0 && status.can_cancel
            ? <Button variant="ghost" disabled={cancel.isPending}
                onClick={() => setCancelOpen(true)}>Cancel profile creation</Button>
            : <Button variant="ghost" disabled={step === 0 || complete.isPending}
                onClick={() => setStep((value) => value - 1)}>Back</Button>}
          {step < STEPS.length - 1
            ? <Button disabled={!canContinue || (step === 1 && draft.target_roles.length === 0)} onClick={() => setStep((value) => value + 1)}>Continue</Button>
            : <Button disabled={!canFinish || complete.isPending} onClick={() => complete.mutate()}>{complete.isPending ? 'Saving setup...' : 'Finish setup'}</Button>}
        </footer>
      </section>
      {cancelOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog" aria-modal="true" aria-labelledby="cancel-profile-title"
          onMouseDown={(event) => { if (event.target === event.currentTarget) setCancelOpen(false) }}>
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-slate-900">
            <h2 id="cancel-profile-title" className="text-lg font-semibold">Discard this profile?</h2>
            <p className="mt-2 text-sm text-slate-500">
              This unfinished profile will be removed and your previous profile will be restored.
            </p>
            {cancel.isError && <p className="mt-3 text-sm text-rose-600">{cancel.error.message}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" disabled={cancel.isPending}
                onClick={() => setCancelOpen(false)}>Keep profile</Button>
              <Button variant="danger" disabled={cancel.isPending}
                onClick={() => cancel.mutate()}>
                {cancel.isPending ? 'Discarding...' : 'Discard profile'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
