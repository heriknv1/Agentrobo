#!/usr/bin/env python3
"""Display bounded browser recovery evidence in Monaw's existing recovery panel.

Only shows evidence already projected by the backend. Does not change the
durable journal, how browser tools execute, or retry decisions.
"""
from pathlib import Path
import argparse

BEFORE = """                    {operation.effect_class === 'opaque_effect' && isUnresolved && (
                      <p className="mt-1 text-[10px] leading-relaxed text-amber-200">This action can’t be checked automatically. Review its effect before continuing.</p>
                    )}
"""

AFTER = """                    {(operation.operation_kind === 'browser_action'
                      || typeof operation.evidence.browser_status === 'string') && isUnresolved && (
                      <div className="mt-1 space-y-1 rounded-md border border-amber-500/20 bg-amber-500/5 p-2 text-[10px] text-amber-100">
                        <p className="font-semibold">Ação do navegador precisa de revisão</p>
                        {typeof operation.evidence.browser_reason_code === 'string' && (
                          <p>Motivo informado: <code>{operation.evidence.browser_reason_code}</code></p>
                        )}
                        {typeof operation.evidence.action_executed === 'boolean' && (
                          <p>Entrada enviada ao navegador: {operation.evidence.action_executed ? 'sim' : 'não'}</p>
                        )}
                        <p>Confira se a página abriu no Chrome e se a extensão do Monaw está conectada. Veja também Settings → Browser e Settings → Execution detail → Developer. Não repita cliques, envios ou downloads sem verificar a página atual.</p>
                      </div>
                    )}
                    {operation.effect_class === 'opaque_effect' && isUnresolved && (
                      <p className="mt-1 text-[10px] leading-relaxed text-amber-200">This action can’t be checked automatically. Review its effect before continuing.</p>
                    )}
"""

def main(root: Path):
    path = root / "frontend" / "src" / "components" / "RecoveryPanel.tsx"
    source = path.read_text(encoding="utf-8")
    if AFTER in source:
        print("Already patched")
        return
    if source.count(BEFORE) != 1:
        raise RuntimeError("Unexpected Monaw version: recovery panel anchor differs")
    path.write_text(source.replace(BEFORE, AFTER, 1), encoding="utf-8", newline="\n")
    print("Browser recovery diagnostics added; safety gates unchanged")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("monaw_root", type=Path)
    args = parser.parse_args()
    main(args.monaw_root.resolve())
