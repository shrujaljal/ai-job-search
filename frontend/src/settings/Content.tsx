import { useEffect, useState } from 'react'
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
interface RawContent {
  default_family?: string
  families?: Record<string, Omit<FamilyContent, 'name'>>
  [k: string]: unknown
}
interface Draft {
  default_family: string
  families: FamilyContent[]
  rest: Record<string, unknown>
}

function toDraft(raw: RawContent): Draft {
  const { default_family, families, ...rest } = raw
  return {
    default_family: default_family ?? '',
    families: Object.entries(families ?? {}).map(([name, config]) => ({
      name,
      summary: config.summary ?? '',
      coursework: config.coursework ?? '',
      skill_categories: (config.skill_categories ?? []).map((category: any) => ({
        name: category.name ?? category.category ?? category.label ?? '',
        items: Array.isArray(category.items) ? category.items.join(', ') : category.items ?? '',
      })),
      projects: config.projects ?? [],
    })),
    rest,
  }
}

function fromDraft(draft: Draft): RawContent {
  const families: Record<string, Omit<FamilyContent, 'name'>> = {}
  for (const family of draft.families) {
    if (!family.name.trim()) continue
    families[family.name.trim()] = {
      summary: family.summary,
      coursework: family.coursework,
      skill_categories: family.skill_categories,
      projects: family.projects,
    }
  }
  return { ...draft.rest, default_family: draft.default_family, families }
}

const emptyFamily = (): FamilyContent => ({
  name: 'New role family',
  summary: '',
  coursework: '',
  skill_categories: [],
  projects: [],
})

export function ContentEditor() {
  const { data, save, reset } = useConfig<RawContent>('resume_content')
  const [draft, setDraft] = useState<Draft | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  useEffect(() => { if (data && !draft) setDraft(toDraft(data)) }, [data, draft])
  if (!draft) return <p className="text-sm text-slate-500">Loading...</p>

  const dirty = data
    ? JSON.stringify(fromDraft(draft)) !== JSON.stringify(fromDraft(toDraft(data)))
    : false
  const active = draft.families[activeIndex]
  const updateActive = (patch: Partial<FamilyContent>) => {
    const families = draft.families.map((family, index) =>
      index === activeIndex ? { ...family, ...patch } : family)
    setDraft({ ...draft, families })
  }
  const addFamily = () => {
    setDraft({ ...draft, families: [...draft.families, emptyFamily()] })
    setActiveIndex(draft.families.length)
  }
  const removeFamily = () => {
    if (!active || !confirm(`Remove "${active.name}" from tailoring preferences?`)) return
    const families = draft.families.filter((_, index) => index !== activeIndex)
    setDraft({
      ...draft,
      families,
      default_family: draft.default_family === active.name ? '' : draft.default_family,
    })
    setActiveIndex(Math.max(0, activeIndex - 1))
  }
  const doReset = async () => {
    if (!confirm('Reset tailoring preferences to the shipped default?')) return
    const fresh = await reset.mutateAsync()
    setDraft(toDraft(fresh))
    setActiveIndex(0)
  }

  return (
    <Section title="Tailoring Preferences"
      desc="Set the preferred summary for each role family. Everything else comes from Profile unless you add an optional override.">
      <div className="rounded-lg border border-slate-200 p-5 dark:border-slate-800">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Default role family">
            <select className={inputCls} value={draft.default_family}
              onChange={(event) => setDraft({ ...draft, default_family: event.target.value })}>
              <option value="">None</option>
              {draft.families.map((family) =>
                <option key={family.name} value={family.name}>{family.name}</option>)}
            </select>
          </Field>
          <Field label="Edit role family">
            <select className={inputCls} value={active ? activeIndex : ''}
              onChange={(event) => setActiveIndex(Number(event.target.value))}>
              {draft.families.map((family, index) =>
                <option key={`${family.name}-${index}`} value={index}>{family.name}</option>)}
            </select>
          </Field>
        </div>

        {active ? (
          <div className="mt-5 space-y-4 border-t border-slate-200 pt-5 dark:border-slate-800">
            <Field label="Role family name">
              <input className={inputCls} value={active.name}
                onChange={(event) => updateActive({ name: event.target.value })} />
            </Field>
            <Field label="Preferred summary">
              <textarea className={inputCls} rows={4} value={active.summary}
                onChange={(event) => updateActive({ summary: event.target.value })}
                placeholder="Leave blank to use the Profile summary." />
            </Field>

            <details className="border-t border-slate-200 pt-4 dark:border-slate-800">
              <summary className="cursor-pointer text-sm font-semibold">Optional overrides</summary>
              <div className="mt-4 space-y-4">
                <Field label="Relevant coursework">
                  <input className={inputCls} value={active.coursework}
                    onChange={(event) => updateActive({ coursework: event.target.value })} />
                </Field>
                <Sub label="Skill categories">
                  <Repeater<SkillCat> items={active.skill_categories}
                    onChange={(skill_categories) => updateActive({ skill_categories })}
                    empty={() => ({ name: '', items: '' })} addLabel="Add skill category"
                    render={(category, update) => (
                      <div className="grid gap-2 md:grid-cols-[180px_1fr]">
                        <input className={inputCls} placeholder="Category" value={category.name}
                          onChange={(event) => update({ name: event.target.value })} />
                        <input className={inputCls} placeholder="Comma-separated skills" value={category.items}
                          onChange={(event) => update({ items: event.target.value })} />
                      </div>
                    )} />
                </Sub>
                <Sub label="Featured Profile projects">
                  <TagList value={active.projects} onChange={(projects) => updateActive({ projects })}
                    placeholder="Add an exact Profile project title" />
                </Sub>
              </div>
            </details>
          </div>
        ) : (
          <p className="mt-5 text-sm text-slate-500">Add a role family to create tailoring preferences.</p>
        )}

        <div className="mt-5 flex gap-3">
          <button type="button" onClick={addFamily}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700">
            Add role family
          </button>
          {active && <button type="button" onClick={removeFamily}
            className="text-sm font-medium text-rose-600">Remove</button>}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess}
          onSave={() => save.mutate(fromDraft(draft))} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
