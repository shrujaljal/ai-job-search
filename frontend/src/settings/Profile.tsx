import { useEffect, useState } from 'react'
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
interface Profile {
  identity: Identity; summary: string
  experience: Exp[]; education: Edu[]; projects: Proj[]; leadership: Lead[]; skills: Skill[]
}

function asText(v: unknown) {
  return Array.isArray(v) ? v.join(', ') : String(v ?? '')
}

function normalizeProfile(raw: any): Profile {
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
    experience: (raw?.experience ?? []).map((e: any) => ({
      company: e.company ?? '',
      role: e.role ?? '',
      date: e.date ?? [e.start, e.end].filter(Boolean).join(' - '),
      bullets: e.bullets ?? [],
    })),
    education: (raw?.education ?? []).map((e: any) => ({
      degree: e.degree ?? '',
      field: e.field ?? '',
      institution: e.institution ?? '',
      location: e.location ?? '',
      graduation: e.graduation ?? '',
      gpa: e.gpa ?? '',
      honors: e.honors ?? [],
    })),
    projects: (raw?.projects ?? []).map((p: any) => ({
      title: p.title ?? '',
      bullets: p.bullets ?? [],
      families: p.families ?? [],
    })),
    leadership: (raw?.leadership ?? []).map((l: any) => ({
      organization: l.organization ?? '',
      role: l.role ?? '',
      bullets: l.bullets ?? [],
    })),
    skills: (raw?.skills ?? []).map((s: any) => ({
      name: s.name ?? s.category ?? s.label ?? '',
      items: asText(s.items),
    })),
  }
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details open className="rounded-2xl border border-slate-200 dark:border-slate-800">
      <summary className="cursor-pointer select-none px-4 py-3 font-semibold">{title}</summary>
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">{children}</div>
    </details>
  )
}

