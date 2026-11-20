# Publicação no Streamlit Community Cloud

## Estado desta preparação

A branch `main` inclui o pacote acadêmico adotado pelo grupo. A aplicação abre com as três páginas e com as previsões fornecidas de 24h e 48h. A série de carga é regional, em MWmed, e serve como referência para o trabalho sobre o Rio de Janeiro.

## Parâmetros definidos

| Campo | Valor a utilizar |
|---|---|
| Repositório GitHub | `tccilda/painel-interativo` |
| Branch | `main`, após integrar a proposta |
| Main file path | `streamlit_app.py`, na raiz do repositório |
| Python version | **3.13**, selecionar em Advanced settings |
| Versão local efetivamente verificada | Python **3.13.14**, Windows x86-64 |
| Dependências da aplicação | `requirements.txt` |
| App URL desejada | `energy-forecast-tcc.streamlit.app`, se disponível |
| Visibilidade do aplicativo | Pública, sem autenticação do visitante |
| Secrets necessários | Nenhum no funcionamento atual |
| Demonstração | Desativada: `ENERGY_FORECAST_ALLOW_DEMO` ausente ou falsa |

A disponibilidade do subdomínio não foi consultada nem reservada. O repositório da organização é público. A visibilidade pública do aplicativo deve ser conferida separadamente nas configurações de compartilhamento.

