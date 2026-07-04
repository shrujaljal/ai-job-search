// Tiny fetch helper. In dev, Vite proxies /api to the FastAPI backend;
// in production the backend serves this app and /api on the same origin.

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export interface Health {
  status: string
  version: string
}

export interface Settings {
  candidate_name: string
  theme: string
  llm: { enabled: boolean; provider: string; model: string }
  [key: string]: unknown
}
