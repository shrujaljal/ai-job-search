import { createContext, useContext } from 'react'

export type Mode = 'light' | 'dark'
export type Accent = 'violet' | 'emerald' | 'sky' | 'rose' | 'amber'
export const ACCENTS: Accent[] = ['violet', 'emerald', 'sky', 'rose', 'amber']

export interface ThemeContextValue {
  mode: Mode
  accent: Accent
  toggleMode: () => void
  setAccent: (accent: Accent) => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme outside ThemeProvider')
  return context
}
