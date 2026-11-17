#!/usr/bin/env python3
"""Add safe handling of conversations blocked from deletion by unresolved Runs.

The original database guard is intentionally left intact. Failed DELETE
requests remain visible, with buttons to inspect the Run or hide the chat
from the sidebar. Hidden chats can be restored. No DB or account data is
deleted by "hide"; hidden IDs are kept locally in Electron renderer storage.
"""
from pathlib import Path
import argparse

def replace_one(path: Path, before: str, after: str) -> None:
    content = path.read_text(encoding="utf-8")
    if after in content:
        print(f"Already patched: {path}")
        return
    occurrences = content.count(before)
    if occurrences != 1:
        raise RuntimeError(f"Upstream layout mismatch for {path}: {occurrences} matching anchors")
    path.write_text(content.replace(before, after, 1), encoding="utf-8", newline="\n")
    print(f"Patched: {path}")

def run(root: Path) -> None:
    app = root / "frontend" / "src" / "App.tsx"
    side = root / "frontend" / "src" / "components" / "Sidebar.tsx"

    replace_one(
        app,
        "import { useItemActions } from './hooks/useItemActions'\n",
        "import { useItemActions } from './hooks/useItemActions'\n"
        "import { ApiError } from './lib/api/client'\n",
    )
    replace_one(
        app,
        "const GUIDE_DISMISSED_KEY = 'monaw.firstRunGuideDismissed'\n",
        """const GUIDE_DISMISSED_KEY = 'monaw.firstRunGuideDismissed'
const ARCHIVED_CHATS_KEY = 'agentrobo.archivedConversations.v1'

// UI-only hide for interrupted conversations. Durable recovery records remain untouched.
function loadArchivedChatIds(): Set<string> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(ARCHIVED_CHATS_KEY) || '[]')
    return new Set(Array.isArray(value)
      ? value.filter((id): id is string => typeof id === 'string' && id.length > 0)
      : [])
  } catch {
    return new Set()
  }
}
""",
    )
    replace_one(
        app,
        "  const [conversations, setConversations] = useState<Conversation[]>([])\n",
        """  const [conversations, setConversations] = useState<Conversation[]>([])
  const [archivedChatIds, setArchivedChatIds] = useState<Set<string>>(loadArchivedChatIds)
  const [deletionBlockedIds, setDeletionBlockedIds] = useState<Set<string>>(new Set())
  useEffect(() => {
    try { window.localStorage.setItem(ARCHIVED_CHATS_KEY, JSON.stringify([...archivedChatIds])) }
    catch { /* Hiding remains available during this session. */ }
  }, [archivedChatIds])
""",
    )
    replace_one(
        app,
        "  const handleDeleteConversation = async (id: string) => {\n",
        """  const archiveConversation = (id: string) => {
    if (conversations.some((conversation) => conversation.id === id && conversation.running)) return
    setArchivedChatIds((current) => new Set(current).add(id))
    if (id === activeConvIdRef.current) handleNewChat()
  }

  const restoreArchivedConversations = () => {
    setArchivedChatIds(new Set())
  }

  const handleDeleteConversation = async (id: string) => {
""",
    )
    replace_one(
        app,
        """    await perform(\u0060conversation:\u0024{id}\u0060, 'Deleting conversation', () => deleteConversation(id), () => {
      setConversations((current) => current.filter((item) => item.id !== id))
""",
        """    await perform(\u0060conversation:\u0024{id}\u0060, 'Deleting conversation', async () => {
      try {
        await deleteConversation(id)
      } catch (error) {
        // 409 is the durable safety guard: do NOT silently force deletion.
        if (error instanceof ApiError && error.status === 409) {
          setDeletionBlockedIds((current) => new Set(current).add(id))
        }
        throw error
      }
    }, () => {
      setDeletionBlockedIds((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
      setArchivedChatIds((current) => {
        if (!current.has(id)) return current
        const next = new Set(current)
        next.delete(id)
        return next
      })
      setConversations((current) => current.filter((item) => item.id !== id))
""",
    )
    replace_one(
        app,
        "          conversations={conversations}\n          activeId={activeConvId}\n",
        """          conversations={conversations.filter((c) => !archivedChatIds.has(c.id))}
          archivedCount={conversations.filter((c) => archivedChatIds.has(c.id)).length}
          deletionBlockedIds={deletionBlockedIds}
          onArchive={archiveConversation}
          onRestoreArchived={restoreArchivedConversations}
          activeId={activeConvId}
""",
    )

    replace_one(
        side,
        """  conversations: Conversation[]
  activeId: string | null
""",
        """  conversations: Conversation[]
  archivedCount?: number
  deletionBlockedIds?: ReadonlySet<string>
  onArchive?: (id: string) => void
  onRestoreArchived?: () => void
  activeId: string | null
""",
    )
    replace_one(
        side,
        """export function Sidebar({
  conversations,
  activeId,
""",
        """export function Sidebar({
  conversations,
  archivedCount = 0,
  deletionBlockedIds,
  onArchive,
  onRestoreArchived,
  activeId,
""",
    )
    replace_one(
        side,
        """        {feedback?.error && (
          <div role="alert" className="mt-1 pl-5 text-[10px] text-red-300">
            {feedback.error}
            {feedback.retry && <button type="button" onClick={() => feedback.retry?.()} className="ml-1 underline">Retry</button>}
          </div>
        )}
""",
        """        {feedback?.error && (
          <div role="alert" className="mt-1 pl-5 text-[10px] text-red-300">
            {deletionBlockedIds?.has(c.id)
              ? 'Não foi possível excluir: há uma execução interrompida ou ação pendente de revisão.'
              : feedback.error}
            {deletionBlockedIds?.has(c.id) ? (
              <div className="mt-1 flex flex-wrap gap-2 text-neutral-300">
                <button type="button" className="underline" onClick={() => onSelect(c.id)}>
                  Revisar execução
                </button>
                {onArchive && !c.running && <button type="button" className="underline" onClick={() => onArchive(c.id)}>
                  Ocultar da lista
                </button>}
                <span className="basis-full text-neutral-500">
                  Ocultar não exclui dados nem cancela tarefas. Você pode restaurar depois.
                </span>
              </div>
            ) : (
              <>
                {feedback.retry && <button type="button" onClick={() => feedback.retry?.()} className="ml-1 underline">Tentar novamente</button>}
                {onArchive && !c.running && <button type="button" onClick={() => onArchive(c.id)} className="ml-2 underline">
                  Ocultar da lista
                </button>}
              </>
            )}
          </div>
        )}
""",
    )
    replace_one(
        side,
        """        <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto px-2 pb-2">

          {conversations.length === 0 ? (
""",
        """        {archivedCount > 0 && onRestoreArchived && (
          <div className="shrink-0 px-3 pb-2">
            <button
              type="button"
              className="text-[11px] text-neutral-400 underline hover:text-neutral-200"
              onClick={onRestoreArchived}
              title="Conversas ocultas continuam salvas e podem ser revisadas"
            >
              Restaurar conversas ocultas ({archivedCount})
            </button>
          </div>
        )}
        <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto px-2 pb-2">

          {conversations.length === 0 ? (
""",
    )
    replace_one(
        side,
        "Conversations will appear here after the first response.",
        "Nenhuma conversa visível. Se houver conversas ocultas, você pode restaurá-las acima.",
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("monaw_root", type=Path)
    run(parser.parse_args().monaw_root.resolve())
