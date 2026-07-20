import { useEffect, useState, type ReactNode } from 'react'
import { ThemeContext, type Accent, type Mode } from './theme-context'

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
    <ThemeContext.Provider value={{
      mode, accent,
      toggleMode: () => setMode((m) => (m === 'dark' ? 'light' : 'dark')),
      setAccent: setAccentState,
    }}>
      {children}
    </ThemeContext.Provider>
  )
}
