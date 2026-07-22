import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { inputCls, Field } from '../components/ui'
import { Section, SaveBar, Toggle } from './parts'
import { Repeater, BulletList, TagList, Sub } from './fields'
import { useConfig } from './useConfig'

interface Link { label: string; url: string }
interface Identity {
  name: string; email: string; phone: string; location: string
  links: Link[]; work_authorization: string; needs_sponsorship: boolean
}
interface Exp { company: string; role: string; date: string; bullets: string[] }
interface Edu { degree: string; field: string; institution: string; location: string; graduation: string; gpa: string; honors: string[] }
interface Proj { title: string; bullets: string[]; families: string[] }
interface Lead { organization: string; role: string; bullets: string[] }
interface Skill { name: string; items: string }
interface CustomSection { id: string; title: string; lines: string[] }
interface ResumeBlueprint {
  source_files: string[]
  section_order: string[]
  section_headings: Record<string, string>
}
interface Profile {
  identity: Identity
  summary: string
  experience: Exp[]
  education: Edu[]
  projects: Proj[]
  leadership: Lead[]
  honors: string[]
  skills: Skill[]
  custom_sections: CustomSection[]
  resume_blueprint: ResumeBlueprint
}

const DEFAULT_ORDER = ['summary', 'experience', 'education', 'projects_leadership', 'skills']
const DEFAULT_HEADINGS: Record<string, string> = {
  summary: 'Professional Summary',
  experience: 'Experience',
  education: 'Education',
  projects: 'Projects',
  leadership: 'Leadership',
  projects_leadership: 'Projects & Leadership',
  skills: 'Skills',
  honors: 'Honors & Awards',
}
const SECTION_OPTIONS = ['summary', 'experience', 'education', 'projects', 'leadership', 'projects_leadership', 'honors', 'skills']

function asText(value: unknown) {
  return Array.isArray(value) ? value.join(', ') : String(value ?? '')
}

function normalizeProfile(raw: any): Profile {
  const customSections: CustomSection[] = (raw?.custom_sections ?? []).map((section: any, index: number) => ({
    id: section.id ?? `section-${index + 1}`,
    title: section.title ?? 'Additional Information',
    lines: section.lines ?? [],
  }))
  const suppliedOrder = raw?.resume_blueprint?.section_order
  const sectionOrder: string[] = Array.from(new Set(
    Array.isArray(suppliedOrder) && suppliedOrder.length ? suppliedOrder : DEFAULT_ORDER,
  ))
  customSections.forEach((section) => {
    const key = `custom:${section.id}`
    if (!sectionOrder.includes(key)) sectionOrder.push(key)
  })

  return {
    identity: {
      name: raw?.identity?.name ?? '',
      email: raw?.identity?.email ?? '',
      phone: raw?.identity?.phone ?? '',
      location: raw?.identity?.location ?? '',
      links: raw?.identity?.links ?? [],
      work_authorization: raw?.identity?.work_authorization ?? '',
      needs_sponsorship: Boolean(raw?.identity?.needs_sponsorship),
    },
    summary: raw?.summary ?? '',
    experience: (raw?.experience ?? []).map((experience: any) => ({
      company: experience.company ?? '',
      role: experience.role ?? '',
      date: experience.date ?? [experience.start, experience.end].filter(Boolean).join(' - '),
      bullets: experience.bullets ?? [],
    })),
    education: (raw?.education ?? []).map((education: any) => ({
      degree: education.degree ?? '',
      field: education.field ?? '',
      institution: education.institution ?? '',
      location: education.location ?? '',
      graduation: education.graduation ?? '',
      gpa: education.gpa ?? '',
      honors: education.honors ?? [],
    })),
    projects: (raw?.projects ?? []).map((project: any) => ({
      title: project.title ?? '',
      bullets: project.bullets ?? [],
      families: project.families ?? [],
    })),
    leadership: (raw?.leadership ?? []).map((leadership: any) => ({
      organization: leadership.organization ?? '',
      role: leadership.role ?? '',
      bullets: leadership.bullets ?? [],
    })),
    honors: raw?.honors ?? [],
    skills: (raw?.skills ?? []).map((skill: any) => ({
      name: skill.name ?? skill.category ?? skill.label ?? '',
      items: asText(skill.items),
    })),
    custom_sections: customSections,
    resume_blueprint: {
      source_files: raw?.resume_blueprint?.source_files ?? [],
      section_order: sectionOrder,
      section_headings: {
        ...DEFAULT_HEADINGS,
        ...(raw?.resume_blueprint?.section_headings ?? {}),
        ...Object.fromEntries(customSections.map((section) => [
          `custom:${section.id}`,
          raw?.resume_blueprint?.section_headings?.[`custom:${section.id}`] ?? section.title,
        ])),
      },
    },
  }
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details open className="rounded-lg border border-slate-200 dark:border-slate-800">
      <summary className="cursor-pointer select-none px-4 py-3 font-semibold">{title}</summary>
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">{children}</div>
    </details>
  )
}

