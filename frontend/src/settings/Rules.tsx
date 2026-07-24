import { useEffect, useState } from 'react'
import { inputCls, Field } from '../components/ui'
import { Section, SaveBar } from './parts'
import { Repeater, TagList, Sub } from './fields'
import { useConfig } from './useConfig'

interface Family { name: string; tier: number; keywords: string[] }
interface Blocker { label: string; pattern: string }
interface Weights {
  tier_base: Record<string, number>
  target_company_bonus: number
  remote_bonus: number
  preferred_location_bonus: number
  acceptable_location_bonus: number
  very_senior_penalty: number
  mid_senior_penalty: number
  over_experience_penalty: number
  red_flag_penalty: number
  sponsorship_penalty: number
  title_weight_multiplier: number
}
interface Tiers { strong: number; good: number; moderate: number }
interface Rules {
  role_families: Family[]
  target_companies: string[]
  preferred_locations: string[]
  acceptable_locations: string[]
  remote_hints: string[]
  hard_red_flags: string[]
  very_senior_terms: string[]
  mid_senior_terms: string[]
  max_years_experience: number
  sponsorship_blockers: Blocker[]
  weights: Weights
  tiers: Tiers
}

function NumberField({ label, value, onChange }: {
  label: string; value: number; onChange: (value: number) => void
}) {
  return <Field label={label}><input type="number" className={inputCls} value={value}
    onChange={(event) => onChange(Number(event.target.value) || 0)} /></Field>
}

const priorityLabel: Record<number, string> = {
  1: 'High priority',
  2: 'Medium priority',
  3: 'Low priority',
}

