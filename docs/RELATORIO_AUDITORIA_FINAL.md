# Auditoria final do Monitor de Previsão

## Escopo verificado

A auditoria original registrou **134 requisitos** na [matriz](MATRIZ_REQUISITOS.md). Eram **129 dentro do escopo**, sendo 105 obrigatórios, 16 complementares e 8 condicionados aos dados. Dos cinco restantes, dois estavam fora do escopo do painel e três eram incompatíveis ou redundantes. A checklist original R001–R157 não estava disponível. A contagem usa a decomposição de todos os grupos do pedido de auditoria. A identidade provisória foi registrada posteriormente como D16.

A revisão consultou a monografia de 21 páginas, o inventário `RELATORIO_VERSOES_MODELOS.md`, os dois ZIPs disponíveis, seus manifestos, o código, a documentação e os testes. A monografia (§§1.2–1.6) pede delimitação territorial pela série efetiva, análise temporal e meteorológica, avaliação posterior ao treino com referências e discussão dos limites. Os capítulos de desenvolvimento, testes e resultados ainda aparecem como títulos. A entrega independente V5 tem o mesmo SHA-256 do membro V5 no pacote consolidado. A leitura não alterou os ZIPs.

## Estado das três abas

| Área | Implementação anterior | O que a auditoria entregou |
| --- | --- | --- |
| Explorador de Previsões | Filtros de t₀, horizonte, cenário, etapa e estimador na V5. Detalhe V1 disponível com o legado. Histórico, previsto, observado e referências. | Identificação das unidades na tabela, observado e sazonal semanal no leitor legado, contagem de calendário e MAE com denominador. A V5 oculta observações posteriores ao relógio da execução. A validação aparece no leitor quando existem emissões dessa etapa. |
| Avaliação de Desempenho e Erros | Agregados V1–V5, curva por passo, papéis dos estimadores e V4 × V5 por pares comuns. | Filtro de versão com cenários compatíveis, denominador do MAPE, transição 24/25 h, horizontes e referências lado a lado. Deltas relativos V4 × V5 usam o valor V4 nos pares comuns. Episódios consultáveis V1/V5, com recorte mensal, filtros no alvo e exportação. Resumo das mudanças técnicas recolhível. |
| Sazonalidade, Clima e Calendário | Perfis horário, semanal e mensal, carga × temperatura, resolução climática e inventário versionado. | Médias anuais com contagem de horas, extremos do perfil horário e seleção de categorias de calendário por tipo e âmbito. |
| Integridade e interface | Parquet mensal, cache, chaves de métrica e forma de distribuição compacta. | Validação de SHA-256 e contagem dos CSVs compactos durante o carregamento, mais domínio de passos e blocos. A navegação no topo e os detalhes recolhíveis foram preservados. |

A comparação entre horizontes é descritiva, com os denominadores de cada modelo e bloco. O teste dos dois modelos de 24 h e 48 h não prova equivalência entre o modelo de 24 h e o primeiro bloco de 48 h. O seletor de versão destaca um recorte, enquanto a visão de evolução reúne as versões elegíveis no cenário escolhido.

## Identidade provisória

O título do navegador e o cabeçalho usam **Monitor de Previsão**, com o subtítulo *Painel Interativo de Previsão de Demanda Energética* na interface. O grupo ainda definirá o título da monografia. As variáveis `ENERGY_FORECAST_*`, o caminho de cache `energy-forecast-versions` e o identificador de URL do plano de deploy foram preservados para compatibilidade.

Na revisão da identidade, os 466 testes passaram no Windows, inclusive em uma cópia limpa sem as bases privadas. O teste de inicialização retornou HTTP 200 nas três rotas. O navegador exibiu o novo nome, os títulos das três abas, os gráficos e a seleção de 48 h. A busca no conteúdo versionado não encontrou o nome de apresentação anterior.