export function ProfileEditor() {
  const { data, save, reset } = useConfig<Profile>('profile')
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState<Profile | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [importMessage, setImportMessage] = useState('')
  const clean = data ? normalizeProfile(data) : null

  useEffect(() => {
    if (clean && !draft) setDraft(structuredClone(clean))
  }, [clean, draft])

  const importFiles = useMutation({
    mutationFn: api.importProfile,
    onSuccess: (result) => {
      const next = normalizeProfile(result.profile)
      setDraft(next)
      queryClient.setQueryData(['config', 'profile'], result.profile)
      setSelectedFiles([])
      if (fileInput.current) fileInput.current.value = ''
      const duplicateText = result.stats.duplicates_removed
        ? `; ${result.stats.duplicates_removed} duplicates removed`
        : ''
      setImportMessage(
        `${result.stats.files} file(s) imported; ${result.stats.items_added} unique items added${duplicateText}.`,
      )
    },
  })

  if (!draft) return <p className="text-sm text-slate-500">Loading...</p>

  const dirty = JSON.stringify(draft) !== JSON.stringify(clean)
  const identity = draft.identity
  const setIdentity = (patch: Partial<Identity>) => {
    setDraft({ ...draft, identity: { ...identity, ...patch } })
  }
  const setBlueprint = (patch: Partial<ResumeBlueprint>) => {
    setDraft({ ...draft, resume_blueprint: { ...draft.resume_blueprint, ...patch } })
  }
  const headingFor = (key: string) => draft.resume_blueprint.section_headings[key] ?? DEFAULT_HEADINGS[key] ?? 'Additional Information'
  const setHeading = (key: string, value: string) => {
    setBlueprint({
      section_headings: { ...draft.resume_blueprint.section_headings, [key]: value },
    })
  }
  const moveSection = (index: number, delta: number) => {
    const nextIndex = index + delta
    if (nextIndex < 0 || nextIndex >= draft.resume_blueprint.section_order.length) return
    const next = [...draft.resume_blueprint.section_order]
    ;[next[index], next[nextIndex]] = [next[nextIndex], next[index]]
    setBlueprint({ section_order: next })
  }
  const availableSections = SECTION_OPTIONS.filter((key) => {
    if (draft.resume_blueprint.section_order.includes(key)) return false
    if (draft.resume_blueprint.section_order.includes('projects_leadership') && ['projects', 'leadership'].includes(key)) return false
    if (draft.resume_blueprint.section_order.some((item) => ['projects', 'leadership'].includes(item)) && key === 'projects_leadership') return false
    return true
  })

  const doReset = async () => {
    if (!confirm('Reset the profile to the shipped default? Your edits will be lost.')) return
    const fresh = await reset.mutateAsync()
    setDraft(normalizeProfile(fresh))
    setImportMessage('')
  }

  const doSave = async () => {
    await save.mutateAsync(draft)
    const saved = await api.getConfig<Profile>('profile')
    queryClient.setQueryData(['config', 'profile'], saved)
    setDraft(normalizeProfile(saved))
  }

  const renderExperience = () => (
    <Repeater<Exp> items={draft.experience} onChange={(experience) => setDraft({ ...draft, experience })}
      empty={() => ({ company: '', role: '', date: '', bullets: [''] })} addLabel="Add experience"
      render={(experience, update) => (
        <>
          <div className="grid gap-2 md:grid-cols-3">
            <input className={inputCls} placeholder="Company" value={experience.company} onChange={(event) => update({ company: event.target.value })} />
            <input className={inputCls} placeholder="Role" value={experience.role} onChange={(event) => update({ role: event.target.value })} />
            <input className={inputCls} placeholder="Dates" value={experience.date} onChange={(event) => update({ date: event.target.value })} />
          </div>
          <div className="mt-3"><Sub label="Bullet library"><BulletList value={experience.bullets} onChange={(bullets) => update({ bullets })} /></Sub></div>
        </>
      )} />
  )

  const renderEducation = () => (
    <Repeater<Edu> items={draft.education} onChange={(education) => setDraft({ ...draft, education })}
      empty={() => ({ degree: '', field: '', institution: '', location: '', graduation: '', gpa: '', honors: [] })} addLabel="Add education"
      render={(education, update) => (
        <>
          <div className="grid gap-2 md:grid-cols-2">
            <input className={inputCls} placeholder="Degree" value={education.degree} onChange={(event) => update({ degree: event.target.value })} />
            <input className={inputCls} placeholder="Field" value={education.field} onChange={(event) => update({ field: event.target.value })} />
            <input className={inputCls} placeholder="Institution" value={education.institution} onChange={(event) => update({ institution: event.target.value })} />
            <input className={inputCls} placeholder="Location" value={education.location} onChange={(event) => update({ location: event.target.value })} />
            <input className={inputCls} placeholder="Graduation" value={education.graduation} onChange={(event) => update({ graduation: event.target.value })} />
            <input className={inputCls} placeholder="GPA" value={education.gpa} onChange={(event) => update({ gpa: event.target.value })} />
          </div>
          <div className="mt-3"><Sub label="Honors"><TagList value={education.honors} onChange={(honors) => update({ honors })} placeholder="Add an honor, press Enter" /></Sub></div>
        </>
      )} />
  )

  const renderProjects = () => (
    <Repeater<Proj> items={draft.projects} onChange={(projects) => setDraft({ ...draft, projects })}
      empty={() => ({ title: '', bullets: [''], families: [] })} addLabel="Add project"
      render={(project, update) => (
        <>
          <input className={inputCls} placeholder="Project title" value={project.title} onChange={(event) => update({ title: event.target.value })} />
          <div className="mt-3"><Sub label="Bullet library"><BulletList value={project.bullets} onChange={(bullets) => update({ bullets })} /></Sub></div>
          <div className="mt-3"><Sub label="Role families"><TagList value={project.families} onChange={(families) => update({ families })} placeholder="Add a role family" /></Sub></div>
        </>
      )} />
  )

  const renderLeadership = () => (
    <Repeater<Lead> items={draft.leadership} onChange={(leadership) => setDraft({ ...draft, leadership })}
      empty={() => ({ organization: '', role: '', bullets: [''] })} addLabel="Add leadership"
      render={(leadership, update) => (
        <>
          <div className="grid gap-2 md:grid-cols-2">
            <input className={inputCls} placeholder="Organization" value={leadership.organization} onChange={(event) => update({ organization: event.target.value })} />
            <input className={inputCls} placeholder="Role" value={leadership.role} onChange={(event) => update({ role: event.target.value })} />
          </div>
          <div className="mt-3"><Sub label="Bullet library"><BulletList value={leadership.bullets} onChange={(bullets) => update({ bullets })} /></Sub></div>
        </>
      )} />
  )

  const renderSectionEditor = (key: string) => {
    if (key === 'summary') {
      return <textarea className={inputCls} rows={4} value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} />
    }
    if (key === 'experience') return renderExperience()
    if (key === 'education') return renderEducation()
    if (key === 'projects') return renderProjects()
    if (key === 'leadership') return renderLeadership()
    if (key === 'projects_leadership') {
      return <div className="space-y-5"><Sub label="Projects">{renderProjects()}</Sub><Sub label="Leadership">{renderLeadership()}</Sub></div>
    }
    if (key === 'skills') {
      return <Repeater<Skill> items={draft.skills} onChange={(skills) => setDraft({ ...draft, skills })}
        empty={() => ({ name: '', items: '' })} addLabel="Add skill category"
        render={(skill, update) => (
          <div className="grid gap-2 md:grid-cols-[200px_1fr]">
            <input className={inputCls} placeholder="Category" value={skill.name} onChange={(event) => update({ name: event.target.value })} />
            <input className={inputCls} placeholder="Comma-separated skills" value={skill.items} onChange={(event) => update({ items: event.target.value })} />
          </div>
        )} />
    }
    if (key === 'honors') {
      return <TagList value={draft.honors} onChange={(honors) => setDraft({ ...draft, honors })} placeholder="Add an honor, press Enter" />
    }
    if (key.startsWith('custom:')) {
      const customId = key.split(':', 2)[1]
      const index = draft.custom_sections.findIndex((section) => section.id === customId)
      if (index < 0) return null
      const section = draft.custom_sections[index]
      return <BulletList value={section.lines} onChange={(lines) => {
        const customSections = draft.custom_sections.map((item, itemIndex) => itemIndex === index ? { ...item, lines } : item)
        setDraft({ ...draft, custom_sections: customSections })
      }} />
    }
    return null
  }

  return (
    <Section title="Profile" desc="Resume facts, source files, section order, and reusable bullet libraries.">
      <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold">Resume sources</h2>
            <p className="mt-1 text-sm text-slate-500">DOCX, PDF, Markdown; up to 10 files per import.</p>
          </div>
          <a href={api.profileEnrichmentPromptUrl}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
            Download AI prompts
          </a>
        </div>
        <input ref={fileInput} type="file" multiple accept=".docx,.pdf,.md,.markdown" className="hidden"
          onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []).slice(0, 10))} />
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => fileInput.current?.click()}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
            Choose files
          </button>
          <button type="button" disabled={!selectedFiles.length || dirty || importFiles.isPending}
            onClick={() => importFiles.mutate(selectedFiles)}
            className="rounded-lg px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: 'var(--accent)' }}>
            {importFiles.isPending ? 'Importing...' : `Import${selectedFiles.length ? ` ${selectedFiles.length}` : ''}`}
          </button>
          {selectedFiles.length > 0 && <span className="text-sm text-slate-500">{selectedFiles.map((file) => file.name).join(', ')}</span>}
        </div>
        {dirty && selectedFiles.length > 0 && <p className="mt-2 text-sm text-amber-600">Save or reset current edits before importing.</p>}
        {importFiles.error && <p className="mt-2 text-sm text-rose-600">{importFiles.error.message}</p>}
        {importMessage && <p className="mt-2 text-sm text-emerald-600">{importMessage}</p>}
        {draft.resume_blueprint.source_files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {draft.resume_blueprint.source_files.map((source) => (
              <span key={source} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">{source}</span>
            ))}
          </div>
        )}
      </div>

      <Group title="Identity">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Full name"><input className={inputCls} value={identity.name} onChange={(event) => setIdentity({ name: event.target.value })} /></Field>
          <Field label="Email"><input className={inputCls} value={identity.email} onChange={(event) => setIdentity({ email: event.target.value })} /></Field>
          <Field label="Phone"><input className={inputCls} value={identity.phone} onChange={(event) => setIdentity({ phone: event.target.value })} /></Field>
          <Field label="Location"><input className={inputCls} value={identity.location} onChange={(event) => setIdentity({ location: event.target.value })} /></Field>
          <Field label="Work authorization"><input className={inputCls} value={identity.work_authorization} onChange={(event) => setIdentity({ work_authorization: event.target.value })} /></Field>
        </div>
        <div className="mt-3"><Toggle checked={identity.needs_sponsorship} onChange={(value) => setIdentity({ needs_sponsorship: value })} label="Needs visa sponsorship" /></div>
        <div className="mt-4">
          <Sub label="Links">
            <Repeater<Link> items={identity.links} onChange={(links) => setIdentity({ links })} empty={() => ({ label: '', url: '' })} addLabel="Add link"
              render={(link, update) => (
                <div className="grid gap-2 md:grid-cols-2">
                  <input className={inputCls} placeholder="Label" value={link.label} onChange={(event) => update({ label: event.target.value })} />
                  <input className={inputCls} placeholder="https://" value={link.url} onChange={(event) => update({ url: event.target.value })} />
                </div>
              )} />
          </Sub>
        </div>
      </Group>

      <Group title="Resume structure">
        <div className="space-y-2">
          {draft.resume_blueprint.section_order.map((key, index) => (
            <div key={key} className="grid grid-cols-[auto_1fr] items-center gap-2 sm:grid-cols-[auto_auto_1fr]">
              <div className="flex">
                <button type="button" title="Move section up" aria-label={`Move ${headingFor(key)} up`}
                  disabled={index === 0} onClick={() => moveSection(index, -1)}
                  className="h-9 w-9 rounded-l-md border border-slate-300 text-slate-500 disabled:opacity-30 dark:border-slate-700">↑</button>
                <button type="button" title="Move section down" aria-label={`Move ${headingFor(key)} down`}
                  disabled={index === draft.resume_blueprint.section_order.length - 1} onClick={() => moveSection(index, 1)}
                  className="h-9 w-9 rounded-r-md border border-l-0 border-slate-300 text-slate-500 disabled:opacity-30 dark:border-slate-700">↓</button>
              </div>
              <span className="w-8 text-right text-xs text-slate-400">{index + 1}</span>
              <input className={`${inputCls} col-span-2 sm:col-span-1`} aria-label={`Heading for ${key}`} value={headingFor(key)} onChange={(event) => setHeading(key, event.target.value)} />
            </div>
          ))}
          {availableSections.length > 0 && (
            <select className={inputCls} value="" aria-label="Add resume section"
              onChange={(event) => {
                if (event.target.value) {
                  setBlueprint({ section_order: [...draft.resume_blueprint.section_order, event.target.value] })
                }
              }}>
              <option value="">Add section...</option>
              {availableSections.map((key) => <option key={key} value={key}>{headingFor(key)}</option>)}
            </select>
          )}
        </div>
      </Group>

      {draft.resume_blueprint.section_order.map((key) => (
        <Group key={key} title={headingFor(key)}>{renderSectionEditor(key)}</Group>
      ))}

      <div className="flex items-center justify-between gap-4">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess} onSave={() => void doSave()} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
