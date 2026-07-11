import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'
import clsx from 'clsx'

interface Toast { id: number; type: 'success' | 'error'; message: string }
interface ToastContextType { success: (msg: string) => void; error: (msg: string) => void }

const ToastContext = createContext<ToastContextType>({ success: () => {}, error: () => {} })

export function useToast() { return useContext(ToastContext) }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  let counter = 0

  const add = useCallback((type: Toast['type'], message: string) => {
    const id = ++counter
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  return (
    <ToastContext.Provider value={{ success: m => add('success', m), error: m => add('error', m) }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3">
        {toasts.map(t => (
          <div key={t.id} className={clsx(
            'flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl animate-slide-up min-w-[280px]',
            t.type === 'success'
              ? 'bg-ethara-success/10 border-ethara-success/30 text-ethara-success'
              : 'bg-ethara-error/10 border-ethara-error/30 text-ethara-error'
          )}>
            {t.type === 'success'
              ? <CheckCircle className="w-4 h-4 shrink-0" />
              : <XCircle className="w-4 h-4 shrink-0" />}
            <span className="text-sm flex-1 text-white">{t.message}</span>
            <button onClick={() => setToasts(p => p.filter(x => x.id !== t.id))}>
              <X className="w-4 h-4 text-ethara-muted hover:text-white" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
