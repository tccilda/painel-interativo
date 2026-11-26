# Consolidação do Monitor de Previsão em 26/11/2026

O commit estável de referência é `26bd008d5d524cf1e1f07f09b428b6279c911503`. O [PR #1](https://github.com/tccilda/painel-interativo/pull/1) integrou `dev` à `main` com um commit de merge de dois pais, preservando os cinco commits e suas autorias. A `dev` foi sincronizada por fast-forward. As duas branches apontaram para o mesmo commit e a mesma árvore após a consolidação.

O [CI pré-merge](https://github.com/tccilda/painel-interativo/actions/runs/45788895677) e o [CI da main](https://github.com/tccilda/painel-interativo/actions/runs/45790380296) passaram em Ubuntu e Windows. No Windows local, 491 testes passaram em uma cópia limpa da versão consolidada, o índice público passou na verificação e as três rotas retornaram HTTP 200.

## Comparação com o repositório anterior

O repositório `tccilda/Painel` e o oficial `tccilda/painel-interativo` são distintos. A comparação de `tccilda/Painel/feat/painel-interativo` (`5ca86a4`) com a nova versão estável mostrou 17 arquivos com diferenças e históricos divergentes a partir de `a37d50c`. Os dados V5 versionados, a amostra estável, as dependências e o preparador coincidiam. O contraste de 55% dos pontos de carga × temperatura e a identidade provisória já constam da `main`.

As diferenças concentram-se na documentação e no código e testes de apresentação. A versão consolidada já incorpora as melhorias equivalentes do catálogo, dos cálculos e da interface, com correções adicionais da `dev`. O repositório anterior mantinha campos numéricos na grade por meio do Styler do Pandas. A versão estável usa texto para exibir os decimais localizados e N/D, o que afeta a ordenação. A conciliação desses comportamentos e a revisão de rótulos e escalas seguem no plano de acabamento do PR #1. Nenhum commit antigo foi identificado como necessário à consolidação imediata.

## Migração do Streamlit

A publicação atual usa `tccilda/Painel/feat/painel-interativo/streamlit_app.py`, conforme o link de código no [painel público](https://monitor-de-previsao-tcc.streamlit.app/). O topo dessa branch era `5ca86a4`. O commit executado deve ser confirmado nos logs administrativos durante a homologação.

1. Criar publicação paralela com subdomínio temporário, repositório `tccilda/painel-interativo`, branch `main`, entrada `streamlit_app.py` e Python 3.13. Conferir o commit `26bd008` no início da homologação.
2. Validar as três abas, amostra V5, retrospectiva de 2026 de 24 h e 48 h, referências, etiquetas N/D e exportações. Confirmar o acesso sem sessão autenticada quando a publicação for pública. Registrar o endereço temporário e o commit de homologação.
3. Após homologação, coordenar a troca do subdomínio em uma janela acordada. Se o endereço atual puder ser liberado e reassociado, renomear o app anterior para um endereço de contingência e atribuir o atual ao novo app. Confirmar a disponibilidade do nome antes da troca e verificar o acesso logo depois. Manter o URL temporário como alternativa caso a plataforma retenha o subdomínio ou a troca falhe. [Configuração oficial de subdomínios](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings#view-or-change-your-apps-url)

O Streamlit identifica a publicação pelas coordenadas do GitHub e exige uma nova implantação para trocar a origem. A migração aguarda a criação e a homologação do app paralelo pelo workspace autorizado. O repositório anterior e a publicação ativa foram preservados. [Orientações oficiais para trocar a origem](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)

## Cobertura pública em desenvolvimento

A branch `feat/amostra-publica` parte da `dev` sincronizada. O acervo integral V5 já está preparado em 88 partições locais. São 89 objetos contando o índice, com 71.681.193 bytes. Sua distribuição exige um destino HTTPS aprovado e a configuração do hash do índice no Streamlit. A alternativa desta branch usa somente previsões reais e amplia a cobertura para 1.420 emissões em 22 meses, com 51.120 passos e as 12 emissões originais do manifesto. Conferi todas as linhas da amostra contra o acervo e regenerei os 89 arquivos versionados com bytes idênticos. A [integração das versões](INTEGRACAO_VERSOES.md) registra a seleção e o procedimento de atualização.

A suíte completa da branch aprovou 491 testes no Windows em cópia limpa. O teste HTTP confirmou as três rotas. A integração com HTTPS simulado também foi exercitada para o caso em que o armazenamento oferece somente a V5.
