import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type Mode = 'light' | 'dark'
export type Accent = 'violet' | 'emerald' | 'sky' | 'rose' | 'amber'
export const ACCENTS: Accent[] = ['violet', 'emerald', 'sky', 'rose', 'amber']

interface ThemeCtx {
  mode: Mode
  accent: Accent
  toggleMode: () => void
  setAccent: (a: Accent) => void
}
const Ctx = createContext<ThemeCtx | null>(null)

function initialMode(): Mode {
  const saved = localStorage.getItem('theme-mode') as Mode | null
  if (saved) return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(initialMode)
  const [accent, setAccentState] = useState<Accent>(
    (localStorage.getItem('theme-accent') as Accent) || 'violet')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark')
    localStorage.setItem('theme-mode', mode)
  }, [mode])

  useEffect(() => {
    document.documentElement.setAttribute('data-accent', accent)
    localStorage.setItem('theme-accent', accent)
  }, [accent])

  return (
    <Ctx.Provider value={{
      mode, accent,
      toggleMode: () => setMode((m) => (m === 'dark' ? 'light' : 'dark')),
      setAccent: setAccentState,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export function useTheme() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useTheme outside ThemeProvider')
  return c
}
