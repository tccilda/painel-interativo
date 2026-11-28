# Perguntas para a banca

## Qual é a variável-alvo?

**Comprovada.** É a carga horária agregada do subsistema Sudeste/Centro-Oeste do ONS em MWmed, com código interno `ONS_SECO_piloto`. O CSV oficial e a série entregue coincidem nas 8.784 horas brutas de 2024 na hipótese São Paulo. A monografia examinada previa escolher uma área brasileira após conferir os dados. A redação regional está proposta para decisão do grupo.

## Por que usar clima e calendário do Rio?

**Parcialmente comprovada.** As duas estações são fontes observadas de alcance local e os eventos têm os âmbitos de seus atos. Essas variáveis permitem explorar associações e dar contexto às previsões do agregado regional. Duas estações não descrevem toda a diversidade meteorológica do SE/CO. Uma leitura causal exigiria um desenho próprio.

## Qual fuso horário foi usado?

**Hipótese.** O experimento localizou o carimbo bruto como UTC em um cenário e como São Paulo no outro. Ambos são exibidos em hora civil de São Paulo. O dicionário do ONS usa data de referência sem deslocamento. A indicação UTC no catálogo se refere à publicação dos metadados. A proposta de usar UTC como referência de apresentação é provisória. O maior desvio absoluto relativo entre os MAEs agregados do OLS foi cerca de 0,83%. A proximidade é descritiva.

## Por que OLS e Ridge são aprendizado de máquina?

**Comprovada quanto ao método.** São regressões supervisionadas que ajustam coeficientes a partir de entradas e cargas observadas. OLS minimiza a soma de resíduos quadráticos, e Ridge acrescenta penalidade L2, útil quando atributos se correlacionam. Interpretabilidade e custo baixo justificam o ponto de partida. A superioridade de qualquer modelo exige avaliação sob o mesmo protocolo.

## O que significa OLS estabilizado?

**Parcialmente comprovada.** A documentação histórica registra padronização ajustada no treino, tolerância do solver e a correção posterior do diagnóstico de posto. Isso diz respeito à solução numérica. V3 e V4 têm MAEs e RMSEs praticamente idênticos nos 118 agregados alinhados. Em um mesmo recorte de 48 h, o Ridge selecionado da V2 teve MAE ligeiramente menor que o OLS selecionado da V3. O código executado ainda precisa ser conferido.

## A V5 sempre melhora e o que significa redução negativa?

**Comprovada no acervo exportado.** A redução é 100 × (MAE da referência − MAE do modelo) / MAE da referência. Valor negativo informa MAE maior no modelo. Na comparação V4 × V5 fornecida para OLS de 48 h e hipótese São Paulo, a V5 reduziu o MAE no teste de 2025 e aumentou na retrospectiva 2026. A evolução depende da janela e do recorte.

## As previsões de 24 h equivalem ao primeiro dia de 48 h?

**Comprovada na especificação publicada.** São modelos independentes. O de 48 h tem atributos de calendário adicionais para os passos 25–48. Seus blocos de 1–24 h e 25–48 h pertencem ao mesmo horizonte de 48 h. A tabela mantém o horizonte e o bloco na chave.

## Vocês têm 209.520 horas distintas de teste?

**Comprovada.** O número é de combinações entre emissão e passo em 48 h completas no teste de 2025, hipótese São Paulo. São 4.365 emissões e 4.412 alvos horários distintos. Cada alvo aparece em sucessivas previsões, criando dependência. O MAPE tem denominador próprio e exclui os observados zero.

## Como responder sobre vazamento temporal?

**Pendência.** Foram auditadas as previsões já exportadas, inclusive chaves, referências, denominadores e parte das métricas recalculadas. O manifesto descreve treino e validação, mas falta conferir o código executado, a disponibilidade da carga e temperatura na emissão e onde os transformadores foram ajustados. Portanto, a ausência de vazamento permanece aberta.

## O que mostra o estudo de Ano-Novo?

**Comprovada no episódio.** Em 48 h sob UTC, a sazonal semanal teve MAE de 1.501,91 MWmed e o OLS, 3.196,54 MWmed, ambos nos mesmos 48 alvos. O padrão se inverte no agregado da mesma retrospectiva. É um contraexemplo à superioridade uniforme. A presença de feriado fornece contexto para investigação, sem atribuição causal.

## Por que não usar XGBoost ou LightGBM agora?

**Hipótese de trabalho futuro.** Um modelo de árvores pode capturar relações não lineares, mas requer comparação com os modelos existentes nas mesmas origens, atributos disponíveis e período reservado. Já há evidência suficiente para discutir o comportamento das referências lineares e simples. Nenhum resultado de boosting foi produzido para este acervo.

## A demonstração é uma previsão operacional?

**Comprovada quanto ao escopo da entrega.** A demonstração usa 1.420 emissões retrospectivas reais em 22 meses. O painel preserva as métricas globais calculadas nos recortes completos. Emitir previsões em produção exigiria fontes com latência comprovada, controle de disponibilidade e avaliação fora da janela de desenvolvimento.

[Metodologia e fontes](METODOLOGIA_CIENTIFICA.md) · [Resultados para a banca](RESULTADOS_CIENTIFICOS.md) · [Ameaças à validade](LIMITACOES_E_AMEACAS_A_VALIDADE.md)