Na rodada final, os filtros de emissão e as métricas mensais passaram a exibir MM/AAAA. As tabelas de pares comuns, disponibilidade e calendário usam rótulos em português e o inventário usa datas em DD/MM/AAAA, com vigência em horário de São Paulo. Os identificadores de origem e o conteúdo dos CSVs exportados conservaram o contrato existente. O idioma de menus nativos continua a cargo do Streamlit.

## Evidência de dados e desempenho

- A fonte consolidada histórica e os CSVs da V5 retornaram 540 linhas globais, 8.792 por passo, 8.832 por hora civil, 2.680 por mês civil e 778 registros de disponibilidade. Há 118 linhas no arquivo V4 × V5. As chaves de cada granularidade são únicas. A aba preserva a precisão dos agregados originais.
- A camada local tem 88 partições Parquet, 44 por horizonte. Foram conferidos SHA-256 e contagens. A leitura por partição confirmou 1.938.816 linhas de 24 h e 4.580.064 de 48 h com grade emissão–passo–alvo, horizonte completo e chave de passo sem duplicatas.
- Nos 6.518.880 registros, observado do alvo, persistência em t₀ e referência semanal no alvo menos 168 h coincidiram com a série auditada na tolerância de 10⁻⁸ MWmed. Os IDs da previsão resolveram no inventário do cenário e estavam no intervalo de vigência registrado para a emissão. Essa checagem usa o calendário entregue.
- Medição pontual local em partições grandes, após resolver o caminho, o hash e o estimador: 24 passos em 0,010 s e 48 passos em 0,007 s. Consultas dos episódios nos mesmos recortes retornaram 17.856 pares em 0,391 s e 35.712 pares em 0,063 s. A segunda consulta reutilizou cache de cenário. Essas são latências do serviço local, sem interface nem transferência remota.
- O leitor legado abriu as previsões V1. No teste de dezembro de 2025, o recorte mensal validado retornou 16.704 pares de 24 h e 33.408 de 48 h. A V5 é o padrão. A amostra pública contém 12 emissões de referência e 432 passos reais, com ambas as hipóteses, horizontes e as três etapas.

## Limites científicos e de produto

- O alvo é **ONS_SECO_piloto**, em MWmed, para o subsistema Sudeste/Centro-Oeste. Clima e calendário do Rio contextualizam a série regional. A linha de pesquisa municipal continua condicionada a medições municipais documentadas.
- A V1 tem carimbo original sem fuso confirmado. A V2–V5 conservam UTC e São Paulo como hipóteses. As previsões individuais V2–V4 e uma equivalência temporal documentada com V1 faltam para comparar curvas de previsão entre versões. A retrospectiva de 2026 usa snapshots fechados.
- A ausência de vazamento no treinamento exige dados, código e protocolo de treino e validação reproduzíveis. A verificação presente cobre os arquivos, a relação emissão–alvo, as referências de carga e os IDs conhecidos em t₀ na visão entregue. A validade jurídica dos atos e conclusões causais sobre clima/calendário ficam fora da verificação do aplicativo.
- Treinar o modelo dentro do Streamlit ou oferecer emissão operacional não faz parte da aplicação avaliada. Atribuir carga regional ao município, duplicar as métricas históricas ou gerar pares ausentes produziria resultados incompatíveis com a fonte.
- Alguns nomes técnicos preservam os identificadores da entrega. Elementos nativos do Streamlit podem usar o idioma do próprio framework.

## Execução e distribuição

O Windows executou Python 3.13.14. A suíte aprovou **466 testes** no ambiente local e **466** em uma cópia limpa da seleção do Git, com avisos de depreciação e sintaxe tratados como erros. `pip check` passou e o smoke HTTP registrou retorno 200 nas três rotas também na cópia limpa. No navegador, conferi as três abas e baixei o CSV de pares comuns. O CSV do teste de 2025, hipótese UTC, 24 h, continha 104.760 pares comuns e os deltas do estrato selecionado.

