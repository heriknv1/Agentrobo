#!/usr/bin/env python3
"""Explicit user-confirmed permanent deletion of stopped, unresolved conversations.

Does not pretend that deleting the local history rolls back external effects.
Cannot discard a Run while live execution is registered or a DB operation is
still in prepared/authorized/executing state.
"""
from pathlib import Path
import argparse

def replace(path, old, new):
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise RuntimeError(f"Unknown pinned upstream layout: {path}, found {src.count(old)} anchors")
    path.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("Patched", path)

def main(root):
    backend=root/"backend"/"app"
    db=backend/"agent"/"database.py"
    memory=backend/"agent"/"memory_manager.py"
    route=backend/"api"/"routes"/"conversations.py"
    client=root/"frontend"/"src"/"lib"/"api"/"conversations.ts"
    app=root/"frontend"/"src"/"App.tsx"
    sidebar=root/"frontend"/"src"/"components"/"Sidebar.tsx"

    replace(db,
        '    def delete_conversation(self, conv_id: str) -> bool:\n',
        '    def delete_conversation(self, conv_id: str, *, discard_unresolved: bool = False) -> bool:\n')
    replace(db,
        '''            if unresolved is not None:
                raise ConversationHasUnresolvedRunError(
                    "Resolve or stop active and recoverable Runs before deleting this conversation."
                )

            candidate_refs''',
        '''            if unresolved is not None:
                if not discard_unresolved:
                    raise ConversationHasUnresolvedRunError(
                        "Resolve or stop active and recoverable Runs before deleting this conversation."
                    )
                # The caller explicitly discarded recovery history. Still refuse
                # if a worker might be able to dispatch another action.
                busy = conn.execute(
                    """SELECT 1 FROM agent_runs AS r
                       WHERE r.conversation_id = ?
                         AND (
                           r.status IN ('running','waiting_approval','pausing')
                           OR EXISTS (
                             SELECT 1 FROM run_operations AS o
                             WHERE o.run_id = r.run_id AND
                               o.status IN ('prepared','authorized','executing')
                           )
                         ) LIMIT 1""",
                    (conv_id,),
                ).fetchone()
                if busy is not None:
                    raise ConversationHasUnresolvedRunError(
                        "A Run or operation is still active; permanent deletion is blocked."
                    )

            candidate_refs''')
    replace(memory,
        'def delete_conversation_file(conversation_id: str) -> bool:\n',
        'def delete_conversation_file(conversation_id: str, *, discard_unresolved: bool = False) -> bool:\n')
    replace(memory,
        '    return get_db().delete_conversation(conversation_id)\n',
        '    return get_db().delete_conversation(conversation_id, discard_unresolved=discard_unresolved)\n')
    replace(memory,
        '    def delete(self, conversation_id: str) -> bool:\n',
        '    def delete(self, conversation_id: str, *, discard_unresolved: bool = False) -> bool:\n')
    replace(memory,
        '        found_db = self._db.delete_conversation(conversation_id)\n',
        '        found_db = self._db.delete_conversation(conversation_id, discard_unresolved=discard_unresolved)\n')
    replace(route,
        '''@router.delete("/conversations/{conv_id}", response_model=OkResponse)
async def delete_conversation(conv_id: str):
    memory_manager = peek_memory_manager()
    try:
        found = memory_manager.delete(conv_id) if memory_manager is not None else delete_conversation_file(conv_id)
''',
        '''@router.delete("/conversations/{conv_id}", response_model=OkResponse)
async def delete_conversation(
    conv_id: str,
    discard_unresolved: bool = False,
    confirmation: str = "",
):
    # Deleting evidence never undoes external actions. Require an explicit
    # opt-in for unresolved, stopped Runs; ordinary DELETE stays protected.
    if discard_unresolved and confirmation != "EXCLUIR":
        raise HTTPException(status_code=400, detail="Explicit permanent deletion confirmation required.")
    if discard_unresolved:
        from app.agent.durable.turn_run import get_active_lifecycle
        db = get_db()
        with db.transaction(immediate=False) as conn:
            run_ids = [str(row["run_id"]) for row in conn.execute(
                "SELECT run_id FROM agent_runs WHERE conversation_id = ?", (conv_id,)
            ).fetchall()]
        if any(get_active_lifecycle(run_id) is not None for run_id in run_ids):
            raise HTTPException(status_code=409, detail="A Run is still active. Stop it before deleting.")
    memory_manager = peek_memory_manager()
    try:
        if discard_unresolved:
            found = (
                memory_manager.delete(conv_id, discard_unresolved=True)
                if memory_manager is not None
                else delete_conversation_file(conv_id, discard_unresolved=True)
            )
        else:
            # Preserve the upstream call contract and existing safety tests.
            found = memory_manager.delete(conv_id) if memory_manager is not None else delete_conversation_file(conv_id)
''')
    replace(client,
        '''export async function deleteConversation(id: string): Promise<void> {
''',
        '''export async function permanentlyDeleteStoppedConversation(id: string): Promise<void> {
  const params = new URLSearchParams({ discard_unresolved: 'true', confirmation: 'EXCLUIR' })
  const res = await apiFetch(
    `${BASE}/api/conversations/${encodeURIComponent(id)}?${params}`,
    { method: 'DELETE' },
  )
  if (!res.ok && res.status !== 404) return throwApiError(res, 'Não foi possível excluir a conversa: pode haver uma tarefa em execução')
}

export async function deleteConversation(id: string): Promise<void> {
''')
    replace(app,
        "import { deleteConversation, fetchConversations,",
        "import { deleteConversation, permanentlyDeleteStoppedConversation, fetchConversations,")
    replace(app,
        '''  const handleDeleteConversation = async (id: string) => {
''',
        '''  const permanentlyDeleteConversation = async (id: string) => {
    const conversation = conversations.find((item) => item.id === id)
    if (!conversation || conversation.running) return
    if (!window.confirm(
      'EXCLUIR DEFINITIVAMENTE esta conversa com erro?\\n\\n'
      + 'O histórico e os registros de recuperação serão apagados. '
      + 'Alterações já feitas no computador NÃO serão desfeitas. '
      + 'Não será possível restaurar esta conversa.'
    )) return
    await perform(`conversation:${id}`, 'Excluindo definitivamente', () =>
      permanentlyDeleteStoppedConversation(id), () => {
        setConversations((current) => current.filter((item) => item.id !== id))
        setDeletionBlockedIds((current) => {
          const next = new Set(current)
          next.delete(id)
          return next
        })
        setArchivedChatIds((current) => {
          const next = new Set(current)
          next.delete(id)
          return next
        })
        if (id === activeConvIdRef.current) handleNewChat()
      })
  }

  const handleDeleteConversation = async (id: string) => {
''')
    replace(app,
        '''          onArchive={archiveConversation}
          onRestoreArchived={restoreArchivedConversations}
''',
        '''          onArchive={archiveConversation}
          onPermanentDelete={permanentlyDeleteConversation}
          onRestoreArchived={restoreArchivedConversations}
''')
    replace(sidebar,
        '''  onArchive?: (id: string) => void
  onRestoreArchived?: () => void
''',
        '''  onArchive?: (id: string) => void
  onPermanentDelete?: (id: string) => void
  onRestoreArchived?: () => void
''')
    replace(sidebar,
        '''  onArchive,
  onRestoreArchived,
''',
        '''  onArchive,
  onPermanentDelete,
  onRestoreArchived,
''')
    replace(sidebar,
        '''                <span className="basis-full text-neutral-500">
                  Ocultar não exclui dados nem cancela tarefas. Você pode restaurar depois.
                </span>''',
        '''                {onPermanentDelete && !c.running && (
                  <button type="button" className="font-semibold text-red-300 underline"
                    onClick={() => onPermanentDelete(c.id)}>
                    Excluir definitivamente
                  </button>
                )}
                <span className="basis-full text-neutral-500">
                  Excluir definitivamente apaga o histórico, mas NÃO desfaz ações no computador.
                  Operações ainda ativas continuam protegidas.
                </span>''')

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("monaw_root",type=Path)
    main(p.parse_args().monaw_root.resolve())
