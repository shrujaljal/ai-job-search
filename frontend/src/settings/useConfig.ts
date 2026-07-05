import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

/** Load / save / reset one config document (profile, rules, resume_content). */
export function useConfig<T = Record<string, unknown>>(name: string) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['config', name], queryFn: () => api.getConfig<T>(name), retry: false })
  const save = useMutation({
    mutationFn: (d: T) => api.putConfig(name, d),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config', name] }),
  })
  const reset = useMutation({
    mutationFn: () => api.resetConfig<T>(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config', name] }),
  })
  return { data: q.data, isLoading: q.isLoading, save, reset }
}
