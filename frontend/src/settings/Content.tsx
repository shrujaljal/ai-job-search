import { useEffect, useState, type ReactNode } from 'react'
import { inputCls, Field } from '../components/ui'
import { Section, SaveBar } from './parts'
import { Repeater, TagList, Sub } from './fields'
import { useConfig } from './useConfig'

interface SkillCat { name: string; items: string }
interface FamilyContent {
  name: string
  summary: string
  coursework: string
  skill_categories: SkillCat[]
  projects: string[]
}
// Raw shape on disk: families is an object keyed by family name; other keys
// (limits, bullet_library, …) are preserved untouched.
interface RawContent {
  default_family?: string
  families?: Record<string, Omit<FamilyContent, 'name'>>
  [k: string]: unknown
}
interface Draft {
  default_family: string
  families: FamilyContent[]
  rest: Record<string, unknown> // passthrough keys we don't edit here
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details open className="rounded-2xl border border-slate-200 dark:border-slate-800">
      <summary className="cursor-pointer select-none px-4 py-3 font-semibold">{title}</summary>
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">{children}</div>
    </details>
  )
}

function toDraft(raw: RawContent): Draft {
  const { default_family, families, ...rest } = raw
  const arr: FamilyContent[] = Object.entries(families ?? {}).map(([name, cfg]) => ({
    name,
    summary: cfg.summary ?? '',
    coursework: cfg.coursework ?? '',
    skill_categories: (cfg.skill_categories ?? []).map((c: any) => ({
      name: c.name ?? c.category ?? c.label ?? '',
      items: Array.isArray(c.items) ? c.items.join(', ') : c.items ?? '',
    })),
    projects: cfg.projects ?? [],
  }))
  return { default_family: default_family ?? '', families: arr, rest }
}

function fromDraft(d: Draft): RawContent {
  const families: Record<string, Omit<FamilyContent, 'name'>> = {}
  for (const f of d.families) {
    if (!f.name.trim()) continue
    families[f.name.trim()] = {
      summary: f.summary,
      coursework: f.coursework,
      skill_categories: f.skill_categories,
      projects: f.projects,
    }
  }
  return { ...d.rest, default_family: d.default_family, families }
}

export function ContentEditor() {
  const { data, save, reset } = useConfig<RawContent>('resume_content')
  const [d, setD] = useState<Draft | null>(null)
  // Initialize the draft once; background refetches won't clobber in-progress edits.
  useEffect(() => { if (data && !d) setD(toDraft(data)) }, [data, d])
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>

  const doReset = async () => {
    if (!confirm('Reset résumé content to the shipped default? Your edits will be lost.')) return
    const fresh = await reset.mutateAsync()
    setD(toDraft(fresh))
  }

  // Compare in the on-disk shape so key reordering doesn't read as a change.
  const dirty = data ? JSON.stringify(fromDraft(d)) !== JSON.stringify(fromDraft(toDraft(data))) : false
  const names = d.families.map((f) => f.name).filter(Boolean)

  return (
    <Section title="Résumé Content"
      desc="Per-role-family tailoring: which summary, coursework, skills, and projects the generator uses. It only selects and rephrases from your Profile — it never invents facts.">
      <Group title="Default family">
        <p className="mb-3 text-sm text-slate-500">Used when a job doesn't clearly match any family below.</p>
        <div className="max-w-md">
          <Field label="Default family">
            <select className={inputCls} value={d.default_family} onChange={(e) => setD({ ...d, default_family: e.target.value })}>
              <option value="">— none —</option>
              {names.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </Field>
        </div>
      </Group>

      <Group title="Families">
        <p className="mb-3 text-sm text-slate-500">
          One entry per role family. The name must match a family in <b>Scoring Rules</b> for auto-detection to pick it.
        </p>
        <Repeater<FamilyContent> items={d.families} onChange={(families) => setD({ ...d, families })}
          empty={() => ({ name: '', summary: '', coursework: '', skill_categories: [{ name: '', items: '' }], projects: [] })}
          addLabel="Add family"
          render={(f, up) => (
            <>
              <Field label="Family name">
                <input className={inputCls} placeholder="e.g. Strategy & Operations" value={f.name} onChange={(e) => up({ name: e.target.value })} />
              </Field>
              <div className="mt-3">
                <Sub label="Summary (tailored profile statement for this family)">
                  <textarea className={inputCls} rows={3} value={f.summary} onChange={(e) => up({ summary: e.target.value })}
                    placeholder="Leave blank to fall back to the Profile default summary." />
                </Sub>
              </div>
              <div className="mt-1">
                <Sub label="Relevant coursework (optional, shown under Education)">
                  <input className={inputCls} value={f.coursework} onChange={(e) => up({ coursework: e.target.value })}
                    placeholder="e.g. Business Analytics, Operations Management" />
                </Sub>
              </div>
              <div className="mt-1">
                <Sub label="Skill categories (override the Profile skills for this family)">
                  <Repeater<SkillCat> items={f.skill_categories} onChange={(skill_categories) => up({ skill_categories })}
                    empty={() => ({ name: '', items: '' })} addLabel="Add skill category"
                    render={(s, sup) => (
                      <div className="grid gap-2 md:grid-cols-[200px_1fr]">
                        <input className={inputCls} placeholder="Category" value={s.name} onChange={(e) => sup({ name: e.target.value })} />
                        <input className={inputCls} placeholder="Comma-separated skills" value={s.items} onChange={(e) => sup({ items: e.target.value })} />
                      </div>
                    )} />
                </Sub>
              </div>
              <div className="mt-1">
                <Sub label="Featured projects (by title — must match a Profile project)">
                  <TagList value={f.projects} onChange={(projects) => up({ projects })} placeholder="Add a project title, press Enter" />
                </Sub>
              </div>
            </>
          )} />
      </Group>

      <div className="flex items-center justify-between">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess} onSave={() => save.mutate(fromDraft(d))} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
