# Estúdio de Mininovelas — Agentrobo v0.1 (720p)

Skill integrada ao Monaw 1.1.0, compilada pelo GitHub Actions do repositório Agentrobo. Usa o modelo de IA que já estiver conectado ao Monaw para escrever roteiros, fichas e prompts. Os clipes são gerados no Google Flow pela interface oficial do navegador, sem endpoints privados.

## Implementado no código

- Projetos por episódios, personagens e cenários, com IDs estáveis.
- Ficha de aparência, voz e figurino; imagens de referência PNG/JPG/WebP locais.
- Planejamento e revisão de cenas com prompts de continuidade e diálogos em português brasileiro.
- Modelos permitidos exclusivamente: Veo 3.1 Lite e Omni Flash 1.2, sempre 720p.
- Orçamento por episódio e por dia, contabilizando tentativas de resultado incerto. O preço real exibido no Flow prevalece.
- Estados: planned → prepared → uncertain após envio → generated → approved/rejected.
- Importação de clipes com FFprobe (1280x720 ou 720x1280 nativos).
- Montagem local em MP4 de 720p com FFmpeg, após todas as cenas serem aprovadas.

## Integração realista com Google Flow

O Monaw possui extensão Chrome com ferramentas de leitura e ação na página. A skill instrui o agente a abrir o Flow, ler as configurações reais, selecionar modelo, duração, 720p e um resultado, preencher o prompt e só gerar com autorização apropriada para consumo de créditos.

O estúdio não usa API privada nem contorna login, CAPTCHA, limites ou políticas do Google. A automação de envio/download no formulário real do Flow precisa ser validada no Windows do usuário, pois a interface muda. Se o navegador perder a conexão, o agente não pode repetir automaticamente a geração.

**A v0.1 não é uma fila autônoma de geração em nuvem e não substitui um editor profissional.** É uma base de planejamento, controle de créditos, continuidade, arquivos e montagem, com automação supervisionada do navegador.

## Como usar por voz ou escrita

Depois de compilar e instalar no Monaw:

"Jarvis, use o Estúdio de Mininovelas. Crie uma série brasileira de suspense e romance chamada Segredos da Rua 12, com três personagens fixos, duas locações e um episódio piloto de 40 segundos em 16:9. Faça roteiro e cenas, priorizando Veo 3.1 Lite, 720p e orçamento de 50 créditos hoje. Não gaste créditos antes de eu autorizar. Mostre o plano e a primeira cena."

Ferramentas: studio_list_projects, studio_create_project, studio_story_bible, studio_attach_reference, studio_plan_episode, studio_revise_scene, studio_next_scene, studio_prepare_scene, studio_record_generation, studio_reconcile_no_charge, studio_import_clip, studio_review_clip, studio_assemble_episode, studio_project_status.

Quando pronto para gerar:

"Jarvis, produza a próxima cena no Flow. Confira visualmente Veo 3.1 Lite, resolução 720p, 8 segundos, uma geração e 10 créditos antes de pedir minha autorização. Se a conexão cair, leia novamente a página antes de qualquer tentativa."

Quando terminar:

"Jarvis, encontre e baixe o clipe, valide 720p nativo, importe ao projeto, revise a continuidade e monte o episódio quando todas as cenas estiverem aprovadas."

## Requisitos de instalação

- Windows 10, Monaw empacotado com a skill do Agentrobo, extensão Chrome conectada.
- Login Google feito manualmente pelo usuário no Flow, com créditos disponíveis.
- FFmpeg e FFprobe no PATH do Windows para importar e montar clipes. Verifique no PowerShell: ffmpeg -version e ffprobe -version.
- Dados locais ficam em Documents/monaw/Agentrobo-Studio ou no workspace configurado. Não suba essa pasta para o repositório público.

## Créditos oficiais (17/11/2026)

| Modelo | Resolução | Clipes | Custo padrão para não-Ultra |
| --- | --- | --- | --- |
| Veo 3.1 Lite | 720p | 4, 6 ou 8 segundos | 10 créditos por geração |
| Omni Flash 1.2 | 720p | 3–10 segundos sem assinatura | 3 créditos por segundo |

Fontes: https://support.google.com/flow/answer/16526234?hl=pt-BR e https://support.google.com/flow/answer/16352836?hl=pt-BR. Preços e acesso podem mudar.

## Estados e retomada

- planned: sem geração, cena pode ser editada
- prepared: prompt e orçamento verificados
- uncertain: ação enviada, mas resultado sem confirmação; não reenviar automaticamente
- generated: clipe local importado com resolução confirmada
- approved: vídeo aprovado para montagem
- rejected: clipe rejeitado e preservado, nova tomada exige orçamento e aprovação

A contabilidade local não substitui o saldo oficial do Flow nem inclui automaticamente gastos feitos fora do estúdio.

## Build e validação

O workflow Windows instala a skill, executa testes unitários e confirma o registro de suas ferramentas no Monaw. O instalador só será publicado se os testes passarem. A etapa de navegação real no Flow e a montagem com FFmpeg exigem testes no notebook e não são comprovadas por um build de código.