export function ProfileEditor() {
  const { data, save, reset } = useConfig<Profile>('profile')
  const [d, setD] = useState<Profile | null>(null)
  const clean = data ? normalizeProfile(data) : null
  // Initialize the draft once; background refetches won't clobber in-progress edits.
  useEffect(() => { if (clean && !d) setD(structuredClone(clean)) }, [clean, d])
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>

  const doReset = async () => {
    if (!confirm('Reset the profile to the shipped default? Your edits will be lost.')) return
    const fresh = await reset.mutateAsync()
    setD(normalizeProfile(fresh))
  }

  const dirty = JSON.stringify(d) !== JSON.stringify(clean)
  const id = d.identity
  const setId = (patch: Partial<Identity>) => setD({ ...d, identity: { ...id, ...patch } })

  return (
    <Section title="Profile" desc="Your facts. Résumés are generated from this — nothing is invented.">
      <Group title="Identity">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Full name"><input className={inputCls} value={id.name} onChange={(e) => setId({ name: e.target.value })} /></Field>
          <Field label="Email"><input className={inputCls} value={id.email} onChange={(e) => setId({ email: e.target.value })} /></Field>
          <Field label="Phone"><input className={inputCls} value={id.phone} onChange={(e) => setId({ phone: e.target.value })} /></Field>
          <Field label="Location"><input className={inputCls} value={id.location} onChange={(e) => setId({ location: e.target.value })} /></Field>
          <Field label="Work authorization"><input className={inputCls} value={id.work_authorization} onChange={(e) => setId({ work_authorization: e.target.value })} /></Field>
        </div>
        <div className="mt-3"><Toggle checked={id.needs_sponsorship} onChange={(v) => setId({ needs_sponsorship: v })} label="Needs visa sponsorship" /></div>
        <div className="mt-4">
          <Sub label="Links (LinkedIn, portfolio…)">
            <Repeater<Link> items={id.links} onChange={(links) => setId({ links })} empty={() => ({ label: '', url: '' })} addLabel="Add link"
              render={(l, up) => (
                <div className="grid gap-2 md:grid-cols-2">
                  <input className={inputCls} placeholder="Label (e.g. LinkedIn)" value={l.label} onChange={(e) => up({ label: e.target.value })} />
                  <input className={inputCls} placeholder="https://…" value={l.url} onChange={(e) => up({ url: e.target.value })} />
                </div>
              )} />
          </Sub>
        </div>
      </Group>

      <Group title="Default summary">
        <textarea className={inputCls} rows={3} value={d.summary} onChange={(e) => setD({ ...d, summary: e.target.value })}
          placeholder="Fallback summary when a role family has none set." />
      </Group>

      <Group title="Experience">
        <Repeater<Exp> items={d.experience} onChange={(experience) => setD({ ...d, experience })}
          empty={() => ({ company: '', role: '', date: '', bullets: [''] })} addLabel="Add experience"
          render={(e, up) => (
            <>
              <div className="grid gap-2 md:grid-cols-3">
                <input className={inputCls} placeholder="Company" value={e.company} onChange={(ev) => up({ company: ev.target.value })} />
                <input className={inputCls} placeholder="Role" value={e.role} onChange={(ev) => up({ role: ev.target.value })} />
                <input className={inputCls} placeholder="Dates (e.g. Feb 2025 – Sep 2025)" value={e.date} onChange={(ev) => up({ date: ev.target.value })} />
              </div>
              <div className="mt-3"><Sub label="Bullets"><BulletList value={e.bullets} onChange={(bullets) => up({ bullets })} /></Sub></div>
            </>
          )} />
      </Group>

      <Group title="Education">
        <Repeater<Edu> items={d.education} onChange={(education) => setD({ ...d, education })}
          empty={() => ({ degree: '', field: '', institution: '', location: '', graduation: '', gpa: '', honors: [] })} addLabel="Add education"
          render={(e, up) => (
            <>
              <div className="grid gap-2 md:grid-cols-2">
                <input className={inputCls} placeholder="Degree" value={e.degree} onChange={(ev) => up({ degree: ev.target.value })} />
                <input className={inputCls} placeholder="Field" value={e.field} onChange={(ev) => up({ field: ev.target.value })} />
                <input className={inputCls} placeholder="Institution" value={e.institution} onChange={(ev) => up({ institution: ev.target.value })} />
                <input className={inputCls} placeholder="Location" value={e.location} onChange={(ev) => up({ location: ev.target.value })} />
                <input className={inputCls} placeholder="Graduation (e.g. June 2026)" value={e.graduation} onChange={(ev) => up({ graduation: ev.target.value })} />
                <input className={inputCls} placeholder="GPA" value={e.gpa} onChange={(ev) => up({ gpa: ev.target.value })} />
              </div>
              <div className="mt-3"><Sub label="Honors"><TagList value={e.honors} onChange={(honors) => up({ honors })} placeholder="Add an honor, press Enter" /></Sub></div>
            </>
          )} />
      </Group>

      <Group title="Skills">
        <Repeater<Skill> items={d.skills} onChange={(skills) => setD({ ...d, skills })}
          empty={() => ({ name: '', items: '' })} addLabel="Add skill category"
          render={(s, up) => (
            <div className="grid gap-2 md:grid-cols-[200px_1fr]">
              <input className={inputCls} placeholder="Category" value={s.name} onChange={(e) => up({ name: e.target.value })} />
              <input className={inputCls} placeholder="Comma-separated skills" value={s.items} onChange={(e) => up({ items: e.target.value })} />
            </div>
          )} />
      </Group>

      <Group title="Projects">
        <Repeater<Proj> items={d.projects} onChange={(projects) => setD({ ...d, projects })}
          empty={() => ({ title: '', bullets: [''], families: [] })} addLabel="Add project"
          render={(p, up) => (
            <>
              <input className={inputCls} placeholder="Project title" value={p.title} onChange={(e) => up({ title: e.target.value })} />
              <div className="mt-3"><Sub label="Bullets"><BulletList value={p.bullets} onChange={(bullets) => up({ bullets })} /></Sub></div>
              <div className="mt-3"><Sub label="Suits role families"><TagList value={p.families} onChange={(families) => up({ families })} placeholder="e.g. Strategy & Operations" /></Sub></div>
            </>
          )} />
      </Group>

      <Group title="Leadership">
        <Repeater<Lead> items={d.leadership} onChange={(leadership) => setD({ ...d, leadership })}
          empty={() => ({ organization: '', role: '', bullets: [''] })} addLabel="Add leadership"
          render={(l, up) => (
            <>
              <div className="grid gap-2 md:grid-cols-2">
                <input className={inputCls} placeholder="Organization" value={l.organization} onChange={(e) => up({ organization: e.target.value })} />
                <input className={inputCls} placeholder="Role" value={l.role} onChange={(e) => up({ role: e.target.value })} />
              </div>
              <div className="mt-3"><Sub label="Bullets"><BulletList value={l.bullets} onChange={(bullets) => up({ bullets })} /></Sub></div>
            </>
          )} />
      </Group>

      <div className="flex items-center justify-between">
        <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess} onSave={() => save.mutate(d)} />
        <button onClick={doReset} className="text-sm text-slate-400 hover:text-rose-500">Reset to default</button>
      </div>
    </Section>
  )
}
