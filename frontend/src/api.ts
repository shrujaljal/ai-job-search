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
  active_template: string
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

export interface ResumeTemplate {
  id: string
  name: string
  builtin: boolean
  active: boolean
  valid: boolean
  recognized_tokens: string[]
  missing_tokens: string[]
  unknown_tokens: string[]
  size: number
}

export interface TemplatesResponse {
  active_template: string
  required_tokens: string[]
  known_tokens: string[]
  templates: ResumeTemplate[]
}

export const api = {
  health: () => req<Health>('/health'),
  getSettings: () => req<Settings>('/config/settings'),

  getConfig: <T = Record<string, unknown>>(name: string) => req<T>(`/config/${name}`),
  putConfig: (name: string, data: unknown) => req<{ saved: boolean }>(`/config/${name}`, 'PUT', data),
  resetConfig: <T = Record<string, unknown>>(name: string) => req<T>(`/config/${name}/reset`, 'POST'),
  testLlm: () => req<{ ok: boolean; provider: string; model: string }>('/llm/test', 'POST'),

  listTemplates: () => req<TemplatesResponse>('/templates'),
  uploadTemplate: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    const res = await fetch('/api/templates', { method: 'POST', body })
    if (!res.ok) {
      let detail = res.statusText
      try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
      throw new Error(detail)
    }
    return res.json() as Promise<ResumeTemplate>
  },
  setActiveTemplate: (id: string) =>
    req<{ active_template: string }>('/templates/active', 'PUT', { id }),
  deleteTemplate: (id: string) =>
    req<{ deleted: boolean }>(`/templates/${encodeURIComponent(id)}`, 'DELETE'),

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
