"""Verifica a seleção pública do Git sem rede, publicação ou leitura de segredos.

O resultado confirma a estrutura do pacote, não sua prontidão científica.
Fixtures sintéticas locais podem ser conferidas separadamente com --include-demo;
elas continuam proibidas na seleção pública enquanto o produto usar só dados reais.
"""

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_MANIFEST = "tests/fixtures/demo_manifest.json"
DEMO_FILENAMES = (
    "calendar.csv", "historical.csv", "weather.csv",
    "forecast_backtest_24h.json", "forecast_backtest_48h.json",
    "forecast_future_24h.json", "forecast_future_48h.json",
    "forecast_validation_2025_06_24h.json", "forecast_validation_2025_06_48h.json",
    "forecast_test_2025_09_24h.json", "forecast_test_2025_09_48h.json",
    "forecast_test_2025_10_24h.json", "forecast_test_2025_10_48h.json",
    "forecast_test_2025_12_24h.json", "forecast_test_2025_12_48h.json",
    "forecast_forecast_2026_02_24h.json", "forecast_forecast_2026_02_48h.json",
    "forecast_forecast_2026_04_24h.json", "forecast_forecast_2026_04_48h.json",
    "forecast_forecast_2026_06_24h.json", "forecast_forecast_2026_06_48h.json",
    "forecast_forecast_2026_09_24h.json", "forecast_forecast_2026_09_48h.json",
)
REQUIRED_PUBLIC_FILES = (
    "streamlit_app.py", "requirements.txt", "README.md", ".gitignore", ".streamlit/config.toml",
    "app_pages/__init__.py", "app_pages/explorador.py", "app_pages/desempenho.py", "app_pages/sazonalidade.py",
    "components/__init__.py", "components/charts.py", "components/metrics_cards.py",
    "components/page_frame.py", "components/sidebar.py", "components/tables.py",
    "contracts/__init__.py", "contracts/forecast_schema.py", "services/__init__.py",
    "services/analysis_service.py", "services/app_data.py", "services/archive_analysis.py",
    "services/archive_loader.py", "services/data_loader.py", "services/forecast_catalog.py",
    "services/forecast_service.py", "services/geography_service.py", "services/history_service.py",
    "services/metrics_service.py", "services/pattern_service.py",
)
PRIVATE_DATA_DIRS = {"historical", "predictions", "weather", "calendar", "imported"}
PRIVATE_NAMES = {
    "secrets.toml", "secrets.json", "secrets.yaml", "secrets.yml", "credentials", "credentials.json",
    "credentials.yaml", "credentials.yml", "credential.json", "token.json", "tokens.json",
    "application_default_credentials.json", ".netrc", ".pypirc", ".envrc",
}


@dataclass
class PublicBundleReport:
    selection: str
    selected_files: int = 0
    selected_bytes: int = 0
    demo_verified_files: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _safe_path(root: Path, value: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Caminho selecionado inválido.")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts:
        raise ValueError(f"Caminho absoluto ou traversal recusado: {value!r}.")
    if not path.parts or path == PurePosixPath("."):
        raise ValueError("Caminho selecionado vazio.")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Caminho resolve fora da raiz escolhida: {value!r}.")
    return path.as_posix(), target


def _private_reason(path: str) -> str | None:
    parts = [part.casefold() for part in PurePosixPath(path).parts]
    name = parts[-1]
    if any(part == ".env" or part.startswith(".env.") for part in parts) or name.endswith(".env"):
        return "arquivo de ambiente/segredo"
    if name.startswith("secrets.") and name.endswith(".toml"):
        return "arquivo de segredos do Streamlit"
    if name.startswith("credentials") and name.endswith(".json"):
        return "nome usual de credencial/segredo"
    if name in PRIVATE_NAMES or name.startswith(("id_rsa", "id_ecdsa", "id_ed25519")):
        return "nome usual de credencial/segredo"
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore")):
        return "arquivo de chave/credencial"
    if name.endswith(".json") and "service" in name and "account" in name:
        return "credencial de conta de serviço"
    if len(parts) >= 3 and parts[0] == "data":
        if parts[1] in PRIVATE_DATA_DIRS and not (len(parts) == 3 and name == ".gitkeep"):
            return "dado local privado fora do pacote público"
        if parts[1] == "demo" and not (len(parts) == 3 and name == ".gitkeep"):
            return "dataset sintético excluído da versão pública com dados reais"
    if "artifacts" in parts[:-1]:
        return "evidência local excluída do pacote público"
    if any(part in {".git", "__pycache__", ".pytest_cache", "build", "dist"} or part.startswith(".venv") for part in parts[:-1]) or name.endswith((".pyc", ".pyo", ".log")):
        return "artefato local de ambiente/cache/log"
    return None


def git_index_paths(root: Path) -> list[str]:
    """Retorna apenas nomes rastreados no índice; não lê blobs ou segredos."""
    try:
        result = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "-z"], capture_output=True, check=False)
    except OSError as exc:
        raise ValueError("Git indisponível para consultar a seleção pública.") from exc
    if result.returncode:
        raise ValueError("Não foi possível consultar o índice Git da raiz escolhida.")
    return [value.decode("utf-8", errors="surrogateescape") for value in result.stdout.split(b"\x00") if value]


