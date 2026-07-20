import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api'
import { Field, inputCls, Card, Button } from '../components/ui'
import { Section, SaveBar, Toggle } from './parts'
import { useSettings } from './useSettings'
import type { Settings } from '../api'

export function AI() {
  const { settings, save } = useSettings()
  const [draft, setDraft] = useState<Settings | null>(null)
  const test = useMutation({ mutationFn: api.testLlm })
  useEffect(() => { if (settings && !draft) setDraft(structuredClone(settings)) }, [settings, draft])
  if (!draft) return <p className="text-sm text-slate-500">Loading…</p>

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)
  const llm = draft.llm
  const setLlm = (patch: Partial<Settings['llm']>) => setDraft({ ...draft, llm: { ...llm, ...patch } })
  const setKey = (p: 'claude' | 'openai', v: string) =>
    setDraft({ ...draft, llm: { ...llm, api_keys: { ...llm.api_keys, [p]: v } } })

  return (
    <Section title="AI-assisted tailoring"
      desc="Optionally let an AI rewrite your summary and bullets to match each JD. When off, the fast rule-based engine is used. Your key is stored locally and only sent to your chosen provider.">
      <Card className="space-y-4">
        <Toggle checked={llm.enabled} onChange={(v) => setLlm({ enabled: v })}
          label={llm.enabled ? 'AI tailoring is ON' : 'AI tailoring is OFF (rule-based)'} />

        {llm.enabled && (
          <>
            <Field label="Provider">
              <select className={inputCls} value={llm.provider} onChange={(e) => setLlm({ provider: e.target.value })}>
                <option value="claude">Anthropic (Claude)</option>
                <option value="openai">OpenAI</option>
              </select>
            </Field>

            {llm.provider === 'claude' ? (
              <>
                <Field label="Claude model">
                  <input className={inputCls} value={llm.model} onChange={(e) => setLlm({ model: e.target.value })}
                    placeholder="claude-sonnet-5" />
                </Field>
                <Field label="Anthropic API key">
                  <input className={inputCls} type="password" value={llm.api_keys.claude}
                    onChange={(e) => setKey('claude', e.target.value)} placeholder="sk-ant-…" />
                </Field>
              </>
            ) : (
              <>
                <Field label="OpenAI model">
                  <input className={inputCls} value={llm.openai_model} onChange={(e) => setLlm({ openai_model: e.target.value })}
                    placeholder="gpt-4o" />
                </Field>
                <Field label="OpenAI API key">
                  <input className={inputCls} type="password" value={llm.api_keys.openai}
                    onChange={(e) => setKey('openai', e.target.value)} placeholder="sk-…" />
                </Field>
              </>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="ghost" disabled={dirty || test.isPending} onClick={() => test.mutate()}>
                {test.isPending ? 'Testing...' : 'Test connection'}
              </Button>
              {dirty && <span className="text-xs text-slate-500">Save changes before testing.</span>}
              {test.isSuccess && <span className="text-sm text-emerald-600">Connected to {test.data.model}</span>}
              {test.isError && <span className="text-sm text-rose-600">{test.error.message}</span>}
            </div>
          </>
        )}
      </Card>
      <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess} onSave={() => save.mutate(draft)} />
    </Section>
  )
}
