# Orientações de manutenção

## Escopo

- Destino oficial: tccilda/painel-interativo. Propostas partem da main oficial em branch de trabalho. Preservar autoria e histórico. Ver CONTRIBUTING.md e docs/EXECUCAO_LOCAL_WINDOWS.md.

- Aplicação Python/Streamlit/Plotly/Pandas/NumPy, local ou Streamlit Community Cloud; testes Pytest. Não adicionar banco, autenticação, FastAPI, Docker ou frameworks JavaScript sem nova decisão do grupo.
- O catálogo usa séries regionais. Preserve a distinção entre carga do ONS SE/CO e variáveis locais do Rio. Não criar remoto nem alterar visibilidade GitHub sem autorização explícita.
- Python alvo da hospedagem: 3.13 (local verificado 3.13.14). requirements.txt contém somente runtime; requirements-dev.txt acrescenta Pytest. .python-version é referência local, a versão Cloud deve ser selecionada em Advanced settings. Não fixar server.address/port no config versionado; manter bind127.0.0.1 em comandos de desenvolvimento.
- O catálogo experimental V1–V5 usa ONS SE/CO em MWmed. Manter V5 padrão e os artefatos volumosos fora do Git, conforme docs/INTEGRACAO_VERSOES.md. As regras municipais abaixo se aplicam exclusivamente ao leitor municipal legado.
- Manter o nome provisório e o subtítulo nas constantes `APP_NAME` e `APP_SUBTITLE` em `streamlit_app.py`. Manter exatamente três abas com `st.Page` e `st.navigation` e preservar seus `url_path`.
- Alvo efetivo da entrega: ONS_SECO_piloto, em MWmed. O leitor municipal opcional conserva a validação territorial.
- A revisão independente de 16/11/2026 comprovou que as 8.784 horas de 2024 do pacote b10830eaae44…f9d7 correspondem ao subsistema Sudeste/Centro-Oeste (`val_carga`, ONS), e A601 é Seropédica. Essa base está em quarentena para a visão municipal. Não remover o bloqueio por causa do rótulo declarado em config.json; não substituir o alvo por SE/CO nem trocar para demo silenciosamente. Ver services/geography_service.py e artifacts/revisao_auditoria_dados.md.
- `app_pages/`: apresentação e controles; `components/`: visuais; `services/`: carregamento/processamento/filtros/métricas; `contracts/`: validação independente. Usar funções pequenas, pathlib e mensagens PT-BR. Dependências diretas verificadas em requirements.txt.
- Manter layout compacto: quatro indicadores curtos no explorador, tabela de comparação com seis linhas na avaliação, textos em tooltips/Detalhes metodológicos, amostra e cobertura em expander. Ausências devem aparecer como N/D. CSVs preservam a precisão numérica original.
- Fonte adicional **Base do grupo (CSV)**: `archive_loader` lê uma cópia do ZIP em data/imported, validada por SHA-256 e metadados explícitos em config.json. Não alterar o original nem converter as 23.236 emissões em objetos/arquivos individuais; usar forecast_catalog e materializar somente a seleção. DataBundle e catálogo em cache são somente leitura.
- Município e fuso da base fornecida foram declarados pelo grupo; não apresentar isso como comprovação independente da fonte. Preservar essa procedência. Não exigir a presença do ZIP particular nos testes: usar fixtures temporárias.

## Integridade dos dados

