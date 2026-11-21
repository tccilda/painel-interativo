# Dicionário de dados — ONS SE/CO v5

Identidade em todos os arquivos modelados: `alvo_id=ONS_SECO_piloto`, `unidade=MWmed`, `versao=v5`, `escopo_avaliacao=retrospectiva_nao_cego`. Carga, erros absolutos e viés usam MWmed. Temperaturas `*_c` usam °C. Erros relativos `*_pct` são porcentagens, e deltas `*_pp` são pontos percentuais. Decimais voltam a float64 sem arredondamento editorial.

A `hipotese_UTC` localiza o carimbo original como UTC. A `hipotese_Sao_Paulo` o localiza em `America/Sao_Paulo`. Ambas convertem seus próprios instantes para UTC. As duas hipóteses têm igual estatuto. Evidência oficial CON-01, Dicionário de Dados ONS v1.2 e CKAN, deixa fuso e borda de `din_instante` em aberto, com UTC no portal referente ao catálogo. A hora civil do calendário é America/Sao_Paulo em ambos os cenários. O modelo usa snapshots fechados, `posicao="inicio"`, lag 0 e `atraso_horas=0`. O atraso e a posição reais do intervalo não foram verificados. CON-02 permanece adiado.

## Esquema comum

UTF-8, separado por vírgula, decimal com ponto, cabeçalho único, flags inteiras 0/1 e nulo escrito como campo vazio. As sete primeiras colunas na ordem são `alvo_id, unidade, cenario, modelo, versao, etapa, escopo_avaliacao`, texto obrigatório. `K=(alvo_id,versao,cenario,etapa,modelo)`. Registros de contexto usam as etapas `base_integrada` e `calendario` e os modelos `serie_horaria` e `calendario_eventos`. Instantes canônicos são textos ISO 8601 UTC `AAAA-MM-DDTHH:MM:SSZ`. Rótulos `*_ons_raw` são textos literais ONS `AAAA-MM-DD HH:MM:SS`. Data e mês civis usam `AAAA-MM-DD` e `AAAA-MM`.

## Arquivos, ordem adicional das colunas e chaves

### `previsoes_24h_v5.csv`

Uma previsão física por chave. 1.938.816 linhas, 24 passos completos por emissão e modelo. Chave `(K,horizonte_h,origem_t,passo_h)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `origem_t` | instante UTC | Obrigatório |
| `instante_alvo` | instante UTC | Obrigatório |
| `origem_ons_raw` | texto | Obrigatório |
| `alvo_ons_raw` | texto | Obrigatório |
| `horizonte_h` | int64 | Obrigatório |
| `passo_h` | int64 | Obrigatório |
| `n_atributos` | int64 | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `y_real` | float64 | Obrigatório |
| `y_pred` | float64 | Obrigatório |
| `y_baseline_semanal` | float64 | Obrigatório |
| `y_baseline_persistencia` | float64 | Obrigatório |
| `erro_abs` | float64 | Obrigatório |
| `erro_pct` | float64 | Sim |
| `fim_de_semana` | int64 (0/1) | Obrigatório |
| `eh_feriado` | int64 (0/1) | Obrigatório |
| `eh_ponto_facultativo` | int64 (0/1) | Obrigatório |
| `evento_versao_ids` | array JSON em texto | Obrigatório |

### `previsoes_48h_v5.csv`

Uma previsão física por chave. 4.580.064 linhas, 48 passos completos por emissão e modelo. Chave `(K,horizonte_h,origem_t,passo_h)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `origem_t` | instante UTC | Obrigatório |
| `instante_alvo` | instante UTC | Obrigatório |
| `origem_ons_raw` | texto | Obrigatório |
| `alvo_ons_raw` | texto | Obrigatório |
| `horizonte_h` | int64 | Obrigatório |
| `passo_h` | int64 | Obrigatório |
| `n_atributos` | int64 | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `y_real` | float64 | Obrigatório |
| `y_pred` | float64 | Obrigatório |
| `y_baseline_semanal` | float64 | Obrigatório |
| `y_baseline_persistencia` | float64 | Obrigatório |
| `erro_abs` | float64 | Obrigatório |
| `erro_pct` | float64 | Sim |
| `fim_de_semana` | int64 (0/1) | Obrigatório |
| `eh_feriado` | int64 (0/1) | Obrigatório |
| `eh_ponto_facultativo` | int64 (0/1) | Obrigatório |
| `evento_versao_ids` | array JSON em texto | Obrigatório |

