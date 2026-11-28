# Decisões e evidências pendentes do grupo

| Prioridade | Estado | Quem pode encaminhar | Evidência ou decisão de aceite |
| --- | --- | --- | --- |
| Recorte da monografia | Pendência | Grupo e orientação | Aprovar a redação regional proposta ou disponibilizar carga municipal comprovada e aprovar o novo plano de modelagem. Registrar decisão no capítulo de delimitação. |
| Fuso e intervalo da carga (CON-01) | Pendência | Grupo junto ao ONS | Resposta oficial referente ao recurso, versão e período. Solicitar zona do carimbo, interpretação de `00:00`, início ou fim da média, tratamento de mudanças históricas de hora e regra de agregação. Manter os dois cenários enquanto não houver resposta. |
| Latência operacional (CON-02) | Pendência | Responsáveis pelo dado e pelos modelos | Informar hora da primeira publicação, revisões e disponibilidade de cada leitura em relação à emissão. Medir a sensibilidade a atrasos, documentando a posição do intervalo. |
| Auditoria dos notebooks e modelos | Pendência | Responsáveis de 24 h e 48 h | Entregar notebooks exatos com hashes, módulos de apoio, ambiente, dados aprovados, comandos e logs. Executar a reprodução com os critérios abaixo. |
| Pareamento independente V4 × V5 | Parcialmente comprovada | Responsáveis pelos modelos | Entregar `pares_v4_24h.csv.gz` e `pares_v4_48h.csv.gz` identificados no manifesto V5, com dicionário, janela e autorização. Conferir chaves, observados e perdas na junção. |
| Comparação complementar com boosting | Hipótese | Grupo e orientação | Decidir se entra no escopo. Se aprovada, registrar protocolo temporal e pares antes de estimar hiperparâmetros. |
| Homologação e publicação integral | Pendência | Administração do GitHub e Streamlit do grupo | Homologar o app paralelo com a amostra e guardar o registro de versão e URL. Completo depende de autorização de distribuição e destino HTTPS aprovado. |

## Pedido de evidências aos responsáveis pelo treinamento

1. Fornecer `modelo_24h_2024_2026_v5.ipynb` e `modelo_48h_2024_2026_v5.ipynb`, além dos scripts importados, em revisão imutável. SHA-256 esperados no manifesto, respectivamente `4da0cd6b37cc65f8f9ece8d14c86ff2afeadd255daa72a9a6df2ca1332e13089` e `13a4ac1125154b5e5d90b78906e3d682941d2d00f2d3b4dbff024c64fad5ab25`. Incluir versões anteriores e logs que sustentem as alegações de mudança V1–V4.
2. Entregar, por hipótese e horizonte, a divisão efetiva por emissão e alvo, datas limites de cada conjunto, política de reajuste, exclusões, origem dos pesos e tabelas de busca e seleção de alfa. Indicar quando o teste foi consultado e por quem. Confirmar que nenhum alvo posterior ao corte entrou no ajuste que deveria antecedê-lo.
3. Fornecer catálogo de atributos e matrizes por etapa ou amostra auditável. Para cada valor, registrar instante de referência, fonte, hora de disponibilidade, interpolação/preenchimento e janela usada. Incluir lags de carga, temperatura observada ou produto de previsão meteorológica com carimbo de emissão, e atos de calendário com vigência.
4. Entregar especificação de cada transformador, imputador, ordenação das colunas, solver, tolerância, penalização e regra de intercepto. Disponibilizar logs ou objetos ajustados que identifiquem as linhas de `fit`. Conferir que parâmetros de escala e imputação não usaram linhas de teste ou retrospectiva.
5. Guardar o ambiente executável, versões, sementes e comando de reprodução. Regerar as mesmas previsões e comparar chaves, valores, máscaras e métricas aos arquivos publicados. Isolar casos de descarte em fronteiras e feriados. Documentar limitações de uso do snapshot mesmo se a reprodução coincidir.

A aprovação científica do treinamento exige evidência do código, dos dados e do protocolo. A aprovação técnica do painel exige checkout, suíte e homologação de implantação. [Metodologia](METODOLOGIA_CIENTIFICA.md) · [Checklist Streamlit](DEPLOY_STREAMLIT.md)
