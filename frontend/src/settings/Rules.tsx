import { useEffect, useState, type ReactNode } from 'react'
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

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details open className="rounded-2xl border border-slate-200 dark:border-slate-800">
      <summary className="cursor-pointer select-none px-4 py-3 font-semibold">{title}</summary>
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">{children}</div>
    </details>
  )
}

function Num({ label, value, onChange, hint }: {
  label: string; value: number; onChange: (v: number) => void; hint?: string
}) {
  return (
    <Field label={label}>
      <input type="number" className={inputCls} value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(e.target.value === '' ? 0 : Number(e.target.value))} />
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </Field>
  )
}

const TIER_LABEL: Record<number, string> = { 1: 'Tier 1 · Priority', 2: 'Tier 2 · Secondary', 3: 'Tier 3 · Fallback' }

export function RulesEditor() {
  const { data, save, reset } = useConfig<Rules>('rules')
  const [d, setD] = useState<Rules | null>(null)
  // Initialize the draft once; background refetches won't clobber in-progress edits.
  useEffect(() => { if (data && !d) setD(structuredClone(data)) }, [data, d])
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>

  const doReset = async () => {
    if (!confirm('Reset the scoring rules to the shipped default? Your edits will be lost.')) return
    const fresh = await reset.mutateAsync()
    setD(structuredClone(fresh))
  }

  const dirty = JSON.stringify(d) !== JSON.stringify(data)
  const w = d.weights
  const setW = (patch: Partial<Weights>) => setD({ ...d, weights: { ...w, ...patch } })
  const setTierBase = (k: string, v: number) => setW({ tier_base: { ...w.tier_base, [k]: v } })
  const t = d.tiers
  const setT = (patch: Partial<Tiers>) => setD({ ...d, tiers: { ...t, ...patch } })

  return (
    <Section title="Scoring Rules" desc="How incoming jobs are scored and ranked. These drive the Search results and fit tiers.">
      <Group title="Role families">
        <p className="mb-3 text-sm text-slate-500">
          Titles are matched against each family's keywords. Tier sets the base score; the best-matching family wins.
        </p>
        <Repeater<Family> items={d.role_families} onChange={(role_families) => setD({ ...d, role_families })}
          empty={() => ({ name: '', tier: 1, keywords: [] })} addLabel="Add role family"
          render={(f, up) => (
            <>
              <div className="grid gap-2 md:grid-cols-[1fr_200px]">
                <input className={inputCls} placeholder="Family name (e.g. Strategy & Operations)" value={f.name} onChange={(e) => up({ name: e.target.value })} />
                <select className={inputCls} value={f.tier} onChange={(e) => up({ tier: Number(e.target.value) })}>
                  {[1, 2, 3].map((n) => <option key={n} value={n}>{TIER_LABEL[n]}</option>)}
                </select>
              </div>
              <div className="mt-3">
                <Sub label="Keywords (matched in job titles/descriptions)">
                  <TagList value={f.keywords} onChange={(keywords) => up({ keywords })} placeholder="Add a keyword, press Enter" />
                </Sub>
              </div>
            </>
          )} />
      </Group>

      <Group title="Target companies">
        <p className="mb-3 text-sm text-slate-500">Jobs at these companies get a bonus. Case-insensitive substring match.</p>
        <TagList value={d.target_companies} onChange={(target_companies) => setD({ ...d, target_companies })} placeholder="Add a company, press Enter" />
      </Group>

      <Group title="Locations">
        <Sub label="Preferred locations (full bonus)">
          <TagList value={d.preferred_locations} onChange={(preferred_locations) => setD({ ...d, preferred_locations })} placeholder="e.g. california, remote" />
        </Sub>
        <Sub label="Acceptable locations (smaller bonus)">
          <TagList value={d.acceptable_locations} onChange={(acceptable_locations) => setD({ ...d, acceptable_locations })} placeholder="e.g. chicago, denver" />
        </Sub>
        <Sub label="Remote hints (words that signal a remote role)">
          <TagList value={d.remote_hints} onChange={(remote_hints) => setD({ ...d, remote_hints })} placeholder="e.g. remote, anywhere, hybrid" />
        </Sub>
      </Group>

      <Group title="Red flags & seniority">
        <Sub label="Hard red-flag titles (heavily penalized — wrong role type)">
          <TagList value={d.hard_red_flags} onChange={(hard_red_flags) => setD({ ...d, hard_red_flags })} placeholder="e.g. software engineer, data scientist" />
        </Sub>
        <Sub label="Very-senior terms (large penalty)">
          <TagList value={d.very_senior_terms} onChange={(very_senior_terms) => setD({ ...d, very_senior_terms })} placeholder="e.g. director, vice president" />
        </Sub>
        <Sub label="Mid-senior terms (smaller penalty)">
          <TagList value={d.mid_senior_terms} onChange={(mid_senior_terms) => setD({ ...d, mid_senior_terms })} placeholder="e.g. senior, staff, lead" />
        </Sub>
        <div className="mt-2 max-w-xs">
          <Num label="Max years of experience" value={d.max_years_experience}
            onChange={(v) => setD({ ...d, max_years_experience: v })}
            hint="Roles asking for more than this are penalized and flagged." />
        </div>
      </Group>

      <Group title="Sponsorship blockers">
        <p className="mb-3 text-sm text-slate-500">
          Regex patterns that flag a job as requiring citizenship / no-sponsorship. Matched (case-insensitive) against the
          job description. Advanced — edit the pattern only if you know regex.
        </p>
        <Repeater<Blocker> items={d.sponsorship_blockers} onChange={(sponsorship_blockers) => setD({ ...d, sponsorship_blockers })}
          empty={() => ({ label: '', pattern: '' })} addLabel="Add blocker"
          render={(b, up) => (
            <div className="grid gap-2 md:grid-cols-2">
              <input className={inputCls} placeholder="Label (shown to you)" value={b.label} onChange={(e) => up({ label: e.target.value })} />
              <input className={`${inputCls} font-mono`} placeholder="Regex pattern" value={b.pattern} onChange={(e) => up({ pattern: e.target.value })} />
            </div>
          )} />
      </Group>

      <Group title="Score weights">
        <p className="mb-3 text-sm text-slate-500">Points added or subtracted. Negative values are penalties.</p>
        <Sub label="Tier base scores">
          <div className="grid gap-3 sm:grid-cols-4">
            <Num label="Tier 1" value={w.tier_base['1']} onChange={(v) => setTierBase('1', v)} />
            <Num label="Tier 2" value={w.tier_base['2']} onChange={(v) => setTierBase('2', v)} />
            <Num label="Tier 3" value={w.tier_base['3']} onChange={(v) => setTierBase('3', v)} />
            <Num label="Unknown" value={w.tier_base['unknown']} onChange={(v) => setTierBase('unknown', v)} />
          </div>
        </Sub>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Num label="Target company bonus" value={w.target_company_bonus} onChange={(v) => setW({ target_company_bonus: v })} />
          <Num label="Remote bonus" value={w.remote_bonus} onChange={(v) => setW({ remote_bonus: v })} />
          <Num label="Preferred location bonus" value={w.preferred_location_bonus} onChange={(v) => setW({ preferred_location_bonus: v })} />
          <Num label="Acceptable location bonus" value={w.acceptable_location_bonus} onChange={(v) => setW({ acceptable_location_bonus: v })} />
          <Num label="Very-senior penalty" value={w.very_senior_penalty} onChange={(v) => setW({ very_senior_penalty: v })} />
          <Num label="Mid-senior penalty" value={w.mid_senior_penalty} onChange={(v) => setW({ mid_senior_penalty: v })} />
          <Num label="Over-experience penalty" value={w.over_experience_penalty} onChange={(v) => setW({ over_experience_penalty: v })} />
          <Num label="Red-flag penalty" value={w.red_flag_penalty} onChange={(v) => setW({ red_flag_penalty: v })} />
          <Num label="Sponsorship penalty" value={w.sponsorship_penalty} onChange={(v) => setW({ sponsorship_penalty: v })} />
          <Num label="Title-weight multiplier" value={w.title_weight_multiplier} onChange={(v) => setW({ title_weight_multiplier: v })} />
        </div>
      </Group>

      <Group title="Fit tiers (score thresholds)">
        <p className="mb-3 text-sm text-slate-500">Minimum score for each fit label shown in results.</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <Num label="Strong ≥" value={t.strong} onChange={(v) => setT({ strong: v })} />
          <Num label="Good ≥" value={t.good} onChange={(v) => setT({ good: v })} />
          <Num label="Moderate ≥" value={t.moderate} onChange={(v) => setT({ moderate: v })} />
        </div>
      </Group>

      <div className="flex items-center justify-between">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess} onSave={() => save.mutate(d)} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
