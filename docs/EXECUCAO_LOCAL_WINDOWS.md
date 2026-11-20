# Execução local no Windows

Instale Git e Python 3.13. A versão testada é Python 3.13.14. Após a integração do painel à branch de produção, clone o repositório oficial:

```powershell
git clone https://github.com/tccilda/painel-interativo.git
cd painel-interativo
.\scripts\setup_local.bat
.\scripts\run_local.bat
```

Para revisar uma proposta antes da integração, use a cópia ou a branch de trabalho disponibilizada pelo grupo. O endereço padrão é http://127.0.0.1:8501. Pressione Ctrl+C no terminal para encerrar. A instalação pode acessar o índice de pacotes. A aplicação lê os arquivos locais disponíveis.

Os scripts localizam a raiz, aceitam caminhos com espaços e acentos e usam diretamente o Python da venv. Para atualizar dependências após receber uma mudança, execute novamente o setup. O script preserva a venv existente e informa se ela é incompatível.

### Comandos manuais

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Se o launcher py estiver ausente, confira a versão com python3.13 --version ou python --version e use o comando correspondente. Se a porta estiver ocupada, escolha outra para a sessão:

```powershell
$env:STREAMLIT_SERVER_PORT = '8503'
.\scripts\run_local.bat
```

### Testes e dados

Em uma cópia de testes sem fixtures, execute:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_public_bundle.py --git-index
.\.venv\Scripts\python.exe scripts/smoke_startup.py
.\.venv\Scripts\python.exe -m services.demo_data
.\.venv\Scripts\python.exe -m pytest -q -W error::DeprecationWarning -W error::SyntaxWarning
```

A versão distribuída abre com o pacote acadêmico regional. Se a fonte estiver ausente, as páginas informam a indisponibilidade. Para testar gráficos com dados sintéticos gerados na cópia de desenvolvimento, defina ENERGY_FORECAST_ALLOW_DEMO=true no ambiente antes de iniciar e selecione **Demonstração** manualmente. Consulte o [guia dos modelos](INTEGRACAO_MODELOS.md).
