import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'info'

export const ToastContext = createContext<{ notify: (message: string, tone?: ToastTone) => void }>({
  // Outside a provider (isolated component tests) notifications are a no-op.
  notify: () => undefined,
})

export function useToast() {
  return useContext(ToastContext)
}
