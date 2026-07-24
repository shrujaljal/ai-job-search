import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api'
import { Field, inputCls, Button } from '../components/ui'
import { Section, SaveBar, Toggle } from './parts'
import { useSettings } from './useSettings'
import type { Settings } from '../api'

const PROVIDERS = {
  openrouter: {
    label: 'OpenRouter Free',
    note: 'Automatically routes to an available free model. Free usage is rate limited.',
    modelKey: 'openrouter_model',
    modelPlaceholder: 'openrouter/free',
    keyName: 'openrouter',
    keyLabel: 'OpenRouter API key',
    setupUrl: 'https://openrouter.ai/settings/keys',
    setupLabel: 'Get an OpenRouter key',
  },
  groq: {
    label: 'Groq Free Tier',
    note: 'Fast hosted inference for open-weight models. Free usage is rate limited.',
    modelKey: 'groq_model',
    modelPlaceholder: 'openai/gpt-oss-20b',
    keyName: 'groq',
    keyLabel: 'Groq API key',
    setupUrl: 'https://console.groq.com/keys',
    setupLabel: 'Get a Groq key',
  },
  ollama: {
    label: 'Ollama Local',
    note: 'Runs on your computer. No paid API key or cloud account is required.',
    modelKey: 'ollama_model',
    modelPlaceholder: 'gpt-oss:20b',
    keyName: '',
    keyLabel: '',
    setupUrl: 'https://ollama.com/download',
    setupLabel: 'Install Ollama',
  },
  openai: {
    label: 'OpenAI',
    note: 'Paid OpenAI API account.',
    modelKey: 'openai_model',
    modelPlaceholder: 'gpt-4o',
    keyName: 'openai',
    keyLabel: 'OpenAI API key',
    setupUrl: 'https://platform.openai.com/api-keys',
    setupLabel: 'OpenAI API keys',
  },
  claude: {
    label: 'Anthropic Claude',
    note: 'Paid Anthropic API account.',
    modelKey: 'model',
    modelPlaceholder: 'claude-sonnet-5',
    keyName: 'claude',
    keyLabel: 'Anthropic API key',
    setupUrl: 'https://console.anthropic.com/settings/keys',
    setupLabel: 'Anthropic API keys',
  },
} as const

type ProviderName = keyof typeof PROVIDERS
type ModelKey = typeof PROVIDERS[ProviderName]['modelKey']

function normalizeSettings(settings: Settings): Settings {
  return {
    ...settings,
    llm: {
      ...settings.llm,
      provider: settings.llm.provider || 'openrouter',
      openrouter_model: settings.llm.openrouter_model || 'openrouter/free',
      groq_model: settings.llm.groq_model || 'openai/gpt-oss-20b',
      ollama_model: settings.llm.ollama_model || 'gpt-oss:20b',
      ollama_base_url: settings.llm.ollama_base_url || 'http://localhost:11434/v1',
      grounding_strictness: settings.llm.grounding_strictness ?? 85,
      api_keys: {
        claude: '',
        openai: '',
        openrouter: '',
        groq: '',
        ...settings.llm.api_keys,
      },
    },
  }
}

function strictnessLabel(value: number) {
  if (value >= 80) return 'Exact evidence'
  if (value >= 50) return 'Balanced'
  return 'Flexible wording'
}

