# Monitor de Previsão — Resultados para a banca

O painel avalia a carga regional do subsistema Sudeste/Centro-Oeste do ONS (`ONS_SECO_piloto`, MWmed). As medições meteorológicas no Rio e os atos municipais e estaduais são variáveis auxiliares de alcance local. O recorte territorial da monografia ainda depende de decisão do grupo.

## Resultados frente às referências

O destaque de Desempenho acompanha versão, estimador, horizonte, bloco, etapa e hipótese. Com **Todas**, o destaque usa a V5. As barras começam em zero. Cada método tem seu próprio contador de pares e as reduções são calculadas como 100 × (MAE da referência − MAE do modelo) / MAE da referência. Resultado negativo indica MAE maior no modelo. Referência ausente ou MAE de referência igual a zero gera N/D para a redução.

| V5, OLS estabilizado, teste 2025, hipótese São Paulo | 24 h | 48 h completas |
| --- | ---: | ---: |
| OLS, MAE em MWmed | 1.080,64 | 1.262,65 |
| Sazonal semanal, MAE em MWmed | 2.022,87 | 2.025,19 |
| Persistência, MAE em MWmed | 5.508,19 | 5.853,31 |
| Redução frente à sazonal semanal | 46,58% | 37,65% |
| Redução frente à persistência | 80,38% | 78,43% |
| Pares de emissão e passo por método | 104.760 | 209.520 |

O painel lê os CSVs globais verificados pelo manifesto. O destaque rotula os agregados como descritivos, pois a igualdade de contagens por si só não comprova identidade dos alvos. A auditoria adicional do acervo completo V5 verificou os hashes das 88 partições, a chave de emissão e passo e o alinhamento dos alvos. Para o OLS e as duas referências, os erros foram calculados lado a lado nas mesmas linhas e agregados por hipótese, etapa, horizonte e bloco. O resultado reproduziu 72 MAEs e os denominadores de MAE e MAPE em 24 recortes. As 3.816.720 ocorrências de pares-bloco desse cheque incluem pares que aparecem nos blocos parciais e no bloco completo de 48 h.

```powershell
# Para o diretório local completo gerado pelo preparador da entrega V5.
python scripts/audit_v5_headline.py "C:\caminho\para\data\versions\detail"
```

## Sensibilidade à hipótese de horário

A seção alinha alvo, unidade, versão, estimador, escopo, etapa, horizonte e bloco. UTC e São Paulo são interpretações alternativas dos carimbos originais. A exibição das horas civis em São Paulo é uma escolha da interface. Para cada métrica, a seção apresenta os dois valores, a diferença com sinal São Paulo − UTC, a magnitude e a variação relativa à hipótese UTC. A diferença de MAPE tem unidade de pontos percentuais.

As métricas usam os pares de cada hipótese. Diferenças pequenas não demonstram equivalência estatística. A hipótese oficial e a convenção da hora da carga continuam pendentes (CON-01).

## Ano-Novo de 2026

O estudo consulta a emissão real de 1º de janeiro às 00:00 locais declarada no manifesto para cada hipótese e horizonte. O gráfico exibe 72 h anteriores à emissão, previsão, observação, persistência e referência sazonal. A tabela calcula MAE e MAPE sobre a interseção dos alvos disponíveis aos três métodos. Observados zero são excluídos somente do MAPE. Os eventos são identificados pelos IDs presentes na partição.

| Hipótese | Horizonte | MAE do OLS na emissão (MWmed) | MAE sazonal na emissão (MWmed) | MAE do OLS no recorte completo (MWmed) |
| --- | ---: | ---: | ---: | ---: |
| UTC | 24 h | 2.340,24 | 494,22 | 1.140,21 |
| São Paulo | 24 h | 1.828,49 | 464,23 | 1.130,80 |
| UTC | 48 h | 3.196,54 | 1.501,91 | 1.320,62 |
| São Paulo | 48 h | 2.529,13 | 1.316,90 | 1.313,14 |

Em 48 h sob a hipótese UTC, o maior erro absoluto do OLS foi 7.838,44 MWmed, no passo 34, em 2 de janeiro às 10:00 no horário de São Paulo. A sazonal semanal teve o menor MAE nas quatro combinações dessa emissão. No recorte completo de retrospectiva, o OLS teve MAE menor que a mesma referência. O episódio ilustra variação de desempenho entre emissões e o calendário descreve o contexto observado.

## Evolução V1–V5 e limites

- O inventário histórico preserva o carimbo sem fuso documentado da V1. Os manifestos e resumos de V2–V4 registram os estimadores selecionados. Em 48 h no teste de 2025 sob a hipótese São Paulo, o Ridge 1 da V2 teve MAE de 1.284,89 MWmed, menor que os 1.285,14 MWmed do OLS estabilizado da V3. Esse contraste é descritivo.
- Os 118 agregados compartilhados pela V3 e V4 foram comparados pela chave completa. A maior diferença observada foi inferior a 0,000000001 MWmed em MAE e RMSE e a 0,00000000001 ponto percentual em MAPE. A documentação histórica registra a mudança na verificação de posto na V4. Estabilidade numérica e desempenho preditivo são propriedades distintas.
- No arquivo de pares comuns, o OLS V5 em 48 h sob a hipótese São Paulo teve MAE 22,48 MWmed menor que a V4 no teste de 2025 (209.520 pares) e 12,98 MWmed maior na retrospectiva de 2026 (347.760 pares). A comparação usa os pares declarados no arquivo fornecido. A reconstrução independente de toda a junção exige as previsões originais da V4.
- O escopo declarado é retrospectivo. O protocolo completo de treinamento e a disponibilidade dos atributos na emissão ainda precisam de validação reproduzível para concluir sobre vazamento temporal.

## Calendário e apresentação

O calendário contabiliza horas únicas, datas civis distintas, cobertura do intervalo e observações por hora. Âmbitos simultâneos ficam na mesma categoria. O gráfico de médias exige cinco datas civis observadas por categoria como critério exploratório. Registros das categorias raras continuam consultáveis. O limiar não determina significância estatística.

O controle de temperatura usa `format="localized"`. O separador depende do idioma do navegador e os limites retornados continuam numéricos. [Documentação oficial de st.slider](https://docs.streamlit.io/develop/api-reference/widgets/st.slider)

Fontes versionadas no projeto: `data/versions/metricas_versoes_anteriores`, `data/versions/entrega_painel_v5` e `data/versions/preview`. Os resumos e manifestos individuais V2–V4 foram consultados somente para leitura no pacote original. A camada de apresentação usa os agregados publicados e consulta uma partição de detalhe por vez.
