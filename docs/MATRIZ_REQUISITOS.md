# Matriz de requisitos do Monitor de Previsão

A checklist numerada R001–R157 não foi localizada nas referências do projeto, no histórico Git disponível, nos anexos pesquisados por número ou título, nem no inventário dos pacotes de modelos. Os 134 IDs da auditoria original correspondem à decomposição do pedido de auditoria. O item D16 acompanha a identidade provisória. A correspondência com o checklist original depende do texto ou arquivo fonte dos 157 itens. A situação inicial inclui os ajustes locais de navegação e limpeza visual feitos antes da auditoria.

A monografia disponível (21 páginas, §§1.2–1.6) orienta a leitura dos requisitos. Ela pede delimitação da variável-alvo e da resolução, análise temporal e das associações, construção das entradas e avaliação posterior ao treino com referência simples. A interface comprova os requisitos de visualização e análise indicados na matriz. Os capítulos de desenvolvimento, testes, resultados e conclusão ainda aparecem como títulos nas páginas 17–20 e o protocolo de treinamento completo não acompanha esta entrega.

**Classificação** · O = obrigatório. CP = complementar pertinente. C = condicionado aos dados. F = fora do escopo. I = incompatível ou redundante. **Situação** · OK = implementado com evidência de validação no recorte indicado. N/A = não aplicável.

**Evidências de verificação** · V = AppTests e testes do catálogo em `tests/test_model_versions.py` e `tests/test_app.py`. G = testes existentes de gráficos, apresentação, contratos, histórico, análise e métricas. S = AppTests de sazonalidade e testes de padrões. P = leitura seletiva e conferência das partições reais. D = inspeção de monografia, inventário, manifestos e documentação. U = AppTests dos controles, tabelas e gráficos serializados. T = suíte, dependências, inicialização HTTP, CI e verificação de distribuição. O [relatório final](RELATORIO_AUDITORIA_FINAL.md) registra os resultados e as verificações ainda pendentes.