export function AI() {
  const { settings, save } = useSettings()
  const [draft, setDraft] = useState<Settings | null>(null)
  const test = useMutation({ mutationFn: api.testLlm })
  useEffect(() => {
    if (settings && !draft) setDraft(normalizeSettings(structuredClone(settings)))
  }, [settings, draft])
  if (!draft) return <p className="text-sm text-slate-500">Loading...</p>

  const effectiveDraft = normalizeSettings(draft)
  const normalized = effectiveDraft.llm
  const dirty = JSON.stringify(effectiveDraft) !==
    JSON.stringify(settings ? normalizeSettings(settings) : settings)
  const providerName = (normalized.provider in PROVIDERS ? normalized.provider : 'openrouter') as ProviderName
  const provider = PROVIDERS[providerName]
  const setLlm = (patch: Partial<Settings['llm']>) =>
    setDraft({ ...effectiveDraft, llm: { ...normalized, ...patch } })
  const setKey = (name: string, value: string) =>
    setLlm({ api_keys: { ...normalized.api_keys, [name]: value } })
  const setModel = (key: ModelKey, value: string) => setLlm({ [key]: value } as Partial<Settings['llm']>)

  return (
    <Section title="AI Tailoring"
      desc="Choose a hosted free tier, a local model, or a paid provider. Tailoring sends only Profile evidence and the job description to the selected provider.">
      <div className="space-y-5 rounded-lg border border-slate-200 p-5 dark:border-slate-800">
        <Toggle checked={normalized.enabled} onChange={(enabled) => setLlm({ enabled })}
          label={normalized.enabled ? 'AI tailoring is on' : 'AI tailoring is off'} />

        {normalized.enabled && (
          <>
            <div>
              <Field label="Provider">
                <select className={inputCls} value={providerName}
                  onChange={(event) => setLlm({ provider: event.target.value })}>
                  <optgroup label="Free options">
                    <option value="openrouter">OpenRouter Free</option>
                    <option value="groq">Groq Free Tier</option>
                    <option value="ollama">Ollama Local</option>
                  </optgroup>
                  <optgroup label="Paid options">
                    <option value="openai">OpenAI</option>
                    <option value="claude">Anthropic Claude</option>
                  </optgroup>
                </select>
              </Field>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                <span>{provider.note}</span>
                <a className="font-medium text-[var(--accent)] hover:underline" href={provider.setupUrl}
                  target="_blank" rel="noreferrer">{provider.setupLabel}</a>
              </div>
            </div>

            <Field label={`${provider.label} model`}>
              <input className={inputCls}
                value={String(normalized[provider.modelKey] ?? '')}
                onChange={(event) => setModel(provider.modelKey, event.target.value)}
                placeholder={provider.modelPlaceholder} />
            </Field>

            {providerName === 'ollama' ? (
              <Field label="Ollama server">
                <input className={inputCls} value={normalized.ollama_base_url}
                  onChange={(event) => setLlm({ ollama_base_url: event.target.value })}
                  placeholder="http://localhost:11434/v1" />
              </Field>
            ) : (
              <Field label={provider.keyLabel}>
                <input className={inputCls} type="password"
                  value={provider.keyName ? normalized.api_keys[provider.keyName] ?? '' : ''}
                  onChange={(event) => {
                    if (provider.keyName) setKey(provider.keyName, event.target.value)
                  }}
                  autoComplete="off" placeholder="Paste API key" />
              </Field>
            )}

            <div className="border-t border-slate-200 pt-5 dark:border-slate-800">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-sm font-semibold">Profile grounding</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Controls rewriting freedom. Facts, numbers, employers, dates, and skills must always come from Profile.
                  </p>
                </div>
                <span className="shrink-0 text-sm font-semibold">{strictnessLabel(normalized.grounding_strictness)}</span>
              </div>
              <input className="mt-4 w-full accent-[var(--accent)]" type="range" min="0" max="100" step="5"
                aria-label="Profile grounding strictness" value={normalized.grounding_strictness}
                onChange={(event) => setLlm({ grounding_strictness: Number(event.target.value) })} />
              <div className="mt-1 flex justify-between text-xs text-slate-400">
                <span>Flexible</span><span>{normalized.grounding_strictness}% strict</span><span>Exact</span>
              </div>
            </div>

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
      </div>
      <SaveBar dirty={dirty} saving={save.isPending} saved={save.isSuccess}
        onSave={() => save.mutate(effectiveDraft)} />
    </Section>
  )
}
