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

## Limpeza segura de conversas com erro

Depois de uma falha, se uma conversa tiver Run interrompido ou ação com resultado incerto, o Monaw pode bloquear a exclusão com HTTP 409 para preservar as evidências de segurança. Esta compilação **não contorna** esse bloqueio.

Ao tentar excluir uma conversa bloqueada, você poderá:
- **Revisar execução**, abrindo a conversa para verificar o estado no painel de recuperação;
- **Ocultar da lista**, sem apagar mensagens, arquivos, registros ou tarefas em andamento;
- usar **Restaurar conversas ocultas** para trazê-las de volta.

Quando o servidor permitir, a exclusão normal continuará removendo a conversa permanentemente. A lista de IDs ocultos fica somente no armazenamento local da interface do Monaw; limpar o cache/dados da interface poderá restaurar a visualização dessas conversas. Não publique o perfil do Monaw no GitHub.

## Evitar revisão desnecessária em ações simples (correção experimental)

O workflow também aplica `scripts/apply_safe_preflight.py` e executa testes de regressão antes do empacotamento. O patch só marca como **falha sem efeitos** as rejeições do controlador `computer_functions_act` que ocorrem **antes de qualquer tentativa de colocar a janela em foco, clicar, digitar ou iniciar programas**. A classificação é autenticada pela própria função local dentro do mesmo contexto da operação; **nunca** depende de campos enviados pela IA.

Se já ocorreu tentativa de interação, falha de verificação, timeout ou perda de conexão, a execução continua sujeita à revisão. Isso é intencional: os registros não podem afirmar que uma ação não aconteceu sem evidência.

O erro `This run needs review before it can safely continue` ainda pode aparecer por motivos diferentes (execuções de comandos, automação no navegador, falha depois do envio de teclas, operações de arquivos e outros). Para diagnosticar, expanda **Used tools** e verifique o nome da primeira ferramenta com erro e os seus `reason_code`/`error`. Não repita cegamente a mesma ação.

## Conversas com erro: exclusão definitiva

A compilação acrescenta **Excluir definitivamente** depois de uma tentativa de exclusão bloqueada por uma execução interrompida. Esse comando exige uma confirmação explícita na interface e transmite `discard_unresolved=true&confirmation=EXCLUIR` ao servidor local autenticado. O banco de dados continua recusando apagar conversas com Runs ativos ou operações ainda preparadas, autorizadas ou executando. Em uma conversa parada, a opção apaga de fato a conversa e seus registros de execução locais, em vez de apenas ocultá-la.

**Excluir não reverte efeitos externos:** se o agente mudou algo no Chrome, em arquivos, no Holyrics ou no Windows, essa alteração pode permanecer. Antes da exclusão, use a recuperação ou o Undo quando disponível. Não publique o banco local no GitHub.

## Recuperar ou regressar

A seção de recuperação mostra **Reparar (verificar)** quando o sistema dispõe de prova verificável de uma operação sobre arquivo. **Regressar (desfazer)** usa a prévia e a confirmação já previstas no mecanismo Undo do Monaw para arquivos compatíveis. Ações de navegador, comandos externos e instalações não podem ser automaticamente revertidos de forma geral. Para falhas não verificáveis, revise o aplicativo de destino e retome de um ponto seguro; a ferramenta não repete silenciosamente uma ação incerta.

## Aprovação pela notificação do Windows

Quando um ticket de aprovação é criado, o Monaw pode notificar mesmo com a janela minimizada. **Aprovar** e **Recusar** aparecem somente para pedidos categorizados como de baixo risco e pertencentes à lista restrita de ações de leitura, abertura ou navegação; antes de resolver, o aplicativo consulta novamente o ticket e o backend aplica suas próprias regras de autorização. Para pedidos sensíveis, a notificação oferece somente **Revisar no app**.

Os avisos não incluem senhas, caminhos pessoais nem conteúdo da conversa. Esse recurso depende das notificações do Windows estarem habilitadas, da integração Electron estar ativa e do notebook não estar suspenso. Os botões ainda precisam ser validados em uma instalação Windows 10 real, e algumas configurações do sistema podem suprimir a notificação ou trazer o aplicativo ao primeiro plano.

## Segurança

- Não coloque neste repositório senhas, tokens, chaves de API, logs privados, arquivos de configuração ou a pasta %USERPROFILE%\.monaw.
- Código, logs e artefatos de repositórios públicos podem ser vistos por terceiros.
- O workflow usa apenas execução manual, permissões contents: read, sem secrets e sem publicação automática.
- Antes de instalar a versão experimental, mantenha o Monaw original e faça backup local da pasta %USERPROFILE%\.monaw fora do GitHub.
- O instalador é não oficial e não assinado. Pode substituir a instalação oficial; teste com cuidado.
- A verificação de importação não comprova o controle do Holyrics/Java. Teste primeiro em Bloco de Notas.
- O atualizador do Monaw pode substituir essa compilação.

Origem pública: https://github.com/kailiang0120/monaw (v1.1.0).