def check_demo_manifest(root: Path) -> tuple[int, list[str]]:
    """Confere fixtures locais; normaliza somente CRLF→LF, sem regravar nada."""
    errors = []
    try:
        _, path = _safe_path(root, DEMO_MANIFEST)
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return 0, [f"Manifesto das fixtures sintéticas indisponível ou inválido ({type(exc).__name__})."]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("nature") != "synthetic" or manifest.get("normalization") != "crlf_to_lf_only":
        return 0, ["Manifesto deve declarar schema_version=1, nature=synthetic e normalization=crlf_to_lf_only."]
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != len(DEMO_FILENAMES):
        return 0, ["Manifesto deve identificar exatamente as 23 fixtures sintéticas."]
    expected = {f"data/demo/{name}" for name in DEMO_FILENAMES}
    seen = set()
    verified = 0
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Entrada inválida no manifesto sintético.")
            continue
        try:
            relative, path = _safe_path(root, entry.get("path"))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if relative not in expected or relative in seen:
            errors.append(f"Fixture inesperada ou duplicada no manifesto: {relative}.")
            continue
        seen.add(relative)
        if entry.get("nature") != "synthetic" or not isinstance(entry.get("sha256_lf"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256_lf"]) or type(entry.get("bytes_lf")) is not int:
            errors.append(f"Metadados de fixture inválidos: {relative}.")
            continue
        try:
            data = path.read_bytes().replace(b"\r\n", b"\n")
            data.decode("utf-8")
        except (OSError, UnicodeError):
            errors.append(f"Fixture ausente ou inválida em UTF-8: {relative}.")
            continue
        if len(data) != entry["bytes_lf"] or hashlib.sha256(data).hexdigest() != entry["sha256_lf"]:
            errors.append(f"Conteúdo divergente do manifesto sintético: {relative}.")
        else:
            verified += 1
    if seen != expected:
        errors.append("O manifesto não cobre os 23 nomes esperados de fixtures sintéticas.")
    return verified, errors


def check_public_bundle(root: Path, selected_paths: Iterable[str] | None = None, *, include_demo: bool = False) -> PublicBundleReport:
    """Audita seleção explícita ou índice Git; não autoriza bases científicas."""
    root = Path(root).resolve()
    report = PublicBundleReport("git_index" if selected_paths is None else "explicit_paths")
    try:
        paths = git_index_paths(root) if selected_paths is None else list(selected_paths)
    except ValueError as exc:
        report.errors.append(str(exc))
        paths = []
    selected = set()
    for value in paths:
        try:
            relative, path = _safe_path(root, value)
        except (OSError, ValueError) as exc:
            report.errors.append(str(exc))
            continue
        if relative in selected:
            report.errors.append(f"Caminho duplicado na seleção: {relative}.")
            continue
        selected.add(relative)
        reason = _private_reason(relative)
        if reason:
            # Recusa pelo nome antes de abrir ou ler qualquer conteúdo.
            report.errors.append(f"Não publicável ({reason}): {relative}.")
            continue
        if not path.is_file():
            report.errors.append(f"Arquivo selecionado ausente: {relative}.")
            continue
        report.selected_bytes += path.stat().st_size
    report.selected_files = len(selected)
    for relative in REQUIRED_PUBLIC_FILES:
        if relative not in selected:
            report.errors.append(f"Arquivo necessário fora da seleção pública: {relative}.")
    if include_demo:
        report.demo_verified_files, errors = check_demo_manifest(root)
        report.errors.extend(errors)
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Auditar somente a seleção pública do Git; nenhuma publicação ou conexão de rede.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--git-index", action="store_true", help="Consultar o índice Git (seleção padrão).")
    parser.add_argument("--include-demo", action="store_true", help="Conferir também as fixtures sintéticas LOCAIS; não permite incluí-las no Git público.")
    args = parser.parse_args()
    report = check_public_bundle(args.root, include_demo=args.include_demo)
    print(json.dumps({"ok": report.ok, **asdict(report)}, ensure_ascii=True, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