### `serie_horaria_auditada_v5.csv`

Uma observação por chave. 24.837 h em cada cenário. Série contínua de 2024-01-01T03:00:00Z a 2026-10-31T23:00:00Z. Chave `(K,instante)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `instante` | instante UTC | Obrigatório |
| `instante_ons_raw` | texto | Obrigatório |
| `carga_mwmed` | float64 | Obrigatório |
| `temp_a621_c` | float64 | Sim |
| `temp_a601_c` | float64 | Sim |
| `temp_rj_c` | float64 | Obrigatório |
| `fonte_temp` | texto | Obrigatório |
| `ano` | int64 | Obrigatório |
| `mes` | int64 | Obrigatório |
| `dia_mes` | int64 | Obrigatório |
| `hora` | int64 | Obrigatório |
| `dia_semana` | int64 | Obrigatório |
| `dia_ano` | int64 | Obrigatório |
| `fim_de_semana` | int64 (0/1) | Obrigatório |
| `eh_feriado` | int64 (0/1) | Obrigatório |
| `eh_ponto_facultativo` | int64 (0/1) | Obrigatório |
| `origem_calendario_t` | instante UTC | Obrigatório |
| `evento_versao_ids` | array JSON em texto | Obrigatório |

### `eventos_calendario_v5.csv`

68 versões do inventário em cada cenário. Datas locais civis e vigência conhecida conforme o ato/hipótese registrada. Chave `(K,evento_versao_id)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `evento_versao_id` | texto | Obrigatório |
| `data_local` | texto | Obrigatório |
| `nome_evento` | texto | Obrigatório |
| `tipo_evento` | texto | Obrigatório |
| `esfera` | texto | Obrigatório |
| `territorio_abrangencia` | texto | Obrigatório |
| `alcance` | texto | Obrigatório |
| `horario_ou_duracao` | texto | Obrigatório |
| `ato` | texto | Obrigatório |
| `fonte_url` | texto | Obrigatório |
| `conhecido_desde_status` | texto | Obrigatório |
| `nota` | texto | Obrigatório |
| `eh_feriado` | int64 (0/1) | Obrigatório |
| `eh_ponto_facultativo` | int64 (0/1) | Obrigatório |
| `publicado_em_data` | texto | Obrigatório |
| `conhecido_desde` | instante UTC | Obrigatório |
| `conhecido_ate` | instante UTC | Sim |

### `comparacao_v4_v5_pares_comuns.csv`

Uma comparação de dois estimadores por bloco e identidade, apenas na interseção de pares. Chave `(K,horizonte_h,bloco_horas,versao_ref,modelo_ref,tipo_comparacao)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `horizonte_h` | int64 | Obrigatório |
| `bloco_horas` | texto | Obrigatório |
| `versao_ref` | texto | Obrigatório |
| `modelo_ref` | texto | Obrigatório |
| `tipo_comparacao` | texto | Obrigatório |
| `n_pares_v4` | int64 | Obrigatório |
| `n_pares_v5` | int64 | Obrigatório |
| `n_pares_comuns` | int64 | Obrigatório |
| `n_origens_comuns` | int64 | Obrigatório |
| `n_alvos_unicos_comuns` | int64 | Obrigatório |
| `n_excluidos_v4` | int64 | Obrigatório |
| `n_excluidos_v5` | int64 | Obrigatório |
| `n_mape_validos_comuns` | int64 | Obrigatório |
| `mae_mwmed_v4` | float64 | Obrigatório |
| `rmse_mwmed_v4` | float64 | Obrigatório |
| `mape_pct_v4` | float64 | Obrigatório |
| `mae_mwmed_v5` | float64 | Obrigatório |
| `rmse_mwmed_v5` | float64 | Obrigatório |
| `mape_pct_v5` | float64 | Obrigatório |
| `delta_mae_mwmed` | float64 | Obrigatório |
| `delta_rmse_mwmed` | float64 | Obrigatório |
| `delta_mape_pp` | float64 | Obrigatório |

### `metricas_globais_v5.csv`

Uma métrica por cenário, etapa, modelo, horizonte e bloco. Chave `(K,horizonte_h,bloco_horas)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `horizonte_h` | int64 | Obrigatório |
| `bloco_horas` | texto | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `n_origens` | int64 | Obrigatório |
| `n_pares` | int64 | Obrigatório |
| `n_alvos_unicos` | int64 | Obrigatório |
| `n_mape_validos` | int64 | Obrigatório |
| `fator_sobreposicao` | float64 | Obrigatório |
| `mae_mwmed` | float64 | Obrigatório |
| `rmse_mwmed` | float64 | Obrigatório |
| `mape_pct` | float64 | Sim |
| `erro_medio_mwmed` | float64 | Obrigatório |

