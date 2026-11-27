# Monitor de Previsão

*Painel Interativo de Previsão de Demanda Energética*

Monitor de Previsão é o nome provisório da aplicação do TCC de Ciência da Computação da Universidade Veiga de Almeida. O estudo tem o Rio de Janeiro como contexto e o catálogo experimental usa a série ONS Sudeste/Centro-Oeste, em MWmed.

O painel mantém fontes isoladas: **Base do grupo (CSV)** e **Arquivos dos modelos (JSON/CSV)**. A demonstração é uma ferramenta local/de testes que precisa ser habilitada explicitamente. Seus dados artificiais não representam medições, calendário oficial ou desempenho dos modelos do TCC.

Repositório oficial [tccilda/painel-interativo](https://github.com/tccilda/painel-interativo).

## Catálogo V1–V5

A fonte padrão mostra a V5 e o histórico experimental dos modelos de 24h e 48h. As métricas, a série e o calendário já acompanham o projeto. A carga da entrega corresponde ao ONS Sudeste/Centro-Oeste. Prepare o detalhe V1/V5 e configure a hospedagem seguindo o [guia de integração das versões](docs/INTEGRACAO_VERSOES.md).

A [matriz de requisitos](docs/MATRIZ_REQUISITOS.md) relaciona o pedido aos dados, código e testes. O [relatório de auditoria](docs/RELATORIO_AUDITORIA_FINAL.md) registra o que foi validado e as pendências científicas. Os [resultados para a banca](docs/RESULTADOS_CIENTIFICOS.md) documentam as comparações com as referências, a sensibilidade ao fuso e o caso de Ano-Novo. A [revisão da monografia](docs/REVISAO_MONOGRAFIA.md) identifica as seções acadêmicas correspondentes. A [fundamentação metodológica](docs/METODOLOGIA_CIENTIFICA.md) reúne as evidências para a banca e a proposta de delimitação territorial.

## Situação da publicação

O checkout abre o catálogo regional com métricas e série auditada. O Explorador desta branch inclui 1.420 emissões reais da V5. A consulta integral V1/V5 usa as partições descritas no guia. O [guia de implantação](docs/DEPLOY_STREAMLIT.md) descreve os parâmetros e a verificação do acesso público.

## Proveniência do pacote legado

A declaração municipal feita na integração anterior foi confrontada com uma fonte independente. **As 8.784 horas de carga de 2024 do pacote recebido coincidem com `val_carga` do subsistema Sudeste/Centro-Oeste**, com diferença máxima de 1,000444171950221×10⁻⁸ MWmed. O [conjunto oficial do ONS](https://dados.ons.org.br/dataset/balanco-energia-subsistema) é horário e regional; seu [dicionário](https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/balanco_energia_subsistema_ho/DicionarioDados_Balanco_Energia_Subsistema.json) define `val_carga` em MWmed. A comparação é vinculada aos hashes do ZIP e do arquivo oficial, com evidência reproduzível em `artifacts/revisao_comparacao_ons_2024.json`.

**Esse pacote está em quarentena na visão municipal.** Selecionar Base do grupo exibe o diagnóstico e impede gráficos, indicadores e exportações de carga ou resultados rotulados como municipais. O novo catálogo disponibiliza o mesmo ZIP no Explorador V1 com o rótulo regional. ZIP, configuração original, previsões e resultados recebidos permanecem intactos. Não há troca automática por dados sintéticos: a demonstração deve ser selecionada explicitamente.

O [catálogo oficial do INMET](https://apitempo.inmet.gov.br/estacoes/T) também identifica A621 como Rio de Janeiro–Vila Militar e A601 como Seropédica–Ecologia Agrícola. A601 não entra na média municipal; estações sem localização verificada ficam indisponíveis na visão municipal. Dados sintéticos continuam permitidos e sinalizados como artificiais.

O calendário recebido não é uma referência municipal integralmente verificada. Há pontos facultativos de âmbito não informado e diferenças em relação às fontes municipais de 2025: 28/02 e 31/10 constam como dias úteis no CSV, enquanto o [Decreto Rio 55.705](https://doweb.rio.rj.gov.br/apifront/portal/edicoes/imprimir_materia/1136252/6942) e a [Prefeitura/CET-Rio](https://prefeitura.rio/cet-rio/faixas-reversiveis-da-cidade-serao-suspensas-nesta-sexta-feira-3/) registram pontos facultativos municipais nessas datas. O CSV não foi reescrito. O grupo deve fornecer a carga municipal e revisar a abrangência do calendário antes do uso científico. Ponto facultativo administrativo não equivale a paralisação de toda a economia.

Relatórios locais da revisão: `artifacts/revisao_auditoria_dados.md`, `artifacts/revisao_auditoria_avaliacao.md` e `artifacts/revisao_auditoria_visual.md`. Essa pasta de evidências de trabalho não integra a distribuição Git pública. A verificação numérica independente abrange 2024; ela não certifica os demais anos nem o protocolo de treino dos modelos.

## Base fornecida: painel.zip

O inventário abaixo descreve os arquivos brutos recebidos, preservados para auditoria. Município e fuso foram inicialmente declarados pelo grupo; a evidência independente posterior contradiz o recorte municipal da carga de 2024 e impede o uso analítico desse pacote no painel municipal.

- **24.840 horas** de carga, de 01/01/2024 a 31/10/2026, sem lacunas ou duplicidades na série recebida.
- **11.618 emissões de cada horizonte**, com 278.832 alvos de 24h e 557.664 alvos de 48h. Emissões completas e valores observados/referências conferidos com a série histórica, respeitando a precisão de exportação.
- **49.540 temperaturas brutas disponíveis**, das estações A621/A601. A coluna composta `temp_rj_c` inclui fallback e preenchimento anterior; ela não é importada como uma terceira estação observada. As contagens de origem da temperatura são preservadas na proveniência.
- **1.035 dias de calendário informado**, com 21 pontos facultativos sem âmbito declarado. Esses âmbitos permanecem **não informados**; não se presume uma esfera administrativa.
- Detalhes por emissão existem para **Teste 2025** e **Forecast 2026**. A **Validação 1S2025** e o **piloto só-carga** aparecem apenas nos resumos recebidos. Seus números são identificados como fornecidos, sem inventar curvas/episódios ou afirmar que foram recalculados. Cobertura e contagens de zeros não verificáveis ficam indisponíveis.

Uma cópia íntegra está em `data/imported/painel_b10830eaae44.zip`, com SHA-256 e metadados em `data/imported/config.json`. Essa pasta é ignorada pelo Git. O ZIP é lido diretamente, sem extrair seus membros ou criar milhares de JSONs. Um catálogo leve seleciona data, hora e modelo, materializando apenas a emissão escolhida. O lote é mantido em memória como somente leitura e recarregado quando a assinatura dos arquivos muda.

Os relatórios estão em `artifacts/auditoria_serie.md` e `artifacts/auditoria_previsoes.md`. O adaptador verifica hash, formatos, horizontes, partições e correspondência com a carga; os erros exportados não substituem os cálculos do painel. O resíduo do painel continua **observado − previsto**, mesmo que algum resumo original use o sinal oposto.

O catálogo regional V1–V5 é a fonte inicial. O leitor municipal oferece **Base do grupo (CSV)** quando há configuração local e aplica o bloqueio geográfico a esse pacote. Uma base para o leitor municipal precisa representar a carga do município e documentar fonte, unidade e fuso. Hashes divergentes são recusados.

## Instalação e execução

Python **3.13** é a versão selecionada para hospedagem; versão local verificada: Python 3.13.14 no Windows. As versões de execução estão fixadas em `requirements.txt`: Streamlit 1.67.0, Plotly 6.9.0, Pandas 2.3.3, NumPy 2.5.5 e tzdata 2026.6. Pytest 9.2.0 fica somente em `requirements-dev.txt`. A instalação pode acessar o índice de pacotes Python. O servidor usa arquivos locais e previsões já produzidas, sem baixar bases nem treinar modelos na inicialização.

Com Git e Python 3.13 instalados, execute os scripts a partir da raiz da branch que contém esta aplicação:

```powershell
.\scripts\setup_local.bat
.\scripts\run_local.bat
```

O [guia Windows](docs/EXECUCAO_LOCAL_WINDOWS.md) explica a clonagem, a atualização e a troca de porta. Os comandos manuais equivalentes no PowerShell são os seguintes.



```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Abra `http://127.0.0.1:8501`. Não é necessário ativar o ambiente virtual ou mudar a política de execução do PowerShell. Para encerrar, pressione Ctrl+C. O comando acima limita a execução local ao computador. A configuração versionada preserva o tema e não fixa endereço/porta, permitindo o roteamento da hospedagem. A preferência local de estatísticas continua desativada; Community Cloud pode sobrescrever opções conforme sua própria política.

No Linux, na raiz do projeto:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Para desenvolvimento e testes, instalar as dependências adicionais e gerar fixtures em um checkout sem `data/demo/*.csv` ou `*.json`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m services.demo_data
.\.venv\Scripts\python.exe -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
.\.venv\Scripts\python.exe scripts/smoke_startup.py
```

O gerador recusa sobrescrever fixtures existentes sem `--overwrite`; não o execute para trocar dados reais. Para inspecionar a demonstração local existente, definir `$env:ENERGY_FORECAST_ALLOW_DEMO = "true"` antes de iniciar o servidor e selecionar **Demonstração** manualmente. Essa variável fica ausente/falsa na versão pública. Os 23 arquivos gerados são ignorados pelo Git; o manifesto de integridade em `tests/fixtures/demo_manifest.json` serve somente à validação local/CI.

Carregamentos padrão e catálogo usam `st.cache_data` com assinatura dos arquivos e isolamento entre fontes. O adaptador de ZIP grande conserva `st.cache_resource`. As assinaturas invalidam caches quando os arquivos mudam, sem depender de arquivos temporários persistentes.

## As três abas

1. **Explorador de Previsões.** A V5 abre por padrão. Selecione hipótese, conjunto, horizonte, mês, estimador e emissão. Compare MAE e MAPE da emissão com as referências nos mesmos alvos válidos e consulte o resumo do recorte completo. A amostra V5 cobre os meses disponíveis nas duas hipóteses, três etapas e dois horizontes. O gráfico combina histórico, previsão, observado e referências. A tabela recolhível reúne valores horários, resumo de calendário e exportação. A V1 aparece quando o ZIP legado está configurado.
2. **Avaliação de Desempenho e Erros.** Consulte as métricas fornecidas V1–V5 por versão, hipótese, etapa, horizonte e bloco. Veja os denominadores de MAE/RMSE e MAPE, a curva por passo, os dois horizontes com referências e o recorte pareado V4 × V5. Os episódios V1/V5 usam um mês de emissão de cada vez, com filtros no alvo por dia da semana, calendário e temperatura.
3. **Sazonalidade, Clima e Calendário.** Compare perfis horários e semanais, médias mensais e anuais, dispersão e séries de carga e temperatura. Filtre as categorias de calendário por tipo e âmbito. As contagens por categoria usam horas únicas, agrupam âmbitos simultâneos e destacam grupos com até 120 h de observação.

A navegação fica no topo. O seletor de fonte só aparece quando a instalação oferece opções adicionais. Explicações ficam nas ajudas dos controles e em **Detalhes metodológicos**. As tabelas exibem números em formato brasileiro e mostram N/D em células vazias. A ordenação pela grade usa o texto exibido. As exportações preservam a precisão e os identificadores da origem.

## Arquitetura

O nome e o subtítulo do aplicativo são definidos por `APP_NAME` e `APP_SUBTITLE` em `streamlit_app.py`. As variáveis `ENERGY_FORECAST_*` e o diretório temporário `energy-forecast-versions` conservam seus nomes para que configurações instaladas e caches existentes continuem funcionando.

```text
streamlit_app.py             # Configuração e navegação st.Page/st.navigation
app_pages/
  explorador.py             # Aba 1: apresentação e controles
  desempenho.py             # Aba 2: apresentação e controles
  sazonalidade.py           # Aba 3: apresentação e controles
components/
  charts.py                 # Gráficos Plotly
  metrics_cards.py          # Indicadores e formatação
  sidebar.py                # Contexto e fonte
  page_frame.py             # Cabeçalhos, identificação e seleção da emissão
services/
  data_loader.py            # Leitura local, validação e isolamento de fontes
  demo_data.py              # Geração determinística dos dados sintéticos
  forecast_service.py       # Seleção, resumo, exportação e alinhamento
  analysis_service.py       # Referências, avaliação por conjunto e desvios
  archive_loader.py         # Adaptação auditada do ZIP e seus metadados
  archive_analysis.py       # Cálculos vetorizados e resumos com origem explícita
  forecast_catalog.py       # Catálogo leve e emissão sob demanda
  app_data.py               # Cache de leitura do lote na aplicação
  geography_service.py      # Evidências territoriais e visão municipal defensiva
  history_service.py        # Filtros e disponibilidade temporal
  pattern_service.py        # Perfis e junções meteorológicas/calendário
  metrics_service.py        # MAE, RMSE e MAPE
contracts/forecast_schema.py
data/demo/                  # Fixtures locais/CI, ignoradas pelo Git
data/predictions/           # JSONs dos modelos reais
data/historical/            # Carga observada
data/weather/               # Meteorologia observada
data/calendar/              # Calendário verificado do município
data/imported/              # Cópia privada do ZIP e configuração explícita
tests/
.streamlit/config.toml
requirements.txt
requirements-dev.txt
scripts/                    # Auditoria da distribuição e smoke HTTP
docs/DEPLOY_STREAMLIT.md
.github/workflows/tests.yml # Verificação futura em Windows e Linux
AGENTS.md
.gitignore
```

Os caminhos usam `pathlib`, resolvidos a partir do projeto. As páginas recebem as mesmas estruturas nos dois modos. O conteúdo das quatro pastas de pesquisa é ignorado pelo Git, exceto `.gitkeep`. Arquivos inválidos geram avisos e estados vazios; não são corrigidos ou substituídos silenciosamente.

## Dados demonstrativos reproduzíveis

- Histórico: 25.176 registros horários, de 01/01/2024 00h até 14/11/2026 23h, no fuso America/Sao_Paulo.
- Meteorologia: 50.352 leituras de duas estações **sintéticas**, correspondentes ao histórico.
- Calendário: 1.096 datas de 2024–2026, com categorias e eventos **artificiais**, inclusive feriados e pontos facultativos fictícios.
- Previsões: 20 JSONs em dez emissões pareadas de 24h/48h, com partições declaradas. Há exemplos com dia útil, fim de semana e eventos sintéticos, para exercitar os filtros.
- As últimas previsões são emitidas em 14/11/2026 23h e seus alvos posteriores ao histórico não recebem observações ou métricas inventadas.

As datas são fixas, não acompanham o relógio. As curvas são fórmulas artificiais com ruído determinístico; nenhum modelo é treinado. O gerador não consulta observações dos alvos para produzir previsões.

Gere os arquivos da demonstração em uma cópia de desenvolvimento ou testes:

```powershell
.\.venv\Scripts\python.exe -m services.demo_data
```

Sem `--overwrite`, arquivos existentes são preservados. Não direcione o gerador para pastas de dados reais.

## Integração dos modelos e dados reais

O painel consome previsões prontas dos modelos de 24h e 48h. O [guia de integração](docs/INTEGRACAO_MODELOS.md) descreve os contratos JSON/CSV, os exemplos completos e os metadados esperados dos responsáveis.

## Regras de avaliação

Comparações usam instantes UTC; tabelas e gráficos exibem America/Sao_Paulo. `issued_at` permanece a origem da previsão e nunca é deslocado para combinar com o histórico. Observações futuras são ocultadas em todas as abas e há um aviso quando arquivos contêm esses registros.

**Referências disponíveis em t₀:** persistência repete a última carga observada até a emissão, com no máximo uma hora de defasagem. Sazonal semanal usa o alvo menos 168h, somente se essa observação já existia em t₀. Não se preenchem lacunas. A disponibilidade é baseada no timestamp do registro; se a fonte publica com atraso, o produtor deve aplicar esse atraso antes da integração.

**Temperatura:** no explorador, última leitura por estação até t₀ e até uma hora de defasagem, respeitando também o relógio atual. Na análise de erros e sazonalidade, temperatura no alvo é contexto retrospectivo, associado por instante exato; não é apresentada como variável conhecida na emissão. A seleção de todas as estações mostra uma média espacial explicitamente identificada.

**Amostras comparáveis:** métricas são separadas por região, unidade, partição, modelo/versão e segmento. Quando há emissões comuns de 24h/48h, a comparação usa essas emissões. A interface usa a interseção dos pares com observado e ambas as referências, incluindo a interseção dos primeiros 24 passos dos modelos. Os detalhes informam emissões usadas/disponíveis, número de pares, alvos e cobertura. Os serviços também suportam estatísticas independentes, identificadas como não pareadas. Não se presume comparabilidade quando não há emissões comuns.

Os segmentos usam o **passo inteiro 1–48**, enquanto `lead_hour` preserva as horas efetivamente decorridas desde t₀, que podem ser fracionárias. Uma previsão de 48h nunca é tratada como uma execução independente do modelo de 24h.

Com resíduo `r = observado − previsto`:

- MAE = média de `|r|`, na unidade da carga.
- RMSE = raiz da média de `r²`, na unidade da carga.
- MAPE = `100 × média(|r / observado|)`, em %, excluindo apenas observados iguais a zero.

Zeros continuam em MAE/RMSE; o número excluído do MAPE aparece nos detalhes de amostra. Valores positivos próximos de zero permanecem no MAPE e podem aumentar seu percentual: não há epsilon ou corte arbitrário. MAPE é indisponível se todos os observados forem zero. Curvas por passo informam os pares próprios do MAPE. Sem pares, métricas ficam indefinidas, nunca zero. Cálculos evitam overflow nas médias/RMSE; MAPE que excede o limite numérico produz mensagem explicativa. Emissões sobrepostas não são amostras estatisticamente independentes.

Os perfis climáticos/calendário mostram associações descritivas, sem conclusão causal. Não substituem um protocolo de validação temporal. O grupo continua responsável por treinar e ajustar transformações apenas com dados permitidos, registrar fontes/versões e manter treino, validação e teste separados.

## Verificações e próximas integrações

A suíte inclui contratos, arquivos ausentes/inválidos, grade temporal, fontes isoladas, clima/calendário, baselines sem acesso ao futuro, métricas conhecidas, zeros, segmentos, fusos/nanossegundos, filtros e serialização Plotly. Os testes `AppTest` executam as três abas no runtime Streamlit e isolam as pastas reais dos arquivos particulares do grupo. Eles verificam troca de fonte/horizonte, comparação de conjuntos, integração sem clima/calendário e ausência de métricas inventadas.

Para integrar o trabalho dos colegas, padronizem os JSONs e partições, exportem a carga municipal compatível em MWmed, anexem meteorologia e calendário verificados e registrem as evidências no capítulo de Testes. A interface já consome esses arquivos sem reescrever as páginas.
