# Fundamentação metodológica — Monitor de Previsão

As classificações abaixo se referem à verificação feita para esta entrega. **Comprovada** identifica evidência direta e reproduzível no recorte indicado. **Parcialmente comprovada** identifica evidência documental ou verificação de parte do processo. **Hipótese** identifica uma escolha experimental aberta. **Pendência** identifica evidência ou decisão ainda necessária.

## A. Variável-alvo e proposta à monografia

**Comprovada.** O identificador interno `ONS_SECO_piloto` representa a carga horária agregada do subsistema Sudeste/Centro-Oeste do Sistema Interligado Nacional, medida em megawatts médios (MWmed). O CSV de origem usa `id_subsistema=SE` e `val_cargaenergiahomwmed`. O ONS descreve o SE/CO como as regiões Sudeste e Centro-Oeste mais Acre e Rondônia. Trata-se do recorte elétrico do subsistema, que inclui o Rio e abrange outras áreas da rede. [Catálogo da Curva de Carga Horária](https://dados.ons.org.br/dataset/curva-carga) · [ONS, Boletim de Geração Solar, seção 4](https://www.ons.org.br/AcervoDigitalDocumentosEPublicacoes/Boletim%20Mensal%20de%20Gera%C3%A7%C3%A3o%20Solar%202021-01.pdf)

**Comprovada.** O SHA-256 do CSV ONS 2024 obtido do recurso oficial é `0c7e02591887591ec0a1e758eeb744dcd24c69e91c09e032ce7772838676cc32`, igual ao do manifesto V5. A junção um a um entre `din_instante` e `instante_ons_raw`, conservando o texto civil sem atribuir fuso, encontrou 8.784 horas e diferença máxima 0,0 MWmed no recorte São Paulo. Na hipótese UTC, a mesma janela canônica da V5 retém 8.781 carimbos brutos de 2024 e todos coincidem. A janela começa em 01/01/2024 às 03:00 UTC em ambas as hipóteses. Esse cheque identifica a série e sua proveniência. [Recurso CSV de 2024](https://dados.ons.org.br/dataset/curva-carga/resource/a481308d-3db5-4e03-9a0e-898583408254) · [Manifesto V5](../data/versions/entrega_painel_v5/MANIFESTO_v5.json)

**Comprovada.** A versão examinada da monografia, `Monografia_UVA.docx (1).pdf`, 21 páginas, SHA-256 `d19013ced5c571dd1943cf14ef97618f5a727571b50b9e392db315c96c71fff4`, propõe prever carga de curto prazo em uma área brasileira. As seções 1.4.1, 1.4.2 e 1.5, páginas 9–10 do PDF, adiam a escolha territorial até a conferência da série. A intenção anterior de estudar a capital do Rio continua como opção acadêmica dependente de dados municipais comprovados.

**Pendência — proposta para decisão do grupo.**

| Parte da monografia | Redação ou encaminhamento proposto |
| --- | --- |
| Objetivo geral | Desenvolver e avaliar retrospectivamente uma aplicação de previsão horária de carga do subsistema Sudeste/Centro-Oeste do ONS, em horizontes independentes de 24 h e 48 h, discutindo desempenho frente a referências simples e limites de generalização. |
| Objetivos específicos | Identificar fonte e unidade da carga. Preparar o histórico e documentar suas duas hipóteses de horário. Descrever sazonalidade e associações com clima e calendário locais. Avaliar OLS e Ridge frente à persistência e à referência sazonal semanal. Comunicar erros, cobertura e limitações em painel interativo. |
| Metodologia e testes | Separar dados de origem, preparação, treino declarado e avaliação das previsões exportadas. Explicitar etapas cronológicas, efeitos da latência de publicação, hipóteses de fuso, chave dos pares e regra de seleção por MAE. |
| Resultados | Apresentar comparações por hipótese, etapa e horizonte, com denominadores. Usar o caso de Ano-Novo para contrastar uma emissão com seu recorte completo. |
| Limitações | Discutir clima e calendário de alcance local, carimbo e borda da carga em aberto, condições de retrospectiva e requisitos para reproduzir o treinamento. |

## B. Carimbo, intervalo e relógios

| Evidência | Classificação e leitura |
| --- | --- |
| [Dicionário da Curva de Carga do ONS, p. 1](https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/curva-carga-ho/DicionarioDados_CurvaCarga.pdf) | **Comprovada.** Define `din_instante` como “Data de referência”, tipo DATETIME, formato `YYYY-MM-DD HH:MM:SS`, e a carga em MWmed. O campo publicado não contém deslocamento. O dicionário consultado não informa fuso ou posição do carimbo no intervalo. |
| [Catálogo CKAN](https://dados.ons.org.br/dataset/curva-carga), seção Informações Adicionais | **Comprovada.** O indicador “(UTC)” aparece em “Última Atualização” e “Criado”, datas administrativas do catálogo. |
| [ONS, Histórico da Operação](https://www.ons.org.br/Paginas/resultados-da-operacao/historico-da-operacao/curva_carga_horaria.aspx) | **Parcialmente comprovada.** O histórico descreve dados originários em grande parte da base técnica do ONS e grandezas supervisionadas e programadas. O catálogo define discretização horária. As fontes consultadas não permitem concluir a regra de agregação/fechamento nem a hora de disponibilização de cada observação. |
| [Dicionário V5](../data/versions/entrega_painel_v5/DICIONARIO_DADOS_v5.md) e manifesto | **Hipótese.** Interpretar o carimbo bruto como UTC ou `America/Sao_Paulo`. Ambos são convertidos a UTC na chave de cálculo. Exibição e data civil de calendário usam `America/Sao_Paulo` em ambos. Início de hora, lag operacional zero e atraso zero são condições do replay em snapshots fechados. |

**Comprovada para os agregados V5.** Nos 12 estratos de OLS comparáveis (três etapas × um bloco de 24 h e três de 48 h), a variação São Paulo − UTC, relativa ao UTC, vai de −0,826% a +0,174% em MAE, −0,905% a +0,285% em RMSE e −0,950% a +0,146% em MAPE. Os sinais variam. A auditoria compara agregados do mesmo desenho com pares de cada hipótese. Concluir equivalência estatística exigiria margem pré-fixada, amostra alinhada e método que trate dependência temporal. [Resultados e cálculo](RESULTADOS_CIENTIFICOS.md#sensibilidade-à-hipótese-de-horário)

**Hipótese de referência provisória, proposta.** Manter UTC como referência de apresentação por já ser a abertura do painel, fixando a escolha antes da leitura de novos resultados. Apresentar São Paulo lado a lado e usar a hora civil local para explicar clima, calendário e emissões. O desempenho próximo e de sinal variável sustenta apresentar as duas interpretações. A decisão oficial depende de resposta do ONS para esse produto, versão e período, incluindo exemplo de `00:00` e regra da publicação.

## C. Auditoria dos modelos e do treino

Foram pesquisados o pacote consolidado, a entrega V5, o `painel.zip` legado, os manifestos individuais V1–V4, o workspace, o histórico Git disponível, as branches de modelos 24 h/48 h no repositório antecedente (somente README) e o Drive conectado. Os manifestos referenciam notebooks por nome e hash, inclusive `modelo_24h_2024_2026_v5.ipynb` e `modelo_48h_2024_2026_v5.ipynb`. Os notebooks correspondentes, componentes importados e logs íntegros de treino não foram localizados nessas fontes. As funções de leitura, preparação das partições e auditoria do painel operam sobre previsões exportadas. [Leitor dos dados](../services/model_versions.py) · [Auditoria de saída](../scripts/audit_v5_headline.py)

| Questão | Classificação e evidência |
| --- | --- |
| Períodos e seleção | **Parcialmente comprovada.** A V5 declara 8.565 origens no treino 2024, 12.909 no reajuste até 1S2025 e 17.325 no refit 2024–2025. As janelas de avaliação declaradas têm 4.293 origens na validação do primeiro semestre de 2025, 4.365 no teste do segundo semestre e 7.245 na retrospectiva 2026. O manifesto fixa menor MAE na validação e desempate por OLS e depois Ridge em alfa crescente. Os CSVs corroboram a seleção de OLS nas duas hipóteses e horizontes. A associação entre cada artefato ajustado e suas linhas de treino, o limite dos alvos na fronteira entre conjuntos e a inspeção prévia do teste seguem sem verificação direta. |
| Atributos e lags de carga | **Parcialmente comprovada.** O manifesto declara 57 lags de carga, nove meteorológicos, 169 atributos integrados em 24 h, 241 em 48 h e 57 no piloto. O dicionário mostra que as 72 flags de calendário dos passos 25–48 alteram a especificação do modelo de 48 h. O replay usa a carga na origem e atraso zero. Falta verificar a lista exata de lags, o momento real de disponibilidade, revisões da fonte e cada construção de atributo em `t₀`. |
| Clima futuro | **Pendência.** A série auditada contém leituras observadas. Isso não identifica quais colunas entraram em cada matriz de treino ou inferência, nem comprova que observados posteriores a `t₀` ficaram fora. Verificar se houve apenas lags/fonte observada disponível, previsão meteorológica arquivada com emissão ≤ `t₀`, cenário fixo ou observação posterior usada como informação perfeita. |
| Transformações e regularização | **Parcialmente comprovada.** O histórico registra padronização ajustada no treino e tolerância explícita no OLS estabilizado. O manifesto identifica Ridge 10 e 100 no integrado de 24 h e Ridge 1 no de 48 h. Ainda é necessário conferir `fit` dos transformadores e imputadores em cada janela, ordem das operações, solver, `rcond`, convenção de alfa/intercepto e histórico do espaço de busca. |
| Vazamento e reprodução | **Pendência.** As saídas verificam datas, passos, referências, hashes e métricas. A integridade das saídas não demonstra ausência de vazamento no treinamento. Falta reexecutar os dois notebooks com suas dependências, dados e configuração originais, confrontar os hashes e inspecionar as matrizes e os logs antes de concluir. |

Os nomes, hashes e evidências a solicitar estão em [Pendências do grupo](PENDENCIAS_GRUPO.md). A auditoria da saída reproduziu 72 MAEs e os denominadores de MAE/MAPE em 24 recortes do OLS e suas referências, lendo um Parquet por vez. A homologação científica do treino é uma etapa própria.

## D. Estimadores e evolução

OLS ajusta coeficientes para minimizar a soma dos quadrados dos resíduos em exemplos rotulados. Ridge minimiza o mesmo erro acrescido de penalidade L2, controlada por alfa. São abordagens supervisionadas e transparentes para uma primeira referência. Coeficientes podem ajudar a descrever associações condicionais, com cautela frente a escala, colinearidade e variáveis omitidas. Lags e flags correlacionadas podem tornar o OLS sensível a posto e condicionamento. Ridge reduz a magnitude dos coeficientes e pode reduzir variância em troca de viés. Um solver mais estável melhora a solução numérica. Redução do erro preditivo exige avaliação nos alvos. [Hoerl e Kennard, 1970, DOI 10.1080/00401706.1970.10488634](https://homepages.math.uic.edu/~lreyzin/papers/ridge.pdf)

| Versão | Evidência disponível |
| --- | --- |
| V1 | **Comprovada nas saídas.** Manifesto/resumo V1 e ZIP legado registram OLS bruto, alternativas, referências e carimbo com fuso sem documentação. A validação tem agregados no pacote histórico. |
| V2 | **Comprovada nos agregados.** Manifesto/resumo V2 registram as duas hipóteses e indicam OLS bruto em 24 h e Ridge 1 em 48 h. O histórico descreve reconstrução da grade e clima; **parcialmente comprovada** a implementação sem os notebooks. |
| V3 | **Comprovada nos agregados.** Manifesto/resumo V3 registram OLS estabilizado para os dois horizontes. O histórico descreve padronização no treino e tolerância; **parcialmente comprovada** a implementação. |
| V4 | **Comprovada nas métricas comuns.** Os 118 agregados alinhados V3/V4 diferem menos de 10⁻⁹ MWmed em MAE e RMSE. O resumo registra ampliação de cortes e preservação dos pares. A correção do diagnóstico de posto é **parcialmente comprovada** pela documentação histórica, sem o código executado. |
| V5 | **Comprovada na entrega.** Calendário versionado, inventário de vigência e métricas publicadas. Em 48 h, sob a hipótese São Paulo, V5 − V4 foi −22,48 MWmed no teste de 2025 e +12,98 MWmed na retrospectiva de 2026, usando o arquivo fornecido de pares comuns. A junção integral requer os pares brutos V4. |

Em 48 h completas no teste de 2025, hipótese São Paulo, o Ridge 1 selecionado da V2 teve MAE 1.284,89 MWmed e o OLS selecionado da V3, 1.285,14 MWmed. O contraste é descritivo e envolve estimadores diferentes. V1 fica isolada dos recortes posteriores em razão do carimbo.

**Hipótese para experimento opcional.** XGBoost ou LightGBM permitem interações e respostas não lineares, com maior espaço de ajuste. Se aprovado, comparar um deles com OLS, Ridge e referências nos mesmos alvos, atributos comprovadamente disponíveis em `t₀` e orçamento de busca declarado. Usar validação cronológica por origem com pré-processamento ajustado dentro de cada janela e reservar um período objetivo jamais usado na escolha. Publicar estabilidade por passo e custo, além dos erros. Nenhuma métrica desses métodos integra a entrega atual. [Chen e Guestrin, 2016, DOI 10.1145/2939672.2939785](https://arxiv.org/abs/1603.02754) · [Ke et al., 2017, NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html)

## E. Clima, calendário e Ano-Novo

**Comprovada na série auditada.** A621 (Vila Militar, Rio de Janeiro) e A601 (Seropédica, RJ) são estações locais. Em cada hipótese, a série composta tem 24.812 horas de A621, 23 de A601 na mesma hora e duas preenchidas com leitura anterior. A exibição de média das leituras disponíveis é uma análise de contexto distinta da série composta dos modelos. Dê aos instantes do INMET o relógio indicado no dado original e registre os limites da leitura e seu momento de publicação. A data civil de cada alvo deriva da hipótese do ONS e da conversão para São Paulo. [INMET, Dados históricos anuais](https://portal.inmet.gov.br/dadoshistoricos/) · [Série auditada](../data/versions/entrega_painel_v5/serie_horaria_auditada_v5.csv)

**Comprovada no inventário.** Atos municipais e estaduais têm alcance territorial próprio. Pontos facultativos administrativos valem para o órgão ou esfera indicados. A regra de elegibilidade usa o conhecimento registrado na emissão e preserva eventos simultâneos sem multiplicar horas. 1º de janeiro é feriado nacional, conforme a Lei 662/1949 com redação da Lei 10.607/2002. O ID exportado para o episódio de 2026 remete à portaria federal do inventário e deve conservar seu campo de alcance administrativo. As associações visuais e o limiar exploratório de cinco datas não identificam efeito causal. [Lei 10.607/2002](https://www.planalto.gov.br/ccivil_03/leis/2002/l10607.htm) · [Lei 9.093/1995](https://www.planalto.gov.br/ccivil_03/leis/l9093.htm) · [Eventos versionados](../data/versions/entrega_painel_v5/eventos_calendario_v5.csv)

**Comprovada na emissão de referência.** Em 48 h sob UTC, a emissão de Ano-Novo teve MAE de 3.196,54 MWmed no OLS, 1.501,91 MWmed na sazonal semanal e 3.990,98 MWmed na persistência sobre os mesmos 48 alvos. Na retrospectiva completa de 48 h sob UTC, o OLS teve MAE de 1.320,62 MWmed e a sazonal, 2.412,08 MWmed, com 347.760 pares. O episódio selecionado de contraste limita alegações de desempenho uniforme. [Estudo de caso](RESULTADOS_CIENTIFICOS.md#ano-novo-de-2026)

## F. Leitura dos resultados e dos denominadores

**Comprovada nos agregados do teste de 2025, hipótese São Paulo.** A redução de MAE do OLS estabilizado em 24 h foi 46,58% ante sazonal e 80,38% ante persistência. Em 48 h completas, foi de 37,65% e 78,43%. As referências repetem a carga na emissão e a carga 168 h antes do alvo, respectivamente para persistência e sazonal semanal. MAE e RMSE usam MWmed. MAPE usa porcentagem e exclui observado zero apenas desse denominador.

| Horizonte e bloco | Emissões | Pares de emissão e passo | Alvos horários únicos |
| --- | ---: | ---: | ---: |
| 24 h independente, 1–24 h | 4.365 | 104.760 | 4.388 |
| 48 h, 1–24 h | 4.365 | 104.760 | 4.388 |
| 48 h, 25–48 h | 4.365 | 104.760 | 4.388 |
| 48 h completas, 1–48 h | 4.365 | 209.520 | 4.412 |

O mesmo alvo pode ser previsto a partir de várias origens e passos. Os alvos únicos dos dois blocos de 48 h também se sobrepõem. Indique o horizonte, bloco, etapa e hipótese junto de cada número. A distribuição pública de 1.420 emissões em 22 meses é uma amostra de exploração. Toda métrica global exibida continua vindo dos agregados originais. Snapshots retrospectivos permitem estudar erros históricos sob hipóteses explícitas. Desempenho operacional futuro exige dados disponíveis no momento, regras de atraso e avaliação nova. [Agregados V5](../data/versions/entrega_painel_v5/metricas_globais_v5.csv) · [Tashman, 2000, DOI 10.1016/S0169-2070(00)00065-0](https://www.sciencedirect.com/science/article/pii/S0169207000000650) · [Hewamalage et al., 2023, DOI 10.1007/s10618-022-00894-5](https://doi.org/10.1007/s10618-022-00894-5)

## Identificação do acervo consultado

- Pacote original `drive-download-20261121T002429Z-1-001.zip`, SHA-256 `de87d5eb5e0808d14864e20b0c059408a97e0a1b42659cb7115ae1952d533ef7`. Consultados os manifestos e resumos individuais V1–V4, o consolidado histórico e a entrega V5.
- Entrega independente `entrega_painel_v5.zip`, SHA-256 `23ca3090c926d690b33bb1b14b75b083b9b4b55e6726ce6965be2fc69ef849e9`. Contém previsões, métricas, inventário e documentação de exportação.
- Pacote `painel.zip`, SHA-256 `b10830eaae445d958d42f05f00551b66a500126af7cbfdfd7d981f34f7e7f9d7`. Contém a série integrada e previsões e resumos legados. Foi consultado em leitura.

As fontes institucionais foram consultadas em 27/11/2026. O painel e os trabalhos acadêmicos do grupo conservam suas respectivas autorias. A redação proposta para a monografia segue para decisão do grupo.