### `metricas_por_passo_v5.csv`

Uma métrica por cenário, etapa, modelo, horizonte e passo de antecedência. Chave `(K,horizonte_h,passo_h)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `horizonte_h` | int64 | Obrigatório |
| `passo_h` | int64 | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `n_origens` | int64 | Obrigatório |
| `n_pares` | int64 | Obrigatório |
| `n_alvos_unicos` | int64 | Obrigatório |
| `n_mape_validos` | int64 | Obrigatório |
| `fator_sobreposicao` | float64 | Obrigatório |
| `mae_mwmed` | float64 | Obrigatório |
| `rmse_mwmed` | float64 | Obrigatório |
| `mape_pct` | float64 | Sim |
| `erro_medio_mwmed` | float64 | Obrigatório |

### `metricas_por_hora_v5.csv`

Uma métrica por cenário, etapa, modelo, horizonte, bloco e hora civil do alvo. Chave `(K,horizonte_h,bloco_horas,hora_alvo_local)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `horizonte_h` | int64 | Obrigatório |
| `bloco_horas` | texto | Obrigatório |
| `hora_alvo_local` | int64 | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `n_origens` | int64 | Obrigatório |
| `n_pares` | int64 | Obrigatório |
| `n_alvos_unicos` | int64 | Obrigatório |
| `n_mape_validos` | int64 | Obrigatório |
| `fator_sobreposicao` | float64 | Obrigatório |
| `mae_mwmed` | float64 | Obrigatório |
| `rmse_mwmed` | float64 | Obrigatório |
| `mape_pct` | float64 | Sim |
| `erro_medio_mwmed` | float64 | Obrigatório |

### `metricas_por_mes_v5.csv`

Uma métrica por cenário, etapa, modelo, horizonte, bloco e mês civil do alvo. Chave `(K,horizonte_h,bloco_horas,mes_alvo_local)`.

| Campo adicional na ordem | Tipo lógico | Nulo |
|---|---|---|
| `horizonte_h` | int64 | Obrigatório |
| `bloco_horas` | texto | Obrigatório |
| `mes_alvo_local` | texto | Obrigatório |
| `eh_selecionado` | int64 (0/1) | Obrigatório |
| `n_origens` | int64 | Obrigatório |
| `n_pares` | int64 | Obrigatório |
| `n_alvos_unicos` | int64 | Obrigatório |
| `n_mape_validos` | int64 | Obrigatório |
| `fator_sobreposicao` | float64 | Obrigatório |
| `mae_mwmed` | float64 | Obrigatório |
| `rmse_mwmed` | float64 | Obrigatório |
| `mape_pct` | float64 | Sim |
| `erro_medio_mwmed` | float64 | Obrigatório |

### `eventos_pendentes_v5.csv`

Espelho byte a byte do candidato T-19, sem as colunas comuns. Chave no espelho `data_local`. As 3 linhas têm `conhecido_desde` vazio e `acao` de manter excluídas. Seu layout próprio, na ordem, é `data_local,nome_evento,tipo_proposto,esfera_proposta,ato_ou_fonte,fonte_url,alcance_horario_pendente,motivo_pendencia,conhecido_desde,acao`. O campo de data usa o formato civil. Trata-se de evidência de exclusão, com os eventos administrativos federais auditados das mesmas datas preservados.

## Janelas e famílias

| Etapa | Origens por cenário e modelo | UTC, primeira a última |
|---|---:|---|
| `validacao_1s2025` | 4.293 | 2025-01-01T03:00:00Z a 2025-06-28T23:00:00Z |
| `teste_2025` | 4.365 | 2025-07-01T03:00:00Z a 2025-12-29T23:00:00Z |
| `retrospectiva_2026` | 7.245 | 2026-01-01T03:00:00Z a 2026-10-29T23:00:00Z |

