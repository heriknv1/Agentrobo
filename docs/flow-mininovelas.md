# Agentrobo — Estúdio de Mininovelas (projeto de integração futura com Google Flow)

**Estado:** planejamento de produto; ainda não abre, controla ou gasta créditos no Google Flow. Não inserir autenticação Google, cookies ou senhas no repositório.

## Objetivo

Transformar um pedido como "crie o episódio 1 de uma mininovela" em roteiro, ficha de personagens, plano de cenas, prompts reutilizáveis, produção supervisionada de clipes e montagem. O usuário define orçamento máximo, duração, gênero, público e grau de autonomia. O agente deve priorizar coerência narrativa, continuidade visual e custo baixo.

## Fluxo econômico proposto

1. **Planejar sem gerar:** sinopse, arco de 4 a 8 episódios, objetivos dramáticos e cliffhanger por episódio; duração e quantidade de clipes estimadas.
2. **Bíblia da série:** identidades fictícias dos personagens, descrição visual estável, roupa, voz, sotaque, personalidade, relacionamentos, local, hora do dia, proibições e continuidade. Usar IDs estáveis (`CHAR01`, `SET01`).
3. **Storyboard:** plano por cena com quadro inicial, objetivo, duração desejada, câmera, direção de arte, diálogo/som, transição e ID do próximo clipe.
4. **Prompts:** redigir em inglês as instruções visuais para maior consistência quando necessário; manter diálogos em português brasileiro e revisar pronúncia. Conferir se modelo/áudio/duração são realmente suportados pela conta.
5. **Orçamento:** ler na interface oficial o saldo de créditos e o custo por geração, perguntar teto de créditos do projeto e *nunca iniciar uma geração acima dele*. Usar 1 saída por pedido, salvo autorização explícita; não repetir automaticamente clipes de resultado incerto.
6. **Prova de conceito:** gerar apenas uma cena/piloto aprovada; conferir se a personagem, roupa, voz, cenário e movimento estão coerentes antes de gastar na próxima.
7. **Episódio:** salvar original e versão aprovada com ID estável e metadados (modelo, créditos estimados/efetivos, prompt, duração, data, status). Não regenerar uma cena já satisfatória.
8. **Montagem:** organizar arquivos em pasta do episódio, criar planilha simples de cenas, lista de tomadas, músicas originais/licenciadas e instruções de edição. Não garantir edição sem ferramenta adequada.
9. **Recuperação:** após erro de UI/rede, primeiro reler o projeto e verificar se a mídia já foi criada. Repetir somente se o resultado anterior comprovadamente não existe e ainda há orçamento autorizado.
10. **Entrega:** apresentar progresso, arquivos/cenas concluídos, inconsistências, consumo observado e o que falta. Notificar usuário quando houver uma decisão de crédito ou revisão visual.

## Política de créditos (consultar novamente na data de uso)

Documentação oficial (verificada em 2026-11-17):
- https://support.google.com/flow/answer/16526234?hl=en
- https://support.google.com/flow/answer/17093911?hl=en
- https://support.google.com/flow/answer/16353333?hl=en

Sem plano Google AI: 50 créditos por dia para testar, sujeito a disponibilidade/rate limits. Em 2026-11-17, Omni Flash 1.2 cobra 1 crédito/s a 360p ou 3 créditos/s a 720p (até 10 s), e Veo 3.1 Lite custa 10 créditos por clipe de 4/6/8 s para não-Ultra. **Custos mudam**: exigir confirmação do custo exibido antes de cada produção. O Flow Agent integrado permite planejar e elaborar prompts sem cobrança de créditos Flow para consultas, sujeito a limite de mensagens.

## Limites técnicos e de segurança

- Google Flow está disponível no Brasil, mas funções/modelos podem depender da conta e da região.
- A integração com o Monaw dependerá do funcionamento da extensão Chrome; não supor API pública para automação, não usar endpoints privados, nem contornar CAPTCHA, login, limites ou proteção anti-bot.
- É preferível usar o Google Flow Agent nativo para roteiro, storyboard e prompting, quando for mais confiável que automação frágil por cliques.
- A aprovação de créditos é **sempre explícita** e com custo exibido; a aprovação genérica de baixo risco por notificação não autoriza gerações pagas.
- Nunca enviar credenciais, cookies, resultados pessoais ou materiais gerados para o repositório público.
- Nada de refazer cena automaticamente após travamento sem confirmar se créditos foram cobrados ou se clipe foi gerado.
- O notebook Windows 10 com 8 GB RAM fica só como interface/organização; processamento de vídeo ocorre no Flow.
- Manter separadas permissão de acesso do Chrome, permissão para geração e uso de créditos e permissão para baixar mídia no computador.

## Próxima etapa quando o usuário quiser ativar

1. Confirmar acesso manual a https://labs.google/fx/tools/flow e características da conta.
2. Verificar Chrome/Monaw com leitura de página segura e captura de tela; corrigir `Browser action · Uncertain` com teste de leitura, não com envio de geração.
3. Criar primeira mininovela com roteiro e 1 cena piloto, sem uso automático de créditos.
4. Só depois implementar no Agentrobo uma integração supervisionada de geração por etapas e orçamento.
