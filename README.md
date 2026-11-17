# Agentrobo — reparo experimental do controlador UIA do Monaw

Repositório público e não oficial, com workflow manual para compilar uma cópia do Monaw v1.1.0 incluindo explicitamente pywinauto, pywin32 e comtypes.

## Executar no GitHub Actions

1. Abra Actions > Monaw UIA - build Windows > Run workflow.
2. O workflow baixa o código público do Monaw fixado no commit 81ee729c37746fe0560096fba98b2c5449cd89c4 (v1.1.0).
3. Aplica o patch de empacotamento, compila o backend PyInstaller e testa importações no executável congelado.
4. Somente se passar gera um instalador de Windows. Baixe o artifact Monaw-UIA-1.1.0-Windows-x64 com instalador e SHA-256 (retenção 3 dias).

## Aviso ao terminar uma tarefa

O projeto também aplica scripts/apply_notifications.py durante o build. Ao concluir ou falhar uma execução de conversa observada pelo Monaw, mostra um aviso nativo do Windows caso a janela do aplicativo esteja minimizada ou sem foco. O alerta usa somente texto genérico (não exibe prompts, resultados ou caminhos privados). Clique no aviso para voltar à janela do Monaw.

Limitações: com o Monaw completamente fechado ou o Windows suspenso, não há notificação; se você trocar de conversa e parar de acompanhar uma execução, o aviso dessa conversa não está garantido. O sistema respeita as configurações de notificações e Assistente de Foco do Windows. Aviso por voz ainda não foi implementado.

## Segurança

- Não coloque neste repositório senhas, tokens, chaves de API, logs privados, arquivos de configuração ou a pasta %USERPROFILE%\.monaw.
- Código, logs e artefatos de repositórios públicos podem ser vistos por terceiros.
- O workflow usa apenas execução manual, permissões contents: read, sem secrets e sem publicação automática.
- Antes de instalar a versão experimental, mantenha o Monaw original e faça backup local da pasta %USERPROFILE%\.monaw fora do GitHub.
- O instalador é não oficial e não assinado. Pode substituir a instalação oficial; teste com cuidado.
- A verificação de importação não comprova o controle do Holyrics/Java. Teste primeiro em Bloco de Notas.
- O atualizador do Monaw pode substituir essa compilação.

Origem pública: https://github.com/kailiang0120/monaw (v1.1.0).
