import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'

/**
 * Kaya — a friendly companion that cheers the user on. Animated SVG blob with
 * a gentle float, occasional blink, and a rotating encouragement speech bubble.
 */
export function Mascot({ name, streak = 0 }: { name?: string; streak?: number }) {
  const who = name ? `, ${name}` : ''
  const lines = useMemo(() => {
    const base = [
      `Hi${who}! I'm Kaya. Let's land a role today. 🌟`,
      `One tailored résumé at a time${who} — you've got this. 💪`,
      `Small steps, big momentum. I believe in you${who}. 🚀`,
      `Every "no" clears the path to your "yes". Keep going. 🌈`,
      `Proud of you for showing up today${who}. ✨`,
    ]
    if (streak >= 2) base.unshift(`🔥 ${streak}-day streak! You're on fire${who}!`)
    return base
  }, [who, streak])

  const [i, setI] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % lines.length), 5000)
    return () => clearInterval(t)
  }, [lines.length])

  return (
    <div className="flex items-center gap-4">
      <motion.div
        initial={{ scale: 0, rotate: -20 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 12 }}
        className="shrink-0"
        style={{ animation: 'floaty 3.4s ease-in-out infinite' }}
      >
        <KayaSVG />
      </motion.div>

      <div className="relative flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.35 }}
            className="relative rounded-2xl border border-slate-200/70 bg-white/90 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm dark:border-slate-700 dark:bg-slate-800/90 dark:text-slate-200"
          >
            <span
              className="absolute -left-2 top-1/2 h-3 w-3 -translate-y-1/2 rotate-45 border-b border-l border-slate-200/70 bg-white/90 dark:border-slate-700 dark:bg-slate-800/90"
            />
            {lines[i]}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

function KayaSVG() {
  return (
    <svg width="76" height="76" viewBox="0 0 100 100" aria-label="Kaya the companion">
      <defs>
        <linearGradient id="kaya-body" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--accent)" />
          <stop offset="100%" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      {/* body */}
      <path d="M50 8 C74 8 88 26 88 52 C88 78 72 92 50 92 C28 92 12 78 12 52 C12 26 26 8 50 8 Z"
        fill="url(#kaya-body)" />
      {/* belly */}
      <ellipse cx="50" cy="60" rx="24" ry="22" fill="#fff" opacity="0.9" />
      {/* eyes (blink) */}
      <g style={{ transformOrigin: '38px 46px', animation: 'blink 4.2s infinite' }}>
        <circle cx="38" cy="46" r="6.5" fill="#fff" />
        <circle cx="39.5" cy="47" r="3.2" fill="#1e293b" />
      </g>
      <g style={{ transformOrigin: '62px 46px', animation: 'blink 4.2s infinite' }}>
        <circle cx="62" cy="46" r="6.5" fill="#fff" />
        <circle cx="63.5" cy="47" r="3.2" fill="#1e293b" />
      </g>
      {/* cheeks */}
      <circle cx="30" cy="58" r="4" fill="#fca5a5" opacity="0.7" />
      <circle cx="70" cy="58" r="4" fill="#fca5a5" opacity="0.7" />
      {/* smile */}
      <path d="M42 62 Q50 70 58 62" stroke="#1e293b" strokeWidth="2.6" fill="none" strokeLinecap="round" />
      {/* little antenna */}
      <line x1="50" y1="10" x2="50" y2="3" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="50" cy="2.5" r="2.6" fill="var(--accent-2)" />
    </svg>
  )
}
