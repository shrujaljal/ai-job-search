import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Button, Field, inputCls } from './ui'

export function AccountSwitcher() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.getAccounts, retry: false })
  const activate = useMutation({
    mutationFn: api.activateAccount,
    onSuccess: () => window.location.reload(),
  })
  const create = useMutation({
    mutationFn: api.createAccount,
    onSuccess: () => window.location.reload(),
  })

  if (!accounts.data) return null
  const busy = activate.isPending || create.isPending
  return (
    <>
      <div className="flex items-center gap-1">
        <select
          aria-label="Active profile"
          className="max-w-32 rounded-lg border border-slate-300 bg-white/80 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800 sm:max-w-40"
          value={accounts.data.active_id}
          disabled={busy}
          onChange={(event) => activate.mutate(event.target.value)}
        >
          {accounts.data.accounts.map((account) => (
            <option key={account.id} value={account.id}>{account.name}</option>
          ))}
        </select>
        <button
          type="button"
          title="Add profile"
          aria-label="Add profile"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-300 text-lg hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          onClick={() => setOpen(true)}
        >
          +
        </button>
      </div>
      {open && createPortal((
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog" aria-modal="true" aria-labelledby="new-profile-title"
          onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-slate-900">
            <h2 id="new-profile-title" className="text-lg font-semibold">New profile</h2>
            <div className="mt-4">
              <Field label="Profile name">
                <input autoFocus className={inputCls} value={name}
                  onChange={(event) => setName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && name.trim()) create.mutate(name.trim())
                    if (event.key === 'Escape') setOpen(false)
                  }}
                  placeholder="e.g. Shrujal - Strategy roles" />
              </Field>
            </div>
            {create.isError && <p className="mt-3 text-sm text-rose-600">{create.error.message}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button disabled={!name.trim() || create.isPending}
                onClick={() => create.mutate(name.trim())}>Create profile</Button>
            </div>
          </div>
        </div>
      ), document.body)}
    </>
  )
}