O verificador da seleção pública aprovou os 107 arquivos previstos para o Git. A busca por padrões usuais de credenciais na seleção textual não encontrou correspondências. Os ZIPs originais, os Parquets integrais e as bases privadas ficam fora da distribuição. A auditoria publicada no commit `e299e68` passou em Ubuntu e Windows no GitHub Actions. [Execução da auditoria publicada](https://github.com/tccilda/Painel/actions/runs/44896072344)

Para o Community Cloud, a demonstração usa `streamlit_app.py`, Python 3.13 e a amostra V5. O acervo completo existe localmente. O índice, as 88 partições e o legado somam 94.804.266 bytes. Os hashes e tamanhos das partições e o hash do ZIP legado foram conferidos. O teste da fonte HTTPS simula a consulta seletiva e a rejeição de conteúdo divergente. A verificação do serviço real requer o endpoint aprovado, as chaves de configuração e o acesso ao app com a branch e o commit identificados. [Roteiro de implantação](DEPLOY_STREAMLIT.md)

Na rodada final, **467 testes passaram no Windows**. A verificação incluiu a amostra distribuída, os rótulos de interface, as datas e a fonte HTTPS simulada. `pip check` passou e o teste de inicialização retornou HTTP 200 nas três rotas. A consulta à API do GitHub não retornou registros de implantação para a branch. Isso não determina o estado de um app no Community Cloud.

## Prontidão e pendências da rodada final

| Requisitos | Situação | Evidência ou dependência |
| --- | --- | --- |
| D01, D10 e D16 | Implementados no painel | Interface e documentação em português, identidade provisória, datas de apresentação e contratos técnicos preservados. |
| E02 | Validado para o recorte regional. Recorte municipal bloqueado | Para apresentar a pesquisa como municipal, o grupo deve obter série municipal comprovada e revisar a delimitação e a avaliação dos modelos. Se o alvo regional for adotado academicamente, a monografia deve refletir essa decisão. |
| E05, E06 e E09 | Hipóteses e etapas preservadas. Protocolo completo de treinamento pendente | Faltam a decisão documentada sobre o carimbo e o pipeline reproduzível com dados de entrada, janelas, transformações e regra de seleção. Checagens da entrega não certificam ausência de vazamento no treinamento. |
| F14 | Preparação verificada. Disponibilização integral externa pendente | Aprovar armazenamento e redistribuição, servir os 90 objetos por HTTPS, configurar URL e hash no app, testar emissões fora da amostra e registrar URL e SHA do app hospedado. |
| Correspondência R001–R157 | Bloqueada por falta da fonte | A busca no histórico, no projeto e nos anexos encontrou menções ao checklist. O inventário dos pacotes contém versões, métricas e dados, sem o checklist. Os 134 IDs são requisitos decompostos da auditoria, com D16 acrescentado posteriormente. |

**Pronto para demonstração acadêmica local do estudo regional**, com cobertura integral V1/V5 na instalação que dispõe do acervo e com cobertura amostral V5 em checkout limpo. **A defesa de conclusões municipais, a certificação do treino e a oferta integral em um endereço público permanecem pendentes.** A validação da apresentação deve identificar a abrangência regional e explicitar as hipóteses e a cobertura exibida.

## Arquivos da auditoria

- **Aplicação:** `app_pages/explorador.py`, `app_pages/sazonalidade.py`, `components/charts.py`, `components/model_versions_views.py`, `services/model_versions.py`, `services/pattern_service.py`.
- **Navegação e seleção de fonte:** `streamlit_app.py` e `components/sidebar.py` já continham ajustes locais no início da auditoria.
- **Testes:** `tests/test_app.py`, `tests/test_model_versions.py`, `tests/test_provided_app.py`.
- **Documentação:** `README.md`, `docs/INTEGRACAO_VERSOES.md`, `docs/MATRIZ_REQUISITOS.md`, `docs/RELATORIO_AUDITORIA_FINAL.md`.