export function RulesEditor() {
  const { data, save, reset } = useConfig<Rules>('rules')
  const [draft, setDraft] = useState<Rules | null>(null)
  useEffect(() => { if (data && !draft) setDraft(structuredClone(data)) }, [data, draft])
  if (!draft) return <p className="text-sm text-slate-500">Loading...</p>

  const dirty = JSON.stringify(draft) !== JSON.stringify(data)
  const setWeights = (patch: Partial<Weights>) =>
    setDraft({ ...draft, weights: { ...draft.weights, ...patch } })
  const setTiers = (patch: Partial<Tiers>) =>
    setDraft({ ...draft, tiers: { ...draft.tiers, ...patch } })
  const doReset = async () => {
    if (!confirm('Reset job preferences to the shipped default?')) return
    setDraft(structuredClone(await reset.mutateAsync()))
  }

  return (
    <Section title="Job Preferences"
      desc="Define the roles, companies, and locations you want. These preferences rank search results automatically.">
      <div className="space-y-5 rounded-lg border border-slate-200 p-5 dark:border-slate-800">
        <div>
          <h2 className="text-sm font-semibold">Target roles</h2>
          <p className="mt-1 text-xs text-slate-500">Add role families and set their priority.</p>
          <div className="mt-3">
            <Repeater<Family> items={draft.role_families}
              onChange={(role_families) => setDraft({ ...draft, role_families })}
              empty={() => ({ name: '', tier: 1, keywords: [] })} addLabel="Add target role"
              render={(family, update) => (
                <>
                  <div className="grid gap-2 md:grid-cols-[1fr_190px]">
                    <input className={inputCls} placeholder="Strategy & Operations" value={family.name}
                      onChange={(event) => update({ name: event.target.value })} />
                    <select className={inputCls} value={family.tier}
                      onChange={(event) => update({ tier: Number(event.target.value) })}>
                      {[1, 2, 3].map((tier) =>
                        <option key={tier} value={tier}>{priorityLabel[tier]}</option>)}
                    </select>
                  </div>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-slate-500">Matching keywords</summary>
                    <div className="mt-2">
                      <TagList value={family.keywords} onChange={(keywords) => update({ keywords })}
                        placeholder="Add a job-title keyword" />
                    </div>
                  </details>
                </>
              )} />
          </div>
        </div>

        <div className="grid gap-5 border-t border-slate-200 pt-5 md:grid-cols-2 dark:border-slate-800">
          <Sub label="Preferred companies">
            <TagList value={draft.target_companies}
              onChange={(target_companies) => setDraft({ ...draft, target_companies })}
              placeholder="Add a company" />
          </Sub>
          <Sub label="Preferred locations">
            <TagList value={draft.preferred_locations}
              onChange={(preferred_locations) => setDraft({ ...draft, preferred_locations })}
              placeholder="Add a city, state, or remote" />
          </Sub>
        </div>

        <div className="max-w-xs border-t border-slate-200 pt-5 dark:border-slate-800">
          <NumberField label="Maximum requested years of experience"
            value={draft.max_years_experience}
            onChange={(max_years_experience) => setDraft({ ...draft, max_years_experience })} />
        </div>
      </div>

      <details className="rounded-lg border border-slate-200 dark:border-slate-800">
        <summary className="cursor-pointer px-5 py-4 text-sm font-semibold">Advanced scoring</summary>
        <div className="space-y-5 border-t border-slate-200 p-5 dark:border-slate-800">
          <div className="grid gap-4 md:grid-cols-2">
            <Sub label="Acceptable locations"><TagList value={draft.acceptable_locations}
              onChange={(acceptable_locations) => setDraft({ ...draft, acceptable_locations })} /></Sub>
            <Sub label="Remote wording"><TagList value={draft.remote_hints}
              onChange={(remote_hints) => setDraft({ ...draft, remote_hints })} /></Sub>
            <Sub label="Roles to avoid"><TagList value={draft.hard_red_flags}
              onChange={(hard_red_flags) => setDraft({ ...draft, hard_red_flags })} /></Sub>
            <Sub label="Very senior terms"><TagList value={draft.very_senior_terms}
              onChange={(very_senior_terms) => setDraft({ ...draft, very_senior_terms })} /></Sub>
            <Sub label="Mid-senior terms"><TagList value={draft.mid_senior_terms}
              onChange={(mid_senior_terms) => setDraft({ ...draft, mid_senior_terms })} /></Sub>
          </div>

          <Sub label="Sponsorship blockers">
            <Repeater<Blocker> items={draft.sponsorship_blockers}
              onChange={(sponsorship_blockers) => setDraft({ ...draft, sponsorship_blockers })}
              empty={() => ({ label: '', pattern: '' })} addLabel="Add blocker"
              render={(blocker, update) => (
                <div className="grid gap-2 md:grid-cols-2">
                  <input className={inputCls} placeholder="Label" value={blocker.label}
                    onChange={(event) => update({ label: event.target.value })} />
                  <input className={inputCls} placeholder="Matching phrase or pattern" value={blocker.pattern}
                    onChange={(event) => update({ pattern: event.target.value })} />
                </div>
              )} />
          </Sub>

          <div>
            <h3 className="text-sm font-semibold">Score weights</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {([
                ['Target company bonus', 'target_company_bonus'],
                ['Remote bonus', 'remote_bonus'],
                ['Preferred location bonus', 'preferred_location_bonus'],
                ['Acceptable location bonus', 'acceptable_location_bonus'],
                ['Very senior penalty', 'very_senior_penalty'],
                ['Mid-senior penalty', 'mid_senior_penalty'],
                ['Experience penalty', 'over_experience_penalty'],
                ['Avoided role penalty', 'red_flag_penalty'],
                ['Sponsorship penalty', 'sponsorship_penalty'],
                ['Title match multiplier', 'title_weight_multiplier'],
              ] as [string, keyof Omit<Weights, 'tier_base'>][]).map(([label, key]) =>
                <NumberField key={key} label={label} value={draft.weights[key]}
                  onChange={(value) => setWeights({ [key]: value })} />)}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold">Fit thresholds</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <NumberField label="Strong" value={draft.tiers.strong}
                onChange={(strong) => setTiers({ strong })} />
              <NumberField label="Good" value={draft.tiers.good}
                onChange={(good) => setTiers({ good })} />
              <NumberField label="Moderate" value={draft.tiers.moderate}
                onChange={(moderate) => setTiers({ moderate })} />
            </div>
          </div>
        </div>
      </details>

      <div className="flex items-center justify-between">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess}
          onSave={() => save.mutate(draft)} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
