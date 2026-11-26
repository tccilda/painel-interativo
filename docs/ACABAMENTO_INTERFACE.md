# Monitor de Previsão — Acabamento da interface

O desenvolvimento parte de `8f9ab78`, merge convencional do [PR #2](https://github.com/tccilda/painel-interativo/pull/2) em `dev`. A `main` permanece em `26bd008`. A publicação existente segue no ambiente atual até a homologação em paralelo.

## Amostra ampliada

A revisão diferencial conferiu os 51.120 passos com as partições locais do acervo original. O índice referencia 88 partições por hash SHA-256, 1.420 emissões reais e 22 meses. As 12 emissões originais do manifesto foram preservadas. Para cada combinação de hipótese e horizonte há 97 emissões na validação de 2025, 97 no teste de 2025 e 161 na retrospectiva de 2026. Cada emissão conserva os 24 ou 48 passos do próprio horizonte. A seleção tem cobertura temporal estratificada para exploração. As métricas globais usam os recortes completos originais e as 540 linhas do catálogo permanecem idênticas.

A revisão executou 30 testes direcionados ao catálogo. A [CI do PR #2](https://github.com/tccilda/painel-interativo/actions/runs/45793607060) passou em Windows e Ubuntu.

## Alterações e verificação

| Problema | Solução | Evidência |
| --- | --- | --- |
| Seletores com opção única | Versão, estimador, mês, data e hora mostram informação fixa quando o recorte tem uma opção. Os seletores interativos conservam as chaves existentes. No catálogo público, V5 continua como padrão e a cobertura aparece no Explorador. | AppTest verifica controles fixos e interativos, alternância de etapas, hipóteses, meses, estimadores e horizontes de 24 h e 48 h. |
| Textos e navegação | Os links do topo são **Previsões**, **Desempenho** e **Sazonalidade**. Cada página conserva o título completo. Os campos de seleção têm instruções em português. As seleções múltiplas quebram linha para mostrar as opções, evitando o resumo `1 more`. | Inspeção no navegador confirmou os três links, os títulos completos, o título da aba do navegador e as opções em português. A barra Plotly mostrou ações traduzidas de zoom e exportação PNG. |
| Formatação | A apresentação usa vírgula decimal, ponto para milhares e N/D. Temperaturas do cartão, das tabelas de erro e do detalhe ao passar o cursor exibem uma casa decimal. As tabelas de métricas conservam a precisão de exibição definida para cada recorte. | Testes verificam formatação, ausências, exportação CSV com valores originais e tooltips climáticos. |
| Ordenação por texto | Em tabelas com valores numéricos e pelo menos duas linhas, **Ordenar tabela** oferece ordem crescente ou decrescente por coluna. O Pandas ordena os números originais antes da apresentação, conserva empates na ordem de origem e põe ausências no fim. | AppTest usa números negativos, positivos, milhares, ausências e infinito nas duas direções. No navegador, foi possível alternar para 48 h e selecionar MAE decrescente. |
| Escala de evolução | A comparação usa barras com origem em zero e separadores brasileiros. A tabela mantém N/D para versões ausentes no recorte. As diferenças em MWmed e em porcentagem são apresentadas na seção V4 × V5 sobre os pares comuns fornecidos. | Os testes verificam barras com base zero mesmo com diferenças residuais, cobertura por versão, comparação pareada e exportação com precisão integral. |
| Eixos de temperatura | O eixo secundário continua à direita em °C, com intervalo de marcação adaptado à amplitude e datas locais. Os valores numéricos das séries foram preservados. | Testes verificam resolução horária, diária e semanal, marcações de 0,2 °C em amplitudes estreitas, separadores e hover. No navegador, as três frequências atualizaram os gráficos com marcações sem sobreposição no recorte medido. |
| Layout responsivo | A navegação superior e as três rotas existentes foram preservadas. | Inspeção local em navegador Chromium nas três abas em 1366 × 768, 1920 × 1080 e 2560 × 1440. Não houve rolagem horizontal na página. O smoke test confirmou HTTP 200 nas três rotas com demonstração desativada. |

## Verificação reproduzível

```powershell
python scripts/check_public_bundle.py --git-index
python -m services.demo_data
python -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
python scripts/smoke_startup.py
```

A suíte local no Windows aprovou 496 testes. A verificação do pacote público e a inicialização HTTP também passaram. O workflow já existente repete essas verificações em Windows e Ubuntu.

## Pendências e limites

- Rótulos nativos como `Deploy`, `Main menu`, `Fullscreen` e comandos internos da grade continuam no idioma do componente ou navegador. Foram preservados os controles suportados pelo Streamlit, sem modificar sua estrutura interna. [API do multiselect](https://docs.streamlit.io/develop/api-reference/widgets/st.multiselect)
- O cabeçalho da grade nativa ainda ordena as células como texto. Para ordenar pelo valor use **Ordenar tabela**. Os botões **Exportar** do painel fornecem CSVs com números originais. A exportação da barra nativa reflete a grade apresentada. [API da grade](https://docs.streamlit.io/develop/api-reference/data/st.dataframe)
- A amostra pública cobre as emissões selecionadas. A disponibilização completa da V5 ainda depende da hospedagem autorizada das partições e da validação do carregamento nesse ambiente.
- A carga segue identificada como ONS Sudeste/Centro-Oeste. A definição acadêmica do recorte municipal, a convenção do fuso e a auditoria de vazamento temporal permanecem pendentes. A homologação pública deve ocorrer em ambiente paralelo autorizado.
