#!/usr/bin/env python3
"""Native Windows approval notifications for trusted, currently pending tickets.

Only tickets marked low-risk by the backend may be approved/denied using a
Windows toast action button. Higher-risk requests always require review in
the app. Before replying, renderer re-fetches the ticket and server rechecks
its status and binding. Never put a token or file path into a notification.
"""
from pathlib import Path
import argparse

def patch(path, old, new):
    content=path.read_text(encoding="utf-8")
    if content.count(old)!=1:
        raise RuntimeError(f"Unexpected pinned Monaw file: {path}; matches={content.count(old)}")
    path.write_text(content.replace(old,new,1),encoding="utf-8",newline="\n")
    print("Patched", path)

def main(root):
    front=root/"frontend"
    main=front/"electron"/"main.js"
    preload=front/"electron"/"preload.js"
    types=front/"src"/"types"/"electron.d.ts"
    approval=front/"src"/"components"/"ApprovalToast.tsx"

    patch(main,
    "ipcMain.handle('tasks:notify', (event, status) => {",
    """// Notifications remain process-local, never use a URL/protocol with an approval token.
const pendingApprovalNotices = new Map()
ipcMain.handle('approval:notify', (event, payload) => {
  assertTrustedIpcSender(event)
  if (!payload || typeof payload !== 'object') throw new TypeError('Invalid approval')
  const id = assertIpcString(payload.ticketId, 'approval ticket id', 128)
  if (!/^[A-Za-z0-9_-]{8,128}$/.test(id)) throw new TypeError('Invalid ticket identifier')
  const risk = assertIpcString(payload.risk, 'risk', 24).toLowerCase()
  const category = assertIpcString(payload.category, 'action category', 50)
  // Do not expose private file paths, descriptions, prompts or API keys in the toast.
  const allowedCategories = new Set(['read','list','launch_app','open_app','navigate','view'])
  const quickApproval = risk === 'low' && !payload.humanOnly && allowedCategories.has(category)
  if (!Notification.isSupported()) return false
  if (pendingApprovalNotices.has(id)) return true
  // Bound lifetime so a stale notification cannot approve a later/replayed ticket.
  const notice = new Notification({
    title: 'Jarvis: aprovação necessária',
    body: quickApproval
      ? `Ação de baixo risco (${category}). Aprovar ou recusar?`
      : 'Ação pendente. Abra o Monaw para revisar os detalhes antes de autorizar.',
    actions: quickApproval ? [
      { type: 'button', text: 'Aprovar' },
      { type: 'button', text: 'Recusar' },
    ] : [{ type: 'button', text: 'Revisar no app' }],
  })
  const entry = { notice, createdAt: Date.now(), quickApproval }
  pendingApprovalNotices.set(id, entry)
  const reveal = () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  }
  notice.on('click', reveal)
  notice.on('action', (_event, index) => {
    if (pendingApprovalNotices.get(id) !== entry || Date.now() - entry.createdAt > 120000) {
      pendingApprovalNotices.delete(id)
      return
    }
    pendingApprovalNotices.delete(id)
    if (entry.quickApproval && (index === 0 || index === 1)
        && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('approval:decision', {
        ticketId: id, decision: index === 0 ? 'approve' : 'reject',
      })
    } else {
      reveal()
    }
  })
  notice.on('close', () => { if (pendingApprovalNotices.get(id) === entry) pendingApprovalNotices.delete(id) })
  notice.show()
  return true
})

ipcMain.handle('tasks:notify', (event, status) => {""")
    # Keep the approval poll responsive while minimized. No other UI actions
    # are executed by this preference change.
    patch(main,
        "    webPreferences: {\n      preload: path.join(__dirname, 'preload.js'),",
        "    webPreferences: {\n      backgroundThrottling: false,\n      preload: path.join(__dirname, 'preload.js'),")
    # Do not embed windows protocol callbacks or trust a toast to authenticate.
    patch(preload,
        "  notifyTaskStatus: (status) => {",
        """  notifyApprovalRequest: (ticket) => {
    if (!ticket || typeof ticket !== 'object') throw new TypeError('Invalid approval')
    return ipcRenderer.invoke('approval:notify', {
      ticketId: safeString(ticket.ticketId, 'ticket id', 128),
      risk: safeString(ticket.risk, 'risk', 24),
      category: safeString(ticket.category, 'category', 50),
      humanOnly: ticket.humanOnly === true,
    })
  },
  onApprovalNotificationDecision: (listener) => {
    if (typeof listener !== 'function') throw new TypeError('Invalid listener')
    const handler = (_event, data) => {
      if (data && (data.decision === 'approve' || data.decision === 'reject')
          && typeof data.ticketId === 'string') listener(data)
    }
    ipcRenderer.on('approval:decision', handler)
    return () => ipcRenderer.removeListener('approval:decision', handler)
  },
  notifyTaskStatus: (status) => {""")
    patch(types,
        "      notifyTaskStatus?: (status: 'complete' | 'error') => Promise<boolean>",
        """      notifyApprovalRequest?: (ticket: {
        ticketId: string; risk: string; category: string; humanOnly: boolean
      }) => Promise<boolean>
      onApprovalNotificationDecision?: (
        listener: (decision: { ticketId: string; decision: 'approve' | 'reject' }) => void
      ) => () => void
      notifyTaskStatus?: (status: 'complete' | 'error') => Promise<boolean>""")
    patch(approval,
        "import { useCallback, useEffect, useState } from 'react'",
        "import { useCallback, useEffect, useRef, useState } from 'react'")
    patch(approval,
        "  const [error, setError] = useState('')",
        """  const [error, setError] = useState('')
  const notifiedTickets = useRef(new Set<string>())
  // Poll in background even while the LLM is streaming and the main window
  // is minimized. Browser Notification cannot reliably provide action buttons.
  useEffect(() => {
    if (!window.electronAPI?.notifyApprovalRequest) return
    let disposed = false
    const checkApprovals = async () => {
      try {
        const pending = await fetchPendingApprovals()
        if (disposed) return
        const activeIds = new Set(pending.map((ticket) => ticket.id))
        for (const known of notifiedTickets.current) {
          if (!activeIds.has(known)) notifiedTickets.current.delete(known)
        }
        for (const ticket of pending) {
          if (notifiedTickets.current.has(ticket.id)) continue
          notifiedTickets.current.add(ticket.id)
          const category = ticket.action_type || ''
          const displayed = await window.electronAPI?.notifyApprovalRequest?.({
            ticketId: ticket.id,
            risk: ticket.risk_level || '',
            category,
            humanOnly: ticket.action_descriptor?.human_only === true,
          })
          if (!displayed) notifiedTickets.current.delete(ticket.id)
        }
      } catch {
        // Offline backend: preserve existing approvals and try again later.
      }
    }
    void checkApprovals()
    const timer = window.setInterval(() => { void checkApprovals() }, 4500)
    return () => { disposed = true; window.clearInterval(timer) }
  }, [])

  useEffect(() => {
    const subscribe = window.electronAPI?.onApprovalNotificationDecision
    if (!subscribe) return
    return subscribe(({ ticketId, decision }) => {
      void (async () => {
        try {
          const pending = await fetchPendingApprovals()
          const ticket = pending.find((item) => item.id === ticketId)
          if (!ticket || ticket.status !== 'pending') return
          const eligible = ticket.risk_level?.toLowerCase() === 'low'
            && ticket.action_descriptor?.human_only !== true
            && ['read','list','launch_app','open_app','navigate','view'].includes(ticket.action_type)
          if (!eligible) return
          if (decision === 'approve') await approveTicket(ticketId)
          else await rejectTicket(ticketId)
          setToast((current) => current?.id === ticketId ? null : current)
        } catch {
          setError('A aprovação na notificação falhou. Abra o Monaw para revisar.')
        }
      })()
    })
  }, [])""")
    patch(approval,
        """        if ('Notification' in window && Notification.permission === 'granted') {""",
        """        if (!window.electronAPI?.notifyApprovalRequest
          && 'Notification' in window && Notification.permission === 'granted') {""")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("monaw_root",type=Path)
    main(p.parse_args().monaw_root.resolve())
