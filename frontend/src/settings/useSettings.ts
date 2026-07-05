import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Settings } from '../api'

export function useSettings() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
  const save = useMutation({
    mutationFn: (s: Settings) => api.putConfig('settings', s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settings'] }),
  })
  return { settings: q.data, isLoading: q.isLoading, save }
}
