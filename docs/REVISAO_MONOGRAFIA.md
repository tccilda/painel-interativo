# Revisão do painel em relação à monografia

Fonte desta revisão: Monografia_UVA.docx (1).pdf, 21 páginas. As páginas indicadas abaixo são as do arquivo PDF, contando a capa. A monografia foi preservada.

| Proposta no PDF | Correspondência no painel | Situação |
| --- | --- | --- |
| Problema de pesquisa, objetivos e delimitação, §§1.2–1.5 (p. 8–10) | Catálogo identifica ONS_SECO_piloto, carga agregada Sudeste/Centro-Oeste em MWmed. O RJ é contexto meteorológico e de calendário. O Explorador identifica emissão e alvos, com passos horários e 24h/48h. | Atendido na interface e na entrega de dados. |
| Preparação e análise de padrões temporais e associações, §1.4.2 (p. 10) | Sazonalidade mostra perfis horário, semanal e mensal, além de carga × temperatura e carga por tipo de dia. Calendário versionado conserva contexto dos atos e separa pendências. | Atendido para a série auditada V5. As associações são descritivas. |
| Construção das entradas e implementação do modelo, §§1.4.2 e 1.6 (p. 10) | O painel consulta previsões já calculadas e documenta alvo, estimador, versão, cenário, etapa e horizonte. O treinamento pertence à entrega metodológica do grupo. | O visualizador está integrado. O PDF não fornece detalhes suficientes para verificar a implementação ou reexecutar o treinamento. |
| Avaliação com dados posteriores ao treino e referência simples, §§1.2 e 1.6 (p. 9–10) | A aba de desempenho preserva validação 1S2025, teste 2025 e retrospectiva 2026. Mostra MAE, RMSE, MAPE, denominadores, persistência e semanal. V4 × V5 usa apenas a interseção fornecida. | Atendido para os resultados entregues. O manifesto registra a seleção pela validação e snapshots retrospectivos. |
| Discussão de resultados, decisões e limites, §§1.3–1.6 (p. 9–11) | Os detalhes explicam relógios alternativos, lacunas N/D, horizonte, papéis dos estimadores, cobertura e fontes. | Atendido no painel. No PDF, os capítulos de desenvolvimento, testes, resultados e conclusão aparecem apenas como títulos nas p. 17–20. |

## Mudanças e verificações

- Retirados quatro gráficos órfãos, os seletores auxiliares de previsão e as duas rotinas antigas de histórico sem chamadas de produção. Os testes da janela histórica exercitam agora o próprio código que alimenta o Explorador.
- O perfil mensal é calculado separadamente. O perfil diário e semanal já é calculado pelos respectivos gráficos. Foi removida a segunda execução que era descartada.
- A navegação pública oferece o catálogo por padrão. Arquivos próprios dos modelos aparecem quando há previsões JSON ou carga CSV. O importador legado continua disponível em instalações que usam o modo anterior. V2–V4 continuam na avaliação e não aparecem como opções de emissão. V1 aparece no Explorador quando o pacote legado está configurado.
- Um checkout sem armazenamento externo tem uma amostra rotulada de 12 emissões de referência do manifesto V5, com 432 passos originais. Os agregados de desempenho usam as amostras completas declaradas. A coleção integral continua em partições externas ou locais.
- O recorte de calendário administrativo federal ficou separado dos feriados nacionais. A aba de sazonalidade evita linguagem causal e corrige a antiga nota que dizia que a estação A601 não integrava a análise regional.
- Foram conferidos os 432 observados e as referências da amostra, usando o observado do alvo, a carga em t₀ para persistência e a carga do alvo menos 168 h para a referência semanal. Os IDs dos eventos resolveram no inventário do cenário.
- O verificador de distribuição conserva a busca por arquivos indevidos. Foi retirada a antiga opção municipal que sempre retornava reprovação, independentemente dos arquivos.

## Limitações que devem constar da monografia

O alvo não representa carga municipal ou metropolitana. A disponibilidade em tempo real e a borda oficial do carimbo ONS seguem indeterminadas. A V1 não deve ser pareada temporalmente com V2–V5 por suposição de relógio. Os resultados referem-se a uma retrospectiva não cega; perfil de carga por calendário não demonstra causalidade. O grupo deve preencher metodologia, protocolo experimental, testes e resultados no PDF com base na entrega efetivamente adotada. O painel, sozinho, não certifica o treinamento ou a ausência de vazamento.
