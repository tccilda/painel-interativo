# Homologação final do Monitor de Previsão

## Estado da entrega

| Dimensão | Estado verificado |
| --- | --- |
| Software | Validado localmente em Windows com a amostra pública. Branch `docs/metodologia` destinada à revisão do grupo em `dev`. |
| Publicação | [Endereço em uso no repositório anterior](https://monitor-de-previsao-tcc.streamlit.app/). Na consulta de 27/11/2026, o Streamlit mostrou a página de app adormecido. O acesso administrativo ao Community Cloud não estava autenticado no navegador disponível. URL paralela e nova publicação oficial pendentes. |
| Metodologia | Proveniência regional e resultados exportados verificados no recorte indicado. Delimitação na monografia, hipótese oficial, posição e latência da carga e reprodução do treinamento dependem de evidência ou decisão do grupo. |

Em 27/11/2026, a `main` oficial estava em `26bd008` e a `dev` em `c0376f7`. O commit final, a tag e o endereço oficial do novo repositório ficam para depois da revisão e da homologação na nuvem. O SHA da branch de metodologia é verificável no GitHub. Após o merge dessa branch, registre o SHA exato de `dev` usado na homologação paralela.

## Histórico

| Entrega | Evidência |
| --- | --- |
| Consolidação da versão estável | [PR #1](https://github.com/tccilda/painel-interativo/pull/1), merge `26bd008` |
| Amostra pública ampliada | [PR #2](https://github.com/tccilda/painel-interativo/pull/2), merge `8f9ab78` |
| Acabamento da interface | [PR #3](https://github.com/tccilda/painel-interativo/pull/3), merge `fcb7b09` |
| Resultados científicos | [PR #4](https://github.com/tccilda/painel-interativo/pull/4), merge `c0376f7` |
| Fundamentação e preparação da versão final | [Branch docs/metodologia](https://github.com/tccilda/painel-interativo/tree/docs/metodologia), revisão do grupo pendente |

## Verificação local de 27/11/2026

- **514 testes aprovados** na execução integral em Windows, Python 3.13.14, com avisos de sintaxe e depreciação tratados como erros. A suíte cobre interface, filtros, referências, Ano-Novo, exportações, datas civis e os cartões de redução, inclusive valores negativos e N/D.
- Inicialização HTTP 200 nas três rotas. Dependências e seleção do pacote público aprovadas. A amostra V5 preserva **1.420 emissões reais**, 51.120 passos, 22 meses e 88 partições. Os dados, manifestos e contratos científicos ficaram idênticos aos da `dev`.
- A auditoria reproduziu **72 MAEs em 24 recortes** lendo as 88 partições do acervo V5 local. A contagem de pares e de pares MAPE de cada recorte coincide com os agregados publicados.
- O navegador percorreu as três abas em 1366 × 768, 1920 × 1080 e 2560 × 1440 sem rolagem horizontal da página. Na retrospectiva de 2026, alternou 24 h e 48 h, o mês, a data e a hora. O CSV exportado para a origem local de 22/10/2026 às 06:00, hipótese UTC, conservou 48 linhas com passos 1–48, unidade MWmed e identificador `ONS_SECO_piloto`.
- Em Desempenho, o teste de 2025 sob a hipótese São Paulo, 24 h, apresentou reduções de 46,58% e 80,38% nos cartões. A tabela de sensibilidade abriu e o caso de Ano-Novo de 48 h sob UTC exibiu 48 alvos comuns e o maior erro de 7.838,44 MWmed. Em Sazonalidade, o calendário exibiu 24.837 de 24.840 horas esperadas, datas civis e os registros raros.
- Medição indicativa em uma sessão local aquecida. Tempo do clique até o primeiro gráfico visível entre **0,23 e 0,66 s** nas nove navegações observadas. Após o roteiro, o processo Streamlit apresentou **190,0 MiB residentes**, com pico residente de **242,5 MiB** e **646,1 MiB de memória privada**. As medições não incluem rede, execução a frio, concorrência ou limites da nuvem.

## Homologação no Community Cloud

A documentação oficial trata organização, repositório, branch e entrada como coordenadas da implantação. A migração será por um app separado. Preserve o endereço em uso até o aceite da substituta. [Procedimento oficial para mudança de origem](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)

1. Após aprovação e merge da metodologia, registre o SHA de `dev` e mantenha o candidato congelado. Confirme a CI desse SHA em Windows e Ubuntu.
2. Uma pessoa com administração do repositório e acesso ao workspace `tccilda` entra no [Community Cloud](https://share.streamlit.io/). Em **Create app**, selecione **Deploy a public app from GitHub**. Informe `tccilda/painel-interativo`, branch `dev`, e entrada `streamlit_app.py`. Em **Advanced settings**, selecione Python 3.13. Use um subdomínio paralelo disponível e deixe as fontes externas e a demonstração sintética sem configuração. Se o GitHub negar acesso, o proprietário da organização deve tratar a autorização pelo fluxo oficial. [Acesso ao GitHub](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account)
3. Confira coordenadas, build e SHA associado ao candidato, registre URL e horário, e faça o [roteiro de homologação](DEPLOY_STREAMLIT.md#homologação-em-aplicativo-paralelo) em sessão sem login e em diferentes resoluções. Registre tempo até renderizar em sessão fria e aquecida e consumo de memória quando a plataforma expuser telemetria. Anote qualquer limitação de medição.
4. Com revisão do grupo, CI e homologação aprovadas, abra PR de `dev` para `main` com merge convencional. Verifique o SHA pós-merge, sincronize `dev` por fast-forward e repita os testes. Registre a tag só após decisão do grupo. Faça um novo deploy a partir da `main` oficial e repita as verificações públicas. A troca de endereço aguarda confirmação do novo app.

| Evidência na nuvem | Registro |
| --- | --- |
| SHA candidato, URL paralela, Python e logs | Pendente de acesso administrativo e revisão do grupo |
| Testes em sessão sem login, latência e memória do app paralelo | Pendente de implantação |
| SHA final, tag, URL definitiva e aceite | Pendente de promoção e nova homologação |

## Funcionalidades e limites

As três abas cobrem previsões V5 de 24 h e 48 h, recortes das versões V1–V5, comparação com referências, sensibilidade ao carimbo, estudo de Ano-Novo, sazonalidade, clima, calendário e exportação. A amostra pública é seletiva. A consulta integral na nuvem é complementar e depende de autorização para distribuição. Alguns controles nativos do Streamlit seguem a configuração do navegador.

A carga é regional e os dados de clima e calendário no Rio têm alcance local. A verificação de saídas descreve erro retrospectivo e fornece evidência para o painel. A capacidade operacional, o uso de atributos na emissão e a ausência de vazamento no treinamento exigem auditoria própria. [Metodologia](METODOLOGIA_CIENTIFICA.md) · [Pendências do grupo](PENDENCIAS_GRUPO.md)

## Contingência para a banca

Em um checkout do SHA revisado, instale previamente as dependências, preserve a amostra versionada e rode o aplicativo localmente. Para apresentação sem internet, teste a mesma máquina com a rede desconectada antes da banca. Os cartões, métricas e partições da amostra já acompanham o projeto. Guarde em separado os CSVs de demonstração e o [roteiro de perguntas](QUESTOES_BANCA.md).

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Abra [o painel local](http://127.0.0.1:8501/) e apresente a retrospectiva, os cartões, o estudo de caso e o calendário. Confira previamente se as variáveis `ENERGY_FORECAST_DETAIL_*` e `ENERGY_FORECAST_ALLOW_DEMO` estão ausentes no ambiente da apresentação amostral.
