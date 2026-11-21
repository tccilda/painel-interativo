# Integração do pacote v5 no painel

Selecione explicitamente este diretório versionado. Leia `MANIFESTO_v5.json` e exija `versao=v5`, `versao_esquema=1.0.0` e o conjunto completo de dez CSVs. Confira SHA-256, tamanho, cabeçalhos, tipos, chaves e contagens antes de habilitar o pacote. Use o [dicionário de dados](DICIONARIO_DADOS_v5.md) na leitura. Em qualquer divergência, mostre “Pacote v5 incompatível” com arquivo e regra violada e mantenha a fonte ativa. A equipe do painel decide a adoção. Os seis CSVs históricos da v1 seguem no diretório original e permanecem disponíveis ao leitor histórico.

## Recorte e rótulos

- Entradas explícitas da consulta: alvo `ONS_SECO_piloto`, versão `v5`, hipótese de relógio, etapa, horizonte e modelo. Sugestão de vista inicial após escolha explícita do cenário: `teste_2025`, 24 h, `eh_selecionado=1`. As duas hipóteses têm igual estatuto. A seleção de uma para exibição vale apenas para a vista.
- Consulte uma emissão por `origem_t` e ordene por `passo_h`. Para a curva, use `instante_alvo`, observado, previsão, semanal e persistência. Cada referência aparece uma vez por origem e passo na vista. Use os modelos físicos para comparar previsões. Use as tabelas de métricas para consultar as duas referências como modelos de comparação.
- Leia `origem_t` e `instante_alvo` como UTC com `Z`. Converta para `America/Sao_Paulo` apenas na exibição local. Preserve `*_ons_raw` como texto de auditoria sem fuso. Horas e meses das métricas referem-se à data civil do alvo. A ação de filtrar emissões usa a hora de origem.
- Nos títulos, mostre ONS SE/CO, MWmed, a hipótese escolhida, o horizonte e o período da etapa. O rótulo de disponibilidade é “Retrospectiva sobre snapshots fechados, períodos examinados”. A disponibilidade operacional e o intervalo do carimbo seguem em aberto. A série avaliada é a do subsistema, com a previsão da carga total da RMRJ em aberto.

Para consultar uma origem sem materializar milhões de linhas, use o horizonte escolhido, o cabeçalho e as chaves do dicionário. Exemplo em Python após as verificações do manifesto:

```python
import pandas as pd

tipos = {campo: "str" for campo in ("alvo_id", "versao", "cenario", "etapa", "origem_t")}
tipos.update(passo_h="int64", eh_selecionado="int64", y_pred="float64", y_real="float64")
for lote in pd.read_csv(
    pacote / "previsoes_24h_v5.csv", chunksize=100_000,
    dtype=tipos, float_precision="round_trip", keep_default_na=False,
):
    recorte = lote.loc[
        lote["alvo_id"].eq("ONS_SECO_piloto") & lote["versao"].eq("v5")
        & lote["cenario"].eq(cenario_escolhido) & lote["etapa"].eq("teste_2025")
        & lote["origem_t"].eq(origem_utc_z) & lote["eh_selecionado"].eq(1)
    ]
    # Recolher os trechos, verificar 24 passos únicos e converter datas para a exibição.
```

Na tela de desempenho, escolha uma granularidade entre bloco, passo, hora civil ou mês civil. O total `1–48 h` já contém os blocos `1–24 h` e `25–48 h`. Some somente recortes disjuntos. Erros descritivos podem compartilhar alvos entre emissões. Para calendário na curva, leia as flags e os IDs da linha de previsão, interpretados na origem. Na série, `origem_calendario_t=instante`. Resolva todos os IDs no inventário via alvo/versão/cenário/ID. Informe que os atos subnacionais são locais e que o corte D+1 é hipótese nos registros indicados.

## Migração dos seis CSVs históricos

| Origem v1 | Vista v5 | Ajuste de esquema |
|---|---|---|
| `previsoes_24h_2025_2026.csv` | `previsoes_24h_v5.csv` | Selecionar identidade, cenário, etapa e modelo; UTC explícito e três etapas; prever 24 passos por emissão. |
| `previsoes_48h_2025_2026.csv` | `previsoes_48h_v5.csv` | Mesma filtragem, com 48 passos; primeiro dia usa 241 atributos integrados, frente a 169 no modelo de 24 h. |
| `resumo_metricas_24h.csv` | `metricas_globais_v5.csv`, horizonte 24 | `origens → n_origens`, `pares → n_pares`, `horizonte → horizonte_h + bloco_horas`, `config_integrado → modelo + eh_selecionado`. |
| `resumo_metricas_48h.csv` | `metricas_globais_v5.csv`, horizonte 48 | Mantém métricas e contagens centrais; ganhos contra uma referência são derivados de linhas do mesmo recorte. |
| `resumo_metricas.csv` | `metricas_globais_v5.csv` | `horizonte_modelo → horizonte_h` inteiro. Use meia-risca nos blocos v5. Normalize hífens antigos apenas no leitor histórico. |
| `serie_horaria_integrada_2024_2026.csv` | `serie_horaria_auditada_v5.csv` e `eventos_calendario_v5.csv` | Série por cenário, UTC explícito. Os IDs recuperam nomes, esferas e versões. Os eventos futuros da curva vêm da previsão. |

Mapeie “Validação 1S2025” e `validacao` para `validacao_1s2025`, “Teste 2S2025” para `teste_2025` e `forecast_2026` para `retrospectiva_2026`. Os rótulos históricos de integrado são papéis. Use o identificador do estimador e a flag de seleção na v5. `piloto_candidato` mapeia para `piloto_so_carga`, e `semanal` para `sazonal_semanal`.

## Testes de integração

Exercite 12 emissões (2 cenários × 2 horizontes × 3 etapas), incluindo uma virada de dia UTC e uma conversão para o relógio civil. Nos exemplos de vigência, 27/10/2026 às 23h BRT ativa o ID antigo para 28/10. Às 00h BRT de 28/10, o ID antigo deixa de valer e o novo entra no passo 48 em 48 h. Em 24 h, o novo alvo aparece no passo 24 a partir de 29/10 às 00h BRT. Teste um manifesto incompleto, coluna de cenário ausente e chave duplicada, sempre preservando a fonte ativa. A geração verificou esses portões em leitor isolado. A adoção da interface e sua publicação são decisões da frente do painel.
