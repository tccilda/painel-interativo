# Publicação do Monitor de Previsão no Streamlit Community Cloud

O catálogo regional **ONS Sudeste/Centro-Oeste** é a fonte padrão. Em um checkout limpo, as três abas usam os dados compactos versionados, com métricas, série auditada, calendário e uma amostra real da V5. A cobertura aparece no Explorador. O commit estável e o roteiro de migração estão no [registro de consolidação](CONSOLIDACAO_2026-11-26.md).

## Configuração da demonstração acadêmica

| Campo | Valor |
| --- | --- |
| Repositório GitHub | `tccilda/painel-interativo` |
| Branch estável para publicação | `main` |
| Arquivo principal | `streamlit_app.py` |
| Python | 3.13 em **Advanced settings** |
| Dependências | `requirements.txt` |
| Demonstração sintética | `ENERGY_FORECAST_ALLOW_DEMO` ausente ou falsa |
| Configuração de dados externos | Dispensável para a amostra. Necessária para o acervo completo |

A pessoa responsável pelo app deve confirmar permissão para implantar a branch na organização, visibilidade e endereço efetivos. Para um app já existente, confirme a branch associada e o commit em execução. Registre a URL efetiva após verificar o acesso do público autorizado. O subdomínio histórico `energy-forecast-tcc` era uma sugestão do plano inicial. [Instruções oficiais de implantação](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## Homologação em aplicativo paralelo

| Campo | Candidato em revisão | Depois da consolidação aprovada |
| --- | --- | --- |
| Repositório | `tccilda/painel-interativo` | Mesmo repositório |
| Branch | `docs/metodologia` durante a revisão, ou `dev` após o merge do candidato | `main`, após a promoção |
| Entrada e ambiente | `streamlit_app.py`, Python 3.13 | Mesma entrada e versão |
| Dados | Somente a amostra V5 incluída no checkout | Amostra V5, com acervo integral opcional |
| Endereço | Subdomínio exclusivo de homologação | Validar disponibilidade do endereço definitivo na janela de troca |

1. Registre SHA, PR, duas execuções aprovadas na matriz Windows/Ubuntu, responsável pela homologação e janela de teste. Use o checkout limpo abaixo para conferir pacote e rotas antes de implantar.
2. No workspace `tccilda`, confirme acesso administrativo e autorização do GitHub para o Streamlit. Crie um app separado com as coordenadas acima, confira o subdomínio disponível e mantenha os ajustes de dados externos e de demonstração ausentes. A amostra versionada é suficiente para a banca. [Acesso ao GitHub pelo Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account) · [Implantação](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
3. Compare a origem exibida nos logs e o commit da branch candidata. Registre URL efetiva, commit, data, Python, conclusão dos testes abaixo e nome de quem homologou.
4. Em sessão sem login, confirme carregamento e as três abas. No Explorador, alterne as hipóteses, 24 h e 48 h, e emita consultas de 2025 e retrospectiva 2026. Confira a identificação de 1.420 emissões em 22 meses quando descrita para toda a amostra e a contagem do recorte selecionado. Exercite a exportação de uma emissão.
5. Em Desempenho, confira redução visível, sinal, N/D, sensibilidade e pares comuns. Valide o caso de Ano-Novo de 48 h UTC. Em Sazonalidade, confira dupla escala, datas civis distintas, calendário raro e rótulo regional. Registre erros de carregamento, renderização ou acesso no checklist.
6. Promova `dev` por PR com merge convencional após homologação do candidato, revisão do grupo e CI verde. Confirme o SHA de `main`, repita os testes essenciais e sincronize `dev` sem reescrever histórico. A aprovação técnica não encerra as pendências científicas descritas em [Pendências do grupo](PENDENCIAS_GRUPO.md). Antes de apresentar os resultados, o grupo deve aceitar a delimitação acadêmica e explicitar as pendências.
7. Preserve a publicação ativa durante a homologação. Se houver troca de endereço, valide o acesso e o commit no novo app durante a janela acordada. Mantenha o endereço paralelo como alternativa e deixe a publicação anterior disponível até confirmar a substituição. A troca de branch ou repositório exige nova implantação. Crie um app separado para manter o anterior acessível durante a migração. [Mudança de coordenadas no Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)

### Registro de homologação

| Campo | Registro |
| --- | --- |
| Branch e commit candidato | Preencher com o SHA efetivamente testado |
| URL paralela e visibilidade | Registrar após verificar o acesso |
| Resultado das três rotas e do roteiro de dados | Em aberto até as verificações no Community Cloud |
| Aceite do grupo e data | Em aberto |
| Plano de troca e contingência | Manter app ativo até validar a substituta |

## Previsões completas V1 e V5

1. Confirme a autorização de distribuição dos arquivos derivados. A configuração atual usa acesso HTTPS aos objetos sem cabeçalho de autenticação personalizado. Se o grupo exigir acesso privado com autenticação adicional, defina essa integração antes da distribuição.
2. Disponibilize sob um mesmo prefixo HTTPS o `index.json` e as 88 partições Parquet, conforme o [inventário da integração](INTEGRACAO_VERSOES.md#hospedagem). Acrescente o `painel.zip` caso a distribuição da V1 também tenha sido autorizada. Use os nomes do índice e mantenha os CSVs grandes fora do Git.
3. Em **Advanced settings → Secrets**, informe a URL base e o SHA-256 do índice para o pacote escolhido. Use as chaves no nível superior e deixe `ENERGY_FORECAST_DETAIL_DIR` ausente na nuvem quando o acervo estiver em HTTPS. [Configuração de segredos no Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

```toml
ENERGY_FORECAST_DETAIL_URL = "https://<endereco-aprovado>/<prefixo-do-pacote>"
ENERGY_FORECAST_DETAIL_SHA256 = "<sha256-do-index.json-publicado>"
```

Caso o destino sirva apenas a V5 integral, acrescente `ENERGY_FORECAST_DETAIL_HAS_LEGACY = false`. O painel conserva as métricas agregadas da V1 e só oferece o detalhe V1 onde o ZIP legado está configurado.

4. Verifique pelo app hospedado uma emissão V5 de 24 h e uma de 48 h fora da amostra e as duas hipóteses. Se o ZIP legado estiver configurado, teste também uma emissão V1. Confira a exportação, os gráficos e os logs. O serviço busca o índice, a partição selecionada e, quando solicitado, o ZIP V1. Cada artefato remoto é confrontado com seu SHA-256.
5. Para voltar à amostra V5, retire as duas chaves da fonte HTTPS e reinicie o app. A indisponibilidade de uma fonte remota já configurada produz aviso de erro, de forma que a amostra não pareça uma consulta integral bem-sucedida.

## Verificação em checkout limpo

```sh
python -m pip install -r requirements-dev.txt
python -m pip check
python scripts/check_public_bundle.py --git-index
python -m services.demo_data
python -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
python scripts/smoke_startup.py
```

As fixtures são geradas somente para testes. O smoke verifica HTTP e as três rotas. Os testes de integração exercitam a interface, a amostra do checkout e a leitura seletiva da fonte HTTPS simulada. O CI em Ubuntu e Windows valida o código, enquanto a execução no Community Cloud requer a verificação do endereço e dos dados configurados naquele app.

## Leitor municipal

A amostra e o acervo integral desta entrega são regionais. A pesquisa com alvo municipal continua pendente de uma série comprovadamente municipal, com fonte, unidade, fuso e autorização de uso registrados. Um eventual pacote municipal deve ser validado conforme os [contratos de integração](INTEGRACAO_MODELOS.md). Clima e calendário do Rio servem como contexto do catálogo regional.
