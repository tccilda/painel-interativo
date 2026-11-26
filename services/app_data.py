"""Contexto de leitura; o lote fornecido é mantido em memória sem cópias por sessão.

O bundle e o catálogo retornados devem ser tratados como somente leitura. A
assinatura inclui nomes, tamanhos e mtimes para invalidar a leitura após edição.
"""

from pathlib import Path
from stat import S_ISREG

import streamlit as st

from services import data_loader
from services.forecast_catalog import forecast_catalog
from services.geography_service import municipal_bundle


def has_model_files() -> bool:
    directory = data_loader.DATA_DIR
    patterns = (("predictions", "*.json"), ("historical", "*.csv"))
    return any(path.is_file() for folder, pattern in patterns for path in (directory / folder).glob(pattern))


def imported_config_path() -> Path:
    return data_loader.DATA_DIR / "imported" / "config.json"


def _signature(directory: Path, *, suffix: str | None = None, names: set[str] | None = None) -> tuple:
    """Fingerprint local inputs by path, size and nanosecond modification time."""
    try:
        paths = sorted(directory.iterdir())
    except FileNotFoundError:
        return ()
    except OSError as exc:
        return ((str(directory.resolve()), "unavailable", type(exc).__name__),)
    result = []
    for path in paths:
        if suffix is not None and path.suffix.lower() != suffix:
            continue
        if names is not None and path.name not in names:
            continue
        try:
            metadata = path.stat()
        except FileNotFoundError:
            # The loader will see the same missing-file state on a cache miss.
            continue
        except OSError as exc:
            result.append((str(path.resolve()), "unavailable", type(exc).__name__))
            continue
        if S_ISREG(metadata.st_mode):
            result.append((str(path.resolve()), metadata.st_size, metadata.st_mtime_ns))
    return tuple(result)


def _standard_signature(mode: str, data_directory: Path) -> tuple:
    if mode == "demo":
        directory = data_directory / "demo"
        return (
            _signature(directory, suffix=".json"),
            _signature(directory, names={"historical.csv", "weather.csv", "calendar.csv"}),
        )
    return tuple(
        _signature(data_directory / directory, suffix=suffix)
        for directory, suffix in (
            ("predictions", ".json"), ("historical", ".csv"),
            ("weather", ".csv"), ("calendar", ".csv"),
        )
    )


@st.cache_resource(show_spinner=False, max_entries=2)
def _load_imported(config_path: str, signature: tuple):
    from services.archive_loader import load_archive_bundle

    bundle = municipal_bundle(load_archive_bundle(Path(config_path)))
    return bundle, forecast_catalog(bundle)


@st.cache_data(show_spinner=False, max_entries=2)
def _load_standard(mode: str, data_directory: str, signature: tuple, loader_identity: int):
    """Cache small bundles and return independent copies to callers.

    The loader's identity also separates injected loaders during tests; the
    actual project path and mode remain part of every cache key. The loader is
    called through its normal public signature, preserving test overrides.
    """
    bundle = municipal_bundle(data_loader.load_data(mode))
    return bundle, forecast_catalog(bundle)


def load_app_context(mode: str):
    if mode == "provided":
        config = imported_config_path()
        return _load_imported(str(config.resolve()), _signature(config.parent))
    if mode not in ("demo", "real"):
        raise data_loader.DataLoadError("Modo de dados inválido; use 'demo', 'real' ou 'provided'.")
    directory = Path(data_loader.DATA_DIR)
    return _load_standard(
        mode, str(directory.resolve()), _standard_signature(mode, directory), id(data_loader.load_data),
    )
