// Typed API client. In dev, Vite proxies /api to FastAPI; in prod the backend
// serves this app and /api on the same origin.

import type {
  SearchResponse, TailorResult, Application, Dashboard, Plan,
} from './types'

async function req<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export interface Health { status: string; version: string }
export interface Settings {
  candidate_name: string
  username: string
  output_dir: string
  theme: string
  accent: string
  llm: {
    enabled: boolean
    provider: string
    model: string
    openai_model: string
    api_keys: { claude: string; openai: string }
  }
  search: { boards: string[]; pages_per_board: number }
  [k: string]: unknown
}

export interface OnboardingStatus {
  complete: boolean
  legacy_inferred: boolean
  role_families: { name: string; tier: number }[]
  defaults: OnboardingPayload
}

export interface OnboardingPayload {
  full_name: string
  display_name: string
  location: string
  work_authorization: string
  needs_sponsorship: boolean
  target_roles: string[]
  preferred_locations: string[]
  max_years_experience: number
  output_dir: string
  ai_enabled: boolean
  ai_provider: 'claude' | 'openai'
  ai_model: string
  ai_api_key: string
}

export interface ProfileImportResult {
  profile: Record<string, unknown>
  stats: {
    files: number
    items_added: number
    duplicates_removed: number
    sections_added: number
  }
  sources: string[]
}

export const api = {
  health: () => req<Health>('/health'),
  getSettings: () => req<Settings>('/config/settings'),
  getOnboarding: () => req<OnboardingStatus>('/onboarding'),
  completeOnboarding: (payload: OnboardingPayload) =>
    req<{ complete: boolean }>('/onboarding', 'POST', payload),
  resetOnboarding: () => req<{ complete: boolean }>('/onboarding/reset', 'POST'),

  getConfig: <T = Record<string, unknown>>(name: string) => req<T>(`/config/${name}`),
  putConfig: (name: string, data: unknown) => req<{ saved: boolean }>(`/config/${name}`, 'PUT', data),
  resetConfig: <T = Record<string, unknown>>(name: string) => req<T>(`/config/${name}/reset`, 'POST'),
  testLlm: () => req<{ ok: boolean; provider: string; model: string }>('/llm/test', 'POST'),

  importProfile: async (files: File[]) => {
    const body = new FormData()
    files.forEach((file) => body.append('files', file))
    const res = await fetch('/api/profile/import', { method: 'POST', body })
    if (!res.ok) {
      let detail = res.statusText
      try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
      throw new Error(detail)
    }
    return res.json() as Promise<ProfileImportResult>
  },
  profileEnrichmentPromptUrl: '/api/profile/enrichment-prompt',

  search: (payload: {
    roles: string[]; location: string; date_posted: string
    job_type: string; pages: number
  }) => req<SearchResponse>('/search', 'POST', payload),

  tailor: (payload: {
    company: string; role: string; jd_text?: string; job_id?: string
    location?: string; enforce_sponsorship?: boolean; use_llm?: boolean
  }) => req<TailorResult>('/tailor', 'POST', payload),

  listApplications: () => req<Application[]>('/applications'),
  addApplication: (a: Partial<Application>) => req<Application>('/applications', 'POST', a),
  patchApplication: (id: number, fields: Partial<Application>) =>
    req<{ updated: boolean }>(`/applications/${id}`, 'PATCH', fields),
  deleteApplication: (id: number) =>
    req<{ deleted: boolean }>(`/applications/${id}`, 'DELETE'),

  getPlan: () => req<Plan>('/plan'),
  putPlan: (p: Plan) => req<{ saved: boolean }>('/plan', 'PUT', p),

  getDashboard: () => req<Dashboard>('/dashboard'),

  downloadUrl: (path: string) => `/api/download?path=${encodeURIComponent(path)}`,
}
