export interface Job {
  id?: string
  title: string
  company: string
  location?: string
  url?: string
  date?: string
  query?: string
  score: number
  tier: string
  family: string
  reason: string
  blocked: boolean
  scored_on_jd: boolean
  jd_text?: string
}

export interface SearchResponse {
  jobs: Job[]
  board_status: Record<string, string>
  counts: { total: number; scored_on_jd: number; blocked: number }
}

export interface TailorResult {
  ok: boolean
  blocked: boolean
  company: string
  role: string
  family?: string
  out_dir?: string
  docx_path?: string
  pdf_path?: string
  warnings?: string[]
  sponsorship_warning?: string
  exp_warning?: string
  pdf_error?: string
  block_reason?: string
}

export interface Application {
  id: number
  company: string
  role: string
  location: string
  url: string
  date_added: string
  status: string
  notes: string
}

export interface Streak {
  current: number
  longest: number
  last_date: string
}

export interface Dashboard {
  total: number
  applied: number
  interviewing: number
  offers: number
  by_status: Record<string, number>
  applications: Application[]
  statuses: string[]
  streak?: Streak
}

export interface Plan {
  date?: string
  plan?: string
  done?: boolean
}

export const STATUSES = [
  'To Apply', 'Applied', 'Phone Screen', 'Interview',
  'Final Round', 'Offer', 'Rejected',
] as const
