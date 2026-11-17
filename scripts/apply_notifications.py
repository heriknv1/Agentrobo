#!/usr/bin/env python3
"""Add local Windows task completion alerts to a clean Monaw v1.1.0 checkout.

No user data, credentials, prompts, or private task details are sent to GitHub
or embedded in notifications. Refuses to patch unknown upstream layouts.
"""
from pathlib import Path
import argparse

PRELOAD_ANCHOR = "  updateStatus: () => ipcRenderer.invoke('updates:status'),"
PRELOAD_NEW = """  notifyTaskStatus: (status) => {
    if (status !== 'complete' && status !== 'error') throw new TypeError('Invalid task status')
    return ipcRenderer.invoke('tasks:notify', status)
  },
""" + PRELOAD_ANCHOR

MAIN_ANCHOR = "ipcMain.handle('updates:status', (event) => {"
MAIN_NEW = """// Local-only, generic notifications. Never expose prompts or file paths on the lock screen.
ipcMain.handle('tasks:notify', (event, status) => {
  assertTrustedIpcSender(event)
  const kind = assertIpcString(status, 'task status', 16)
  if (kind !== 'complete' && kind !== 'error') {
    throw new Error('Unsupported task status')
  }
  if (!Notification.isSupported() || !mainWindow || mainWindow.isDestroyed()) return false
  // The chat itself shows results when the user is already looking at Monaw.
  if (mainWindow.isFocused() && !mainWindow.isMinimized()) return false
  const notice = new Notification({
    title: kind === 'complete' ? 'Jarvis: tarefa concluída' : 'Jarvis: tarefa interrompida',
    body: kind === 'complete'
      ? 'O Monaw terminou uma resposta. Clique para conferir o resultado.'
      : 'A execução encontrou um erro. Clique para revisar no Monaw.',
  })
  notice.on('click', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
  notice.show()
  return true
})

""" + MAIN_ANCHOR

TYPE_ANCHOR = "      updateStatus?: () => Promise<UpdateState>"
TYPE_NEW = """      /** Local Windows notification for a completed or failed task (no task content). */
      notifyTaskStatus?: (status: 'complete' | 'error') => Promise<boolean>
""" + TYPE_ANCHOR

APP_ANCHOR = "  const resumedRunMessageRefresh = useRef<string | null>(null)"
APP_NEW = """  // Notify only for messages observed running in this window. Old history must
  // never trigger desktop alerts when opening or changing conversations.
  const observedRunningMessages = useRef(new Set<string>())
  useEffect(() => {
    for (const message of messages) {
      if (message.role !== 'assistant') continue
      if (message.streaming) {
        observedRunningMessages.current.add(message.id)
        continue
      }
      if (!observedRunningMessages.current.delete(message.id)) continue
      if (message.runStatus === 'complete' || message.runStatus === 'error') {
        const notify = window.electronAPI?.notifyTaskStatus
        if (notify) void notify(message.runStatus).catch(() => {})
      }
    }
  }, [messages])
""" + APP_ANCHOR

def patch_one(file: Path, anchor: str, replacement: str) -> None:
    text = file.read_text(encoding="utf-8")
    if replacement in text:
        print(f"Already patched: {file}")
        return
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Refusing patch: unexpected upstream layout {file} ({count} anchors)")
    file.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")
    print(f"Patched: {file}")

def main(root: Path) -> None:
    root = root.resolve()
    patch_one(root / "frontend/electron/preload.js", PRELOAD_ANCHOR, PRELOAD_NEW)
    patch_one(root / "frontend/electron/main.js", MAIN_ANCHOR, MAIN_NEW)
    patch_one(root / "frontend/src/types/electron.d.ts", TYPE_ANCHOR, TYPE_NEW)
    patch_one(root / "frontend/src/App.tsx", APP_ANCHOR, APP_NEW)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("monaw_root", type=Path)
    main(parser.parse_args().monaw_root)