| ID | Requisito | Origem | Classificação de escopo | Situação inicial | Evidência no código/dados | Ação necessária | Situação final | Teste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A01 | Seleção V1–V5 e V5 padrão | Pedido §3.A | C | Parcial | render_explorer e manifestos | V1 depende do ZIP. V2–V4 aparecem na avaliação | Parcial | V |
| A02 | Horizonte 24 h e 48 h | Pedido §3.A | O | OK | render_explorer, _render_legacy | Preservado | OK | V |
| A03 | Etapa de avaliação | Pedido §3.A | O | Parcial | STAGES e _render_legacy | Disponibilizar validação no leitor quando houver detalhe | OK | V |
| A04 | Data e hora de emissão | Pedido §3.A | O | OK | _render_v5, forecast_picker | Preservado | OK | V |
| A05 | Hipótese de horário | Pedido §3.A | O | OK | SCENARIOS e _render_v5 | Preservadas duas hipóteses e o carimbo legado | OK | V |
| A06 | Identidade do estimador | Pedido §3.A | O | OK | issues_for_models e forecast_details | Preservado | OK | V |
| A07 | Histórico de 48, 72, 120 ou 168 h | Pedido §3.A | O | OK | _render_forecast e explorer_frame | Preservado | OK | V |
| A08 | Opções encadeadas válidas | Pedido §3.A | O | OK | detail_index, forecast_picker | Preservado | OK | V |
| A09 | Curva de carga histórica | Pedido §3.A | O | OK | explorer_chart | Preservada | OK | V |
| A10 | Curva prevista até 24 ou 48 passos | Pedido §3.A | O | OK | forecast_detail, explorer_chart | Preservada | OK | V, P |
| A11 | Carga real sobreposta | Pedido §3.A | C | Parcial | _render_forecast, prepare_evaluation | Ocultar observação posterior ao relógio | OK | V, P |
| A12 | Referência sazonal semanal | Pedido §3.A | O | OK | explorer_chart, V5 y_baseline_semanal | Preservada | OK | P |
| A13 | Marcador da emissão no gráfico | Pedido §3.A | O | OK | _mark_issuance | Preservado | OK | G |
| A14 | Legenda, zoom, hover e navegação | Pedido §3.A | O | OK | explorer_chart e Streamlit/Plotly | Preservados | OK | G |
| A15 | Unidades, datas e horários | Pedido §3.A | O | Parcial | _render_forecast | Traduzir colunas e explicitar MWmed | OK | V |
| A16 | Pico de carga previsto | Pedido §3.A | O | OK | _render_forecast, forecast_summary | Preservado | OK | V, G |
| A17 | Data e hora do pico | Pedido §3.A | O | OK | _render_forecast, forecast_summary | Preservadas | OK | V |
| A18 | Temperatura observada em t₀ | Pedido §3.A | C | OK | temperature_at_issue | Preservar defasagem de até 1 h | OK | G |
| A19 | MAE da emissão | Pedido §3.A | C | Parcial | _render_forecast, calculate_metrics | N/D e contagem quando faltam observações | OK | V, G |
| A20 | Classificação horária de calendário | Pedido §3.A | O | OK | classify, Valores horários e calendário | Preservados flags e IDs | OK | V, P |
| A21 | Resumo de categorias do horizonte | Pedido §3.A | O | Ausente na V5 | _render_forecast | Adicionar contagem por categoria recolhível | OK | V |
| A22 | Tabela horária observada, prevista e referências | Pedido §3.A | O | Parcial | _render_forecast e _render_legacy | Adicionar observado e referência semanal à tabela legada. Rotular referências V5 | OK | V |
| A23 | Exportação do recorte em CSV | Pedido §3.A | C | OK | csv_bytes e export_forecast_csv | Preservar metadados e precisão | OK | V |
| A24 | Datas, versões e emissões indisponíveis | Pedido §3.A | O | OK | render_explorer, _render_v5, forecast_picker | Estados vazios e ajuda recolhível | OK | V |
| A25 | Comparação de curvas de previsões entre versões | Pedido §3.A | C | Bloqueado | Pacote legado e inventário V1–V5 | Aguardar pares horários de versões com relógios verificáveis | Bloqueado | D |
| B01 | Filtro de versão | Pedido §3.B | O | Ausente no catálogo | render_evolution | Adicionar versão e filtrar cenários compatíveis | OK | V |
| B02 | Filtro de horizonte | Pedido §3.B | O | OK | render_evolution | Preservado | OK | V |
| B03 | Filtro de etapa | Pedido §3.B | O | OK | render_evolution e STAGES | Preservado | OK | V |
| B04 | Filtro de hipótese | Pedido §3.B | O | OK | render_evolution e SCENARIOS | Preservar carimbo V1 isolado | OK | V |
| B05 | Seleção de MAE, RMSE e MAPE | Pedido §3.B | O | OK | render_evolution, _step_chart | Preservada | OK | V, G |
| B06 | Seleção dos três blocos | Pedido §3.B | O | OK | render_evolution | Preservado horizonte independente | OK | V |
| B07 | Indicadores globais | Pedido §3.B | O | OK | metric_tables, render_evolution | Preservados na tabela | OK | V |
| B08 | Comparação 24 h e 48 h | Pedido §3.B | O | Parcial | _horizon_summary | Exibir lado a lado com denominadores independentes | OK descritivo | V |
| B09 | Persistência e sazonal semanal | Pedido §3.B | O | Parcial | _horizon_summary | Exibir referências dos dois horizontes na mesma seleção | OK | V |
| B10 | Selecionados, alternativas e pilotos | Pedido §3.B | O | OK | metric_tables e render_evolution | Preservar separação | OK | V |
| B11 | Quantidades de pares válidos | Pedido §3.B | O | Parcial | render_evolution | Adicionar denominador do MAPE | OK | V |
| B12 | Períodos e critérios da avaliação | Pedido §3.B | O | Parcial | STAGES e detalhes metodológicos | Explicitar semestres e natureza retrospectiva | OK | V, D |
| B13 | Gráfico de evolução V1–V5 | Pedido §3.B | O | OK | render_evolution | Preservar pontos e recortes | OK | V |
| B14 | Tabela histórica consolidada | Pedido §3.B | O | OK | metric_tables | Preservar fonte única por versão | OK | V, D |
| B15 | Variações absolutas e percentuais | Pedido §3.B | CP | Parcial | _paired_section | Calcular deltas relativos de MAE/RMSE sobre V4 em pares comuns | OK | V |
| B16 | Comparação pareada V4 × V5 | Pedido §3.B | O | OK | comparacao_v4_v5_pares_comuns.csv | Preservar fonte fornecida | OK | V, D |
| B17 | Pares comuns, exclusões e denominadores | Pedido §3.B | O | OK | _paired_section | Preservar campos originais | OK | V |
| B18 | Erro por passo | Pedido §3.B | O | OK | _step_chart | Preservar passos e lacunas | OK | V |
| B19 | Divisão entre passos 24 e 25 | Pedido §3.B | CP | Ausente no catálogo | _step_chart | Marcar 24,5 no gráfico completo de 48 h | OK | V |
| B20 | Curvas de erro de versões compatíveis | Pedido §3.B | O | OK | _step_chart, métricas por passo | Preservar caráter descritivo e os mesmos filtros | OK | V |
| B21 | Filtro por mês | Pedido §3.B | O | Ausente no catálogo | _episode_section | Filtrar mês civil da emissão em uma partição | OK | V, P |
| B22 | Filtro por dia da semana | Pedido §3.B | O | Ausente no catálogo | _episode_section, largest_errors | Aplicar dia civil do alvo | OK | V, G |
| B23 | Filtro por calendário | Pedido §3.B | O | Ausente no catálogo | _episode_section, largest_errors | Filtrar categoria do alvo conhecida em t₀ na V5 | OK | V, G |
| B24 | Filtro por temperatura | Pedido §3.B | C | Ausente no catálogo | _episode_section e episode_rows | Usar temperatura observada no alvo como contexto | OK | V, G |
| B25 | Episódios com maiores erros | Pedido §3.B | C | Ausente no catálogo | episode_rows e legacy_episode_rows | Ordenar até 30 pares verificados no mês da emissão | OK onde há detalhe | V, P |
| B26 | Ordenação da tabela | Pedido §3.B | CP | Parcial | data_table, largest_errors | Ordenar por erro na origem e manter ordenação do grid | OK | V |
| B27 | Exportação de resultados filtrados | Pedido §3.B | CP | Ausente no catálogo | csv_bytes, render_evolution | Oferecer métricas, pares comuns e episódios | OK | V |
| B28 | Lacunas como N/D | Pedido §3.B | O | OK | data_table, _step_chart | Preservar ausências | OK | V |
| B29 | Histórico técnico das versões | Pedido §3.B | CP | Parcial | inventário e render_evolution | Resumo recolhível na interface | OK | V, D |
| C01 | Seleção de anos e períodos 2024–2026 | Pedido §3.C | O | OK | _render_profiles, region_history | Preservada | OK | S |
| C02 | Perfil médio horário | Pedido §3.C | O | OK | daily_profile, daily_pattern_chart | Preservado | OK | S |
| C03 | Perfil médio semanal | Pedido §3.C | O | OK | weekly_profile, weekly_pattern_chart | Preservado | OK | S |
| C04 | Evolução mensal | Pedido §3.C | O | OK | monthly_profile, monthly_chart | Preservada sem preencher lacunas | OK | S |
| C05 | Evolução anual | Pedido §3.C | O | Ausente | annual_profile, annual_chart | Adicionar médias das horas disponíveis e contagens | OK | S |
| C06 | Comparação entre períodos ou anos | Pedido §3.C | CP | Parcial | _render_profiles, annual_chart | Comparar anos selecionados no mesmo gráfico | OK | S |
| C07 | Horas de maior e menor carga média | Pedido §3.C | CP | Parcial | daily_pattern_chart | Identificar extremos no perfil horário | OK | S |
| C08 | Dispersão carga × temperatura | Pedido §3.C | O | OK | join_weather, temperature_scatter | Preservada | OK | S |
| C09 | Séries temporais de carga e temperatura | Pedido §3.C | O | OK | load_temperature_chart | Preservadas | OK | S |
| C10 | Filtro por estação | Pedido §3.C | O | OK | render_seasonality | Preservar A621, A601 e média disponível | OK | S |
| C11 | Temperatura média com fundamento | Pedido §3.C | O | OK | join_weather | Preservar média por instante e contagem | OK | S |
| C12 | Unidades °C e MWmed | Pedido §3.C | O | OK | temperature_scatter e load_temperature_chart | Preservadas | OK | S |
| C13 | Agregação diária e semanal | Pedido §3.C | CP | OK | aggregate_load_temperature | Preservada | OK | S |
| C14 | Interatividade, zoom e hover | Pedido §3.C | CP | OK | components/charts.py | Preservados | OK | G, S |
| C15 | Perfis de dias úteis, fins de semana e feriados | Pedido §3.C | O | OK | calendar_profile_chart | Preservados | OK | S |
| C16 | Âmbitos nacional, estadual e municipal | Pedido §3.C | O | OK | classify, SCOPE_LABELS | Preservar âmbito da fonte e âmbito administrativo federal | OK | S, D |
| C17 | Pontos facultativos | Pedido §3.C | O | OK | classify e calendar_profile | Preservados | OK | S |
| C18 | Filtro de categorias de calendário | Pedido §3.C | CP | Ausente | _render_profiles | Adicionar seleção por tipo e âmbito | OK | S |
| C19 | Sobreposição de eventos | Pedido §3.C | O | OK | classify, IDs de calendário | Preservar prioridade e inventário | OK | S, P |
| C20 | Eventos pendentes | Pedido §3.C | O | OK | render_seasonality, eventos_pendentes_v5.csv | Preservar separados das classificações | OK | S |
| C21 | Períodos incompletos | Pedido §3.C | O | OK | filter_history e contagens de perfil | Manter horas disponíveis, sem extrapolar | OK | S |
| C22 | Associação observacional | Pedido §3.C | O | OK | detalhes metodológicos | Preservar interpretação descritiva | OK | S, D |
| D01 | Interface em português brasileiro | Pedido §3.D | O | Parcial | Views, títulos do app e rótulos das tabelas | Traduzir colunas, legendas e controles sob domínio do painel. Preservar IDs da fonte | Validado nas superfícies do painel. Idioma dos controles nativos depende do Streamlit | U, V |
| D02 | Exatamente três abas | Pedido §3.D | O | OK | streamlit_app.py | Preservar navegação no topo | OK | U |
| D03 | Layout amplo | Pedido §3.D | CP | OK | streamlit_app.py | Preservado | OK | U |
| D04 | Identidade visual consistente | Pedido §3.D | CP | OK | .streamlit/config.toml e charts | Preservada | OK | U |
| D05 | Filtros compactos | Pedido §3.D | CP | OK | streams por colunas | Manter filtros adicionais em seções recolhíveis | OK | U |
| D06 | Cartões e métricas legíveis | Pedido §3.D | O | OK | metric_cards, data_table | Preservados | OK | U |
| D07 | Gráficos responsivos | Pedido §3.D | O | OK | st.plotly_chart width stretch | Preservados | OK | U, G |
| D08 | Unidades visíveis | Pedido §3.D | O | Parcial | _render_forecast, tabelas | Identificar MWmed e °C nas novas tabelas e gráficos | OK | V, S |
| D09 | Legendas e tooltips | Pedido §3.D | CP | OK | components/charts.py | Preservar unidade, séries e horário | OK | G |
| D10 | Números e datas em formato brasileiro | Pedido §3.D | O | Parcial | data_table, format_timestamp, month_choice | Aplicar MM/AAAA nos filtros e na tabela mensal, DD/MM/AAAA no inventário e manter chaves originais nas exportações | Validado nas superfícies do painel | G, U, V |
| D11 | Estados vazios claros | Pedido §3.D | O | OK | render_evolution, _episode_section, _render_profiles | Mensagens nos recortes sem dados | OK | V, S |
| D12 | Metodologia recolhível | Pedido §3.D | O | OK | expanders nas três abas | Preservada | OK | U |
| D13 | Poluição visual baixa | Pedido §3.D | CP | OK | estrutura das abas | Manter descrições e diagnósticos recolhidos | OK | U |
| D14 | Textos redundantes | Pedido §3.D | I | OK | mudança local anterior ao início da auditoria | Preservar remoção das legendas explicativas soltas | OK | U |
| D15 | Cores e espaçamento | Pedido §3.D | CP | OK | config.toml, charts e CSS | Preservados | OK | U |
| D16 | Nome provisório e subtítulo consistentes | Padronização da identidade | O | Parcial | `APP_NAME` e `APP_SUBTITLE` em `streamlit_app.py` | Alinhar títulos, cabeçalho, navegação, README e guias | OK | AppTest, navegação no navegador e inspeção das referências versionadas |
| E01 | Proveniência da série e dos resultados | Pedido §3.E | O | OK | manifestos e inventário | Preservar identificação | OK | D |
| E02 | Alvo territorial de carga | Pedido §3.E | O | OK | TARGET, monografia §§1.2 e 1.5 | Identificar ONS SE/CO. Aguardar decisão acadêmica sobre o alvo e série municipal comprovada caso o grupo mantenha esse objetivo | Validado para ONS SE/CO. Escopo municipal bloqueado por dados | D |
| E03 | Unidade de medida | Pedido §3.E | O | OK | check_identity e contratos | Verificar MWmed no manifesto e nos agregados | OK | V, D |
| E04 | Carimbos e emissão | Pedido §3.E | O | OK | forecast_detail, contratos | Verificar emissão, passo e alvo | OK | V, P |
| E05 | Fusos e hipóteses | Pedido §3.E | O | OK | SCENARIOS, INSTRUCOES_PAINEL_v5.md | Manter UTC e São Paulo como hipóteses | OK na interface, fuso oficial em aberto | V, D |
| E06 | Separação treino, validação, teste e retrospectiva | Pedido §3.E | O | Parcial | STAGES e manifesto V5 | Distinguir etapas rotuladas na entrega. Solicitar código, dados de entrada e protocolo reproduzível para auditar sua criação | Etapas do painel validadas. Separação do treino bloqueada por evidência ausente | V, D |
| E07 | Grade de passos | Pedido §3.E | O | OK | build_horizon, forecast_detail | Validar limite de passos também nos agregados | OK | V, P |
| E08 | Observados válidos para o erro | Pedido §3.E | O | Parcial | episode_rows, _render_forecast | Conferir série auditada nos episódios e ocultar alvos futuros | OK | V, P |
| E09 | Ausência de vazamento temporal | Pedido §3.E | O | Bloqueado | Monografia §§1.6, manifesto V5 e auditoria das partições | Verificar origem, alvo, referências e vigência no painel. Auditar ajustes, atributos e partições no pipeline de treino quando entregue | Checagens da entrega validadas. Ausência de vazamento no treino não demonstrada | D, P |
| E10 | Valores ausentes | Pedido §3.E | O | OK | data_table, history_service, largest_errors | Preservar lacunas e pares válidos | OK | G, V |
| E11 | Checksums e manifestos | Pedido §3.E | O | Parcial | _checked_csv, partition_path, prepare_model_versions | Verificar compactos, partições e contagens | OK para os artefatos usados | V, D, P |
| E12 | Duplicatas de métricas | Pedido §3.E | O | OK | metric_tables | Chave única por granularidade | OK | V |
| E13 | Duplicatas de previsões | Pedido §3.E | O | OK | build_horizon, forecast_detail | Verificar chaves e grade na preparação e recortes | OK | P |
| E14 | MAE, RMSE e MAPE | Pedido §3.E | O | OK | metrics_service e agregados com checksum | Preservar valores fornecidos. Testar cálculo local e denominadores | OK para o painel | G, V |
| E15 | Amostras comparáveis | Pedido §3.E | O | OK | pares comuns V4 × V5, _horizon_summary | Distinguir descritivo de pareado | OK | V, D |
| E16 | Estimadores selecionados | Pedido §3.E | O | OK | eh_selecionado, metric_tables | Preservar flag sem inferir pelo nome | OK | V |
| E17 | Séries observadas e previstas | Pedido §3.E | O | OK | explorer_chart e cabeçalhos da tabela | Manter séries e unidades distintas | OK | V, G |
| E18 | Eventos conhecidos na emissão | Pedido §3.E | O | OK | classify e manifesto | Usar flags/IDs da previsão e validar vigência em lote | OK para o pacote, atos não auditados externamente | P, D |
| E19 | Retrospectiva de 2026 | Pedido §3.E | O | OK | STAGES, manifesto e detalhes | Preservar classificação de replay | OK | V, D |
| E20 | Treinamento do modelo no painel | Pedido §3.E | F | N/A | Monografia §1.4.2 e entrega de resultados | Treino pertence à frente de modelagem | N/A | D |
| E21 | Previsão operacional em tempo real | Pedido §3.E | F | N/A | Manifesto V5 | O pacote é retrospectivo | N/A | D |
| E22 | Atribuir carga regional ao município | Pedido §3.E | I | N/A | TARGET e contrato geográfico | Preservar rótulo regional | N/A | D |
| E23 | Fabricar curvas ou pareamento histórico | Pedido §3.E | I | N/A | Inventário e manifesto | V2–V4 ficam com agregados. V1 tem carimbo distinto | N/A | D |
| F01 | Carregar V1–V5 | Pedido §3.F | O | OK | metric_tables, legacy_bundle, forecast_detail | Conferir V1 legado e as cinco versões nos agregados | OK | V, P |
| F02 | Esquemas, colunas e tipos | Pedido §3.F | O | Parcial | _manifest, metric_tables e build_horizon | Checar manifesto, contagens e domínio de passos/blocos | OK para o pacote testado | V, P |
| F03 | Uma fonte por chave | Pedido §3.F | O | OK | metric_tables e BASE_KEY | Usar consolidado V1–V4 e V5 separado | OK | V |
| F04 | Evitar carregar CSVs gigantes em execução | Pedido §3.F | O | OK | prepare_model_versions, partition_path | Manter colunas e filtros em Parquet | OK | P |
| F05 | Cache dos agregados | Pedido §3.F | O | OK | metric_tables | Preservado | OK | V |
| F06 | Consulta seletiva por emissão | Pedido §3.F | O | OK | forecast_detail | Preservada. Episódios limitados por mês, bloco e modelo | OK | P |
| F07 | Partições eficientes | Pedido §3.F | O | OK | prepare_model_versions, index.json | Preservadas | OK | P |
| F08 | Originais e checksums preservados | Pedido §3.F | O | OK | ZIPs de entrada e camada derivada | Ler originais sem escrever | OK | D, P |
| F09 | Apresentação separada dos dados | Pedido §3.F | O | OK | services e components | Adicionar junções no serviço e controles na interface | OK | V, S |
| F10 | Caminhos multiplataforma | Pedido §3.F | O | OK | pathlib, workflow tests.yml | Preservar | OK no Windows, Linux via CI | T |
| F11 | Dependências consistentes | Pedido §3.F | O | OK | requirements.txt, requirements-dev.txt | Sem novas dependências | OK | T |
| F12 | Execução Windows | Pedido §3.F | O | OK | setup_local.bat, run_local.bat, smoke_startup.py | Confirmar suíte e inicialização | OK | T |
| F13 | Instalação e inicialização local | Pedido §3.F | O | OK | scripts e docs/EXECUCAO_LOCAL_WINDOWS.md | Preservar scripts | OK | T |
| F14 | Preparação Streamlit Community Cloud | Pedido §3.F | O | Parcial | docs/DEPLOY_STREAMLIT.md, INTEGRACAO_VERSOES.md e índice completo | Validar amostra em cópia limpa e caminho HTTPS simulado. Obter armazenamento autorizado, configurar URL e SHA-256, confirmar app e commit hospedado | Preparação e leitura seletiva validadas. Endpoint real e acervo integral na nuvem dependem do grupo | T, V, P |
| F15 | Mesma base de código local/nuvem | Pedido §3.F | O | OK | streamlit_app.py e configuração por ambiente | Preservado | OK | T |
| F16 | Dados gigantes fora do Git | Pedido §3.F | O | OK | .gitignore, check_public_bundle.py | Verificar pacote versionado | OK | T |
| F17 | Credenciais e arquivos sensíveis | Pedido §3.F | O | OK | check_public_bundle.py | Verificar seleção de arquivos | OK estrutural | T |
| F18 | README e documentação técnica | Pedido §3.F | O | Parcial | README e docs | Atualizar procedimentos, matriz e relatório | OK | D |
| F19 | Testes automatizados | Pedido §3.F | O | OK | tests/, smoke_startup.py | Adicionar regressões e executar suíte | OK | T |
| F20 | Integração segura ao Git compartilhado | Pedido §3.F | O | Parcial | feat/painel-interativo e histórico do GitHub | Preservar o histórico e manter as correções na branch de trabalho | Validado na auditoria publicada, com CI em Ubuntu e Windows. Esta rodada segue o mesmo recorte de branch | T |
