#!/usr/bin/env python3
"""Expose existing, verified recovery and rollback capabilities in Portuguese.

Repair checks recoverable file effects, with no unverified replay. Regress
requires the built-in confirmed Undo preview for supported file changes.
Browser, shell and unknown effects are not fabricated as reversible.
"""
from pathlib import Path
import argparse

def change(path,old,new):
    content=path.read_text(encoding="utf-8")
    if content.count(old)!=1:
        raise RuntimeError(f"Unexpected recovery UI: {path}: {content.count(old)}")
    path.write_text(content.replace(old,new,1),encoding="utf-8",newline="\n")

def main(root):
    target=root/"frontend"/"src"/"components"/"RecoveryPanel.tsx"
    change(target,
        """        <h2 className="text-xs font-medium text-neutral-200">{needsReview ? 'Review before continuing' : 'File changes'}</h2>
      </header>""",
        """        <h2 className="text-xs font-medium text-neutral-200">
          {needsReview ? 'Reparar execução ou regressar' : 'Alterações de arquivos e reversão'}
        </h2>
      </header>
      {needsReview && (
        <div className="space-y-2 text-[11px] text-neutral-300">
          <p>Reparar: verifique o resultado de uma ação com prova disponível (botão abaixo).
            Se não há prova, examine o aplicativo e depois retome por um ponto seguro.</p>
          <p>Regressar: apenas modificações de arquivos com Undo disponível podem ser
            revertidas automaticamente, com prévia e confirmação. Ações do navegador,
            comandos e instalações não possuem reversão geral garantida.</p>
          {onRefresh && (
            <button type="button" className="rounded-md border border-white/10 px-2 py-1 underline"
              onClick={() => void onRefresh()}>
              Atualizar diagnóstico da execução
            </button>
          )}
        </div>
      )}""")
    change(target,"                      Verify\n                    </button>",
        "                      Reparar (verificar)\n                    </button>")
    change(target,"                      Skip\n                    </button>",
        "                      Ignorar somente após revisar\n                    </button>")
    change(target,"                            > Undo\n", "                            > Regressar (desfazer)\n")
    print("Recovery guidance added; no automatic replay or unsafe rollback.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("monaw_root",type=Path)
    main(parser.parse_args().monaw_root.resolve())