- Preservar arquivos do usuário. Não sobrescrever dados reais para corrigir carregamento. Erros devem produzir avisos e estados vazios úteis.
- Isolar data/demo de predictions, historical, weather e calendar. Modo real nunca recorre à demonstração. A UI pública oculta demo por padrão; habilitar somente por ENERGY_FORECAST_ALLOW_DEMO=true explícito para teste/local e selecionar a fonte manualmente. Manter **Modo demonstração — dados sintéticos** e a identificação de carga, clima, calendário e métricas artificiais em todas as abas demo.
- data/demo/*.csv e *.json são fixtures ignoradas pelo Git, geradas explicitamente antes da suíte em checkout limpo, nunca no startup da aplicação. Manifesto em tests/fixtures/demo_manifest.json. Não incluir ZIP privado, datasets não autorizados, .env, secrets, chaves, logs ou artifacts locais no índice público. scripts/check_public_bundle.py verifica a seleção estrutural.
- Demonstração fixa 2024–2026; não deslocar emissões para o relógio atual nem alegar fontes reais. Gerar somente arquivos conhecidos com `python -m services.demo_data --overwrite`; nunca apontar o gerador a dados reais.
- Forecast exige 24/48 pontos únicos, ordenados, horários; primeiro alvo no intervalo (t₀,t₀+1h]. Preservar emissão, fuso original e nanossegundos; comparar UTC e mostrar America/Sao_Paulo.
- Aceitar MW/MWmed apenas como séries separadas. Unidade faz parte das chaves de observações e avaliações. Não converter ou misturar implicitamente.
- `dataset_split` deve ser declarado como validation_2025, test_2025, forecast_2026 ou unspecified. Não inferir teste/validação pelo ano nem certificar ausência de vazamento por esse rótulo.
- Histórico permite lacunas horárias inteiras, sem interpolação; validar grade e duplicatas também entre arquivos. Não escolher arbitrariamente observações conflitantes.
- Meteorologia: junção exata no alvo; na emissão, somente última leitura por estação até t₀, com defasagem máxima de 1h e limite no relógio atual. Identificar médias entre estações. Temperatura do alvo é contexto retrospectivo, nunca informação presumidamente conhecida em t₀.
- A visão municipal usa somente estações verificadas no município; A601 não compõe médias municipais. Agregações climáticas diária/semanal são visuais, preservam contagens e lacunas e não alteram modelos/métricas. Dispersão mantém os pares filtrados; opção horária limita a série temporal a 168h com indicação explícita.
- Calendário: somente classificações fornecidas/verificadas, dias locais completos no intervalo; não presumir feriado, ponto facultativo ou dia comum na ausência de classificação. Rejeitar datas duplicadas por região para não multiplicar observações.
- Pontos facultativos podem ter âmbito `nao_informado`; preservar ausência de esfera no ZIP. Meteorologia importada usa apenas A621/A601 brutas, sem tratar temp_rj preenchida como nova medição.
- Ocultar observações futuras em todas as abas. Baselines usam somente observações disponíveis até a emissão: persistência com tolerância de 1h; sazonal semanal no alvo−168h, sem preenchimento.

## Métricas e apresentação

- Avaliar correspondência exata de instante/região/unidade. Manter partições/modelos/segmentos separados. Na comparação, explicitar emissões comuns, amostra comum, cobertura, alvos e pares efetivamente usados.
- Segmentos 1–24/25–48/1–48 usam forecast_step inteiro, distinto da antecedência lead_hour, que pode fracionar. Não cortar 48h para simular o modelo de 24h.
- Resíduo = observado−previsto. MAPE exclui observados zero somente do MAPE; preservar zeros em MAE/RMSE, informar contagens e retornar indefinido sem pares. Nunca inventar precisão de 2026 sem observado correspondente.
- Positivos próximos de zero são mantidos no MAPE, sem epsilon arbitrário. Usar contagens próprias de pares válidos/excluídos ao mostrar MAPE por passo. comparison_verified diferencia pareamento entre horizontes comprovado de estatísticas descritivas; não apresentar amostras não pareadas como comparação verificada.
- Separar **métricas recalculadas dos pares** e **resumos fornecidos**. No ZIP legado V1, validação 1S2025 e pilotos não têm previsões detalhadas; não criar curvas ou episódios para esses agregados. Cobertura, alvos e contagens de zeros não verificáveis devem permanecer indisponíveis. Não importar o sinal do erro médio original como se fosse o resíduo do painel.
- Perfis, clima e calendário são associações descritivas, com contagens; não alegar causalidade ou generalização. Emissões sobrepostas não são amostras independentes.
- Plotly com unidades, hover, legenda, zoom e lacunas preservadas; dois eixos climáticos explicitam MWmed/°C. Não mostrar gráficos sem suporte nos dados. Interface acessível e responsiva, sem HTML não escapado vindo dos arquivos.

## Verificação

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# Somente em checkout sem as fixtures: python -m services.demo_data
.\.venv\Scripts\python.exe -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
.\.venv\Scripts\python.exe scripts/smoke_startup.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

- Testar comportamento científico e bordas relevantes, sem reproduzir a implementação. Testes não podem depender de pastas de pesquisa vazias ou modificar arquivos particulares do grupo.
- Alterações de contrato/carregamento/análise devem cobrir formatos inválidos, fusos, janelas, referências, zeros, unidades e partições. Mudanças em gráficos exigem serialização Plotly e inspeção quando afetam layout.
- Verificar três abas, 24h/48h, emissão retrospectiva e sem observado, dados reais vazios e integração sem clima/calendário.
- Reportar somente testes realmente executados. Atualizar README ao alterar contratos, instalação, convenções temporais ou uso.
- Executar também em cópia limpa dos arquivos públicos, sem bases particulares. O workflow Ubuntu/Windows preparado não comprova por si só que testes Linux foram executados; informar a diferença entre auditoria/wheels e execução real. A prévia distribuída deve conter somente emissões reais documentadas.