`.python-version` documenta a série de Python para ferramentas locais. A seleção de Python na hospedagem é feita na interface de Advanced settings; não depender desse arquivo ou de um `runtime.txt` para configurá-la. As instruções seguem a [documentação oficial de deploy](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Ambiente e portabilidade

`requirements.txt` fixa Streamlit 1.67.0, Plotly 6.9.0, Pandas 2.3.3, NumPy 2.5.5 e tzdata 2026.6. O NumPy selecionado exige Python >=3.12; usar a série 3.13 testada. `requirements-dev.txt` inclui o runtime e Pytest 9.2.0, sem acrescentar Pytest à imagem de produção. Não há bibliotecas específicas de Windows nem pacotes `apt` necessários ao código atual, portanto não foi criado `packages.txt` vazio.

Os caminhos de dados partem de `Path(__file__)` e usam diretórios relativos à aplicação. Nenhum carregador depende de Downloads, OneDrive ou da conta Windows do desenvolvedor. O arquivo `.streamlit/config.toml` preserva cores, fonte e preferências visuais, sem fixar endereço ou porta que conflitem com o proxy da nuvem. Executar comandos sempre da raiz do repositório, conforme a [organização oficial de arquivos](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

Instalação de execução em ambiente limpo:

```sh
python -m venv .venv
# Linux:
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

No PowerShell, usar `.\.venv\Scripts\python.exe` no lugar de `.venv/bin/python`. O endereço local passado pela linha de comando é para desenvolvimento; na Community Cloud a plataforma inicia o servidor e define o acesso externo.

Não existe treinamento, download de séries extensas, geração de demonstração ou escrita obrigatória em disco no startup. A aplicação lê previsões prontas. `st.cache_data` evita repetir leitura/validação e catálogo das fontes padrão em filtros; o lote grande importado mantém `st.cache_resource`. As chaves incluem assinatura dos arquivos e a fonte. Reiniciar o servidor recria o cache a partir dos arquivos, sem perder dados científicos.

## Dados necessários e bloqueio atual

| Uso | Arquivos esperados pelo carregador existente | Situação |
|---|---|---|
| Previsões 24h/48h | `data/predictions/*.json`, nos [contratos de integração](INTEGRACAO_MODELOS.md) | Previsões do grupo também vêm no ZIP |
| Histórico, reais e referências | `data/historical/*.csv` | Carga regional no ZIP |
| Meteorologia municipal | `data/weather/*.csv`, estações verificadas | A621 e A601 no ZIP |
| Calendário | `data/calendar/*.csv`, datas/esferas/atos conferidos | Calendário informado pelo grupo no ZIP |
| Base acadêmica padrão | `data/imported/config.json` e ZIP | Incluída no Git com checksum e rótulo regional |
| Fixtures sintéticas | Geradas em `data/demo/`, 23 arquivos, cerca de 7,13 MiB | Somente desenvolvimento/testes, fora do Git público |

Para habilitar todas as análises reais, a carga deve cobrir os alvos e ao menos a janela de histórico e referência semanal; o clima/calendário devem abranger os intervalos analisados. Lacunas permanecem ausentes, com cobertura explícita. Não inventar observações para forecasts futuros nem substituir a validação sem detalhes por curvas artificiais. O formato e as regras temporais estão no [guia de integração](INTEGRACAO_MODELOS.md).

Antes de incorporar uma base futura, registrar fonte oficial/produtora, abrangência documentada, unidade, fuso, processamento temporal, natureza observada/previsão retrospectiva/forecast e permissão ou licença de redistribuição. Preservar modelos, versões e partições. Revisar o calendário e as estações. Criar exceções nominais no `.gitignore` somente para os arquivos aprovados; eles devem fazer parte do checkout da nuvem. Não remover globalmente a proteção das pastas privadas nem incluir arquivos particulares.

Não foi acrescentado um download externo de dados: não há fonte municipal autorizada fornecida para configurar. Quando o pacote correto chegar, sua inclusão e a auditoria científica serão uma etapa própria. A checagem `--require-municipal-data` sinaliza a pendência atual; ela deverá ser atualizada com verificação da fonte efetivamente aprovada, sem substituir essa auditoria por um rótulo `municipal`.

## Verificação antes de publicar

Em um checkout limpo, sem bases particulares:

```sh
python -m pip install -r requirements-dev.txt
python -m pip check
python scripts/check_public_bundle.py --git-index
python scripts/smoke_startup.py
# Somente para exercitar a ciência e a UI em testes:
python -m services.demo_data
python scripts/check_public_bundle.py --git-index --include-demo
python -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
# Esta etapa falha enquanto não houver uma base municipal aprovada:
python scripts/check_public_bundle.py --git-index --require-municipal-data
```

O gerador é uma etapa explícita de testes, não é executado pela aplicação e não substitui dados reais. Ele recusa sobrescrita por padrão. As fixtures são ignoradas pelo Git e têm manifesto de integridade com normalização textual de finais de linha. A demonstração da UI local só aparece ao habilitar explicitamente `ENERGY_FORECAST_ALLOW_DEMO=true` e selecioná-la na lateral; mesmo com essa variável, o padrão continua real.

O smoke verifica saúde e respostas HTTP das três rotas. AppTests verificam a execução das páginas, filtros, indicadores, Plotly e botões de exportação; testes de serviço conferem os bytes CSV e a ciência. Respostas HTTP 200 isoladas não comprovam os cálculos ou renderização WebGL. O workflow `.github/workflows/tests.yml` prepara a mesma verificação em Ubuntu e Windows, Python 3.13, após publicação autorizada. Não confundir o workflow preparado com uma execução Linux já concluída.

`.gitignore` exclui `.env`, segredos Streamlit, chaves, credenciais usuais, ambiente virtual, logs, evidências locais e datasets privados. O checker recusa esses nomes/locais no índice Git sem imprimir seu conteúdo; é uma auditoria estrutural, não uma garantia de detecção de todo segredo possível. Revisar o diff antes de cada commit. Não há necessidade de segredos no aplicativo atual.

## Implantação da prévia e atualização com dados

1. Use a branch `main` publicada. A base acadêmica já está no checkout. Para trocar a fonte futuramente, atualize a configuração e documente sua abrangência.
2. Valide mudanças em uma branch de trabalho e integre-as à `main` por revisão. O aplicativo recebe os commits da branch vinculada.
3. Em [share.streamlit.io](https://share.streamlit.io), entrar com a conta responsável, escolher **Create app** e informar o repositório, `main` e `streamlit_app.py`.
4. Informar o subdomínio `energy-forecast-tcc`, caso disponível. Em **Advanced settings**, selecionar Python **3.13**. Não inserir credenciais locais; o app atual não exige secrets. Manter a demonstração desativada.
5. Após autorização para publicar, acionar **Deploy** e acompanhar o build. O Cloud instala `requirements.txt` a partir do checkout; não enviar `.venv` nem arquivos temporários. Ver [dependências oficiais](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
6. Em **Settings → Sharing → Who can view this app**, selecionar **This app is public and searchable**. Conferir o acesso sem sessão autenticada em uma janela privada antes de compartilhar com o orientador. Ver [compartilhamento oficial](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
7. Verificar na nuvem as três abas, 24h/48h, emissão, datas, gráficos, origem/unidades, exportação e estados sem observado. Registrar a URL efetiva e o commit implantado. O endereço desejado ainda não é uma URL publicada.

Atualizações futuras chegam ao app ao enviar commits autorizados para a branch vinculada. Dados autorizados devem continuar disponíveis após reinícios. Alterar Python na Community Cloud exige nova implantação; manter registrada a versão escolhida e reexecutar os testes ao alterar dependências.

Se o build falhar, confira no log o Python escolhido e a resolução de `requirements.txt`. Se as páginas iniciarem vazias, confira os arquivos presentes no commit e a compatibilidade indicada no painel. Para recuperar uma versão anterior, proponha um commit de reversão ou correção na branch de trabalho, valide-o e integre-o pelo fluxo de revisão. Registre o SHA resultante e confirme o novo build.
