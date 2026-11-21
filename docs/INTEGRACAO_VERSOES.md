# Evolução experimental V1–V5

O catálogo é a fonte padrão. O alvo é ONS_SECO_piloto, carga do ONS Sudeste/Centro-Oeste em MWmed. O RJ entra como contexto acadêmico. A série não mede a carga municipal. V5 é a versão padrão. As três páginas originais permanecem. Em um clone limpo, a amostra de 12 emissões reais do manifesto permite abrir 24h e 48h nas três etapas e nas duas hipóteses.

- **Explorador:** V5 consulta uma emissão por cenário, etapa, horizonte, estimador e data/hora. V1 conserva a leitura do pacote legado e o carimbo interpretado apenas para exibição. Para V2–V4, o painel explica a disponibilidade exclusivamente agregada.
- **Desempenho:** os CSVs consolidados fornecem V1–V4 e o piloto histórico. Os CSVs V5 fornecem a versão atual. O painel separa estimadores selecionados, alternativas, pilotos e referências. As métricas por hora ou mês civil referem-se ao alvo. A tabela V4 × V5 usa o CSV de pares comuns e calcula as variações relativas de MAE e RMSE sobre o valor V4 nesse mesmo conjunto.
- **Episódios de erro:** ative a consulta no painel recolhível. A V5 lê apenas o estimador e o bloco de um mês de emissão. A V1 usa o leitor do ZIP legado nas etapas com detalhe. Os filtros de dia da semana, calendário e temperatura referem-se ao alvo. A temperatura observada no alvo serve para descrever o erro retrospectivo. Na hospedagem com a amostra, os episódios representam as emissões amostradas e o controle identifica essa cobertura.
- **Sazonalidade:** usa a série auditada V5 por hipótese de horário, estações A621 e A601 e eventos pela chave de cenário e ID. As pendências aparecem separadas e não alteram a grade. O calendário administrativo e subnacional tem alcance declarado nos eventos.

## Preparar a consulta local

Instale as dependências atualizadas. Na raiz, execute:

```powershell
.\scripts\setup_local.bat
.\.venv\Scripts\python.exe scripts/prepare_model_versions.py "C:\caminho\drive-download-20261121T002429Z-1-001.zip"
.\scripts\run_local.bat
```

O preparo verifica SHA-256 dos CSVs de previsão contra o manifesto original. Abre um CSV por vez em diretório temporário, lê lotes de 80 mil linhas, valida identidade, unidade, passos 1…H, UTC e distância origem–alvo e cria partições por cenário, etapa, horizonte e mês civil de emissão. Depois verifica duplicatas e completude por emissão. Reserve espaço em disco para o CSV de 48 h (~1,34 GB), o ZIP de entrada e a camada derivada (~95 MB nesta entrega, incluindo o legado). O original fica intacto. O índice é publicado no diretório somente após o processamento das partições e do legado.

O checkout já inclui os arquivos compactos em data/versions: manifestos, métricas, comparação, série e calendário; não é preciso repetir sua preparação. Para atualizar esses arquivos deliberadamente, use o mesmo comando com --small e revise os manifestos e a auditoria do pacote antes do commit. O comando principal gera data/versions/detail/ (ignorado pelo Git). Para uma atualização de detalhe, gere em um novo diretório com --detail-dir e aponte ENERGY_FORECAST_DETAIL_DIR para ele após validar. Faça uma nova execução do processo ao trocar os arquivos compactos. O modo legado lê um ZIP separado com os seis CSVs originais.

## Hospedagem

Use streamlit_app.py na raiz e Python 3.13. As tabelas e a série auditada funcionam com os arquivos versionados. Para ampliar o Explorador da amostra para a coleção integral e habilitar o detalhe V1, disponibilize o diretório derivado em armazenamento HTTPS aprovado. Sirva index.json, os arquivos Parquet e painel.zip com os mesmos nomes. Defina no ambiente do servidor:

- ENERGY_FORECAST_DETAIL_URL com a URL HTTPS base, sem credenciais na URL.
- ENERGY_FORECAST_DETAIL_SHA256 com o SHA-256 do index.json impresso pelo preparador.

O pacote local conferido tem **90 objetos e 94.804.266 bytes**: um índice de 30.217 bytes, 88 partições V5 (44 por horizonte, 6.518.880 linhas no total) e um ZIP V1 de 23.123.073 bytes. A maior partição tem 1.144.124 bytes. O SHA-256 do índice desta cópia é `b4781dbcefa4b70acafd9c95499412fb39d4f199ccbc538cb7ea0293759efdbf`. Use o hash dos bytes efetivamente publicados se o índice for regenerado. Os nomes de cada partição constam em `partitions[].file`.

O carregador precisa receber o conteúdo original de cada objeto por GET HTTPS sem credenciais na URL. Links de compartilhamento que devolvem uma página HTML não substituem esses arquivos. Consulte o [roteiro de configuração e validação](DEPLOY_STREAMLIT.md#previsões-completas-v1-e-v5).

No Community Cloud, essas variáveis podem ser definidas no campo **Secrets** como chaves TOML de nível superior. O índice informa hashes e limites de cada partição. O painel só baixa a partição do mês/recorte consultado e confirma SHA-256 antes de abrir. O cache é temporário e pode ser reconstruído a partir dessa fonte após reinício. O ZIP legado só é buscado quando V1 é escolhida. Em instalações com arquivos locais montados, ENERGY_FORECAST_DETAIL_DIR substitui a URL. Sem detalhe integral configurado, o Explorador seleciona explicitamente a amostra V5 versionada. Essa amostra tem 432 alvos originais e ocupa cerca de 122 kB. Regere-a com `python scripts/prepare_model_versions.py --preview` após preparar o detalhe integral. As métricas não são recalculadas a partir da amostra.

## Interpretação

O carimbo bruto V1 não tem fuso oficial documentado. V2–V5 mantêm as hipóteses UTC e São Paulo com igual estatuto. A interface não combina V1 com essas hipóteses em uma curva pareada. As emissões V5 são retrospectivas sobre snapshots fechados. Cenário, etapa, bloco, estimador e denominadores fazem parte do recorte. Diferença entre globais independentes não é efeito pareado. Apenas a tabela fornecida de pares comuns sustenta a comparação V4 × V5. Os alvos se repetem entre emissões e os resultados não demonstram desempenho operacional futuro.

Em testes, gerar fixtures sintéticas apenas para a suíte histórica. Os testes do catálogo usam os agregados reais e pequenas partições temporárias criadas para verificar o contrato da interface; esses dados de teste não são distribuídos na hospedagem.
