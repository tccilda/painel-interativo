# Publicação do Monitor de Previsão no Streamlit Community Cloud

O catálogo regional **ONS Sudeste/Centro-Oeste** é a fonte padrão. Em um checkout limpo, as três abas usam os dados compactos versionados, com métricas, série auditada, calendário e 12 emissões reais da V5. A amostra permite demonstrar as duas hipóteses de horário, os dois horizontes e as três etapas. A cobertura da amostra aparece no filtro de mês.

## Configuração da demonstração acadêmica

| Campo | Valor |
| --- | --- |
| Repositório GitHub | `tccilda/painel-interativo` |
| Branch para demonstração | `dev` |
| Arquivo principal | `streamlit_app.py` |
| Python | 3.13 em **Advanced settings** |
| Dependências | `requirements.txt` |
| Demonstração sintética | `ENERGY_FORECAST_ALLOW_DEMO` ausente ou falsa |
| Configuração de dados externos | Dispensável para a amostra. Necessária para o acervo completo |

A pessoa responsável pelo app deve confirmar permissão para implantar a branch na organização, visibilidade e endereço efetivos. Para um app já existente, confirme a branch associada e o commit em execução. Registre a URL efetiva após verificar o acesso do público autorizado. O subdomínio histórico `energy-forecast-tcc` era uma sugestão do plano inicial. [Instruções oficiais de implantação](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## Previsões completas V1 e V5

1. Confirme a autorização de distribuição dos arquivos derivados. A configuração atual usa acesso HTTPS aos objetos sem cabeçalho de autenticação personalizado. Se o grupo exigir acesso privado com autenticação adicional, defina essa integração antes da distribuição.
2. Disponibilize sob um mesmo prefixo HTTPS o `index.json`, as 88 partições Parquet e o `painel.zip` legado, conforme o [inventário da integração](INTEGRACAO_VERSOES.md#hospedagem). Use os nomes indicados pelo índice, sem incluir os CSVs grandes no Git.
3. Em **Advanced settings → Secrets**, informe a URL base e o SHA-256 do índice para o pacote escolhido. Use as chaves no nível superior e deixe `ENERGY_FORECAST_DETAIL_DIR` ausente na nuvem quando o acervo estiver em HTTPS. [Configuração de segredos no Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

```toml
ENERGY_FORECAST_DETAIL_URL = "https://<endereco-aprovado>/<prefixo-do-pacote>"
ENERGY_FORECAST_DETAIL_SHA256 = "<sha256-do-index.json-publicado>"
```

4. Verifique pelo app hospedado uma emissão V5 de 24 h e uma de 48 h fora da amostra, as duas hipóteses e uma emissão V1. Confira a exportação, os gráficos e os logs. O serviço busca o índice, a partição selecionada e, quando solicitado, o ZIP V1. Cada artefato remoto é confrontado com seu SHA-256.
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