24 h: `ols_estabilizado`, `ridge_10`, `ridge_100` e `piloto_so_carga` na validação; selecionado e piloto nas demais. 48 h: `ols_estabilizado`, `ridge_1` e `piloto_so_carga` nas três etapas. `sazonal_semanal` e `persistencia` ocupam colunas das previsões e linhas das métricas. Contar uma vez por par, sem duplicação entre modelos. `eh_selecionado=1` identifica a escolha integrada de cada cenário e horizonte. O MAE de validação decide, com empate pela ordem OLS e Ridge em alfa crescente.

| Cenário | Horizonte (h) | Variante selecionada | MAE na validação (MWmed) |
|---|---:|---|---:|
| `hipotese_UTC` | 24 | `ols_estabilizado` | 1090,81823648 |
| `hipotese_Sao_Paulo` | 24 | `ols_estabilizado` | 1089,7913553 |
| `hipotese_UTC` | 48 | `ols_estabilizado` | 1305,44977329 |
| `hipotese_Sao_Paulo` | 48 | `ols_estabilizado` | 1300,21983444 |

O piloto usa 57 atributos. Os integrados usam 169 e 241, respectivamente. As 72 flags de calendário de h25–48 explicam a diferença de especificação no primeiro dia. Os blocos possíveis são `1–24 h`, `25–48 h` e `1–48 h`. O bloco total de 48 h sobrepõe-se aos dois componentes.

## Calendário, relógios e junções

- A previsão usa `instante_alvo=origem_t+passo_h`. Cruze observado com a carga na série por alvo, versão, cenário e instante. Cruze persistência com a carga na origem e semanal com a carga no alvo menos 168 h. Compare ambos os carimbos brutos com a série.
- Converta o alvo para data civil local e selecione eventos com `conhecido_desde <= origem_t < conhecido_ate`. Fim vazio é vigência aberta. Aplique OR nas flags. `evento_versao_ids` é uma lista JSON ordenada, `[]` na ausência de evento. Valide IDs no inventário por alvo, versão, cenário e ID. Na série, o alvo é a própria hora e `origem_calendario_t=instante`. O fim de semana vem do dia civil do alvo.
- O inventário vem de `eventos_auditados_v5.csv`, SHA-256 `9c1d0e9cf1aa45d67b99fcd1d20cc424fa764c1d39f4c0efcd4db2288cd11a38`. O espelho de pendências tem SHA-256 `1f925b85135077841675d574320801d7e14800993301ac9ceea3b58c4d480499`. Há 18 linhas subnacionais (10 municipais do Rio e 8 estaduais do RJ), com escopo restrito. D+1 é hipótese de conhecimento onde registrado.
- `ano,mes,dia_mes,hora,dia_semana,dia_ano` são inteiros da hora civil, com segunda-feira igual a zero. `hora_alvo_local` varia de 0 a 23. `mes_alvo_local` usa AAAA-MM. `fonte_temp` é A621_observada, A601_fallback_t ou ffill_causal_anterior. `temp_rj_c` é obrigatório na grade.

## Métricas e comparação

Erro assinado é `y_pred − y_real`. Erro absoluto é seu módulo. Erro percentual é 100 vezes a razão entre erro absoluto e observado em módulo. Observado zero implica erro percentual nulo. MAE é média do erro absoluto, RMSE é raiz da média do erro quadrático, MAPE é média das porcentagens válidas e `erro_medio_mwmed` é média do erro assinado. `n_origens` e `n_alvos_unicos` contam instantes distintos; `n_pares` conta linhas e `n_mape_validos` conta denominadores não zero. Sobreposição é pares por alvo único. Para combinar grupos disjuntos, pondere quadrados de RMSE pelos pares e MAPE pelos válidos. Não some totais aos blocos componentes.

O recálculo v4 × v5 junta por origem bruta e passo dentro de cenário, etapa e horizonte e valida carimbo bruto alvo, instantes UTC e observado a `atol=1e-8, rtol=0`. Ambos os lados usam só a interseção, e `n_excluidos_v4/v5` medem a perda de pares de cada lado. `tipo_comparacao=mesmo_estimador` compara a mesma família; `selecionado_vs_selecionado` é reservado para mudança de escolha. Deltas são v5 menos v4. As métricas são descritivas e se referem à carga agregada ONS SE/CO em avaliação retrospectiva. Para hashes de arquivos, ambiente e fontes, leia o [manifesto](MANIFESTO_v5.json).
