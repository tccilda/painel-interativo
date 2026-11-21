"""Seleção pública e integridade de fixtures sem depender dos dados particulares."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.check_public_bundle import (
    DEMO_FILENAMES, DEMO_MANIFEST, REQUIRED_PUBLIC_FILES, check_demo_manifest, check_public_bundle,
)


def public_files(root: Path) -> list[str]:
    for name in REQUIRED_PUBLIC_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture pública\n", encoding="utf-8")
    return list(REQUIRED_PUBLIC_FILES)


def demo_manifest(root: Path) -> Path:
    content = "fixture sintética\nsegunda linha\n".encode()
    entries = []
    for name in DEMO_FILENAMES:
        relative = f"data/demo/{name}"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        entries.append({"path": relative, "nature": "synthetic", "bytes_lf": len(content), "sha256_lf": hashlib.sha256(content).hexdigest()})
    manifest = root / DEMO_MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"schema_version": 1, "nature": "synthetic", "normalization": "crlf_to_lf_only", "files": entries}), encoding="utf-8")
    return manifest


def test_runtime_can_be_structurally_ready_without_claiming_real_data(tmp_path):
    report = check_public_bundle(tmp_path, public_files(tmp_path))
    assert report.ok and report.selected_files == len(REQUIRED_PUBLIC_FILES)
    assert report.demo_verified_files == 0


def test_missing_runtime_file_in_selection_or_on_disk_is_reported(tmp_path):
    paths = public_files(tmp_path)
    paths.remove("services/data_loader.py")
    (tmp_path / "requirements.txt").unlink()
    report = check_public_bundle(tmp_path, paths)
    assert any("fora da seleção" in error and "data_loader.py" in error for error in report.errors)
    assert any("ausente" in error and "requirements.txt" in error for error in report.errors)


@pytest.mark.parametrize("name", [
    ".env", ".env.production", "private.env", "configs/development.env",
    ".streamlit/secrets.toml", ".streamlit/secrets.production.toml", ".streamlit/secrets.test.toml",
    "credentials.json", "credentials-service.json", "credentials2.json",
    "service_account.json", "private.pem", "id_rsa", "logs/run.log",
])
def test_secret_names_are_rejected_without_reading_contents(tmp_path, name, monkeypatch):
    paths = public_files(tmp_path)
    secret = tmp_path / name
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("DO_NOT_LEAK_SECRET_VALUE", encoding="utf-8")
    def do_not_read(_):
        raise AssertionError("O verificador não deve ler conteúdo de segredos")
    monkeypatch.setattr(Path, "read_bytes", do_not_read)
    report = check_public_bundle(tmp_path, paths + [name])
    assert not report.ok
    assert "DO_NOT_LEAK_SECRET_VALUE" not in json.dumps(asdict(report))
    assert any("Não publicável" in error for error in report.errors)


@pytest.mark.parametrize("folder", ["historical", "predictions", "weather", "calendar", "imported"])
def test_private_dataset_directories_are_never_in_public_selection(tmp_path, folder):
    paths = public_files(tmp_path)
    name = f"data/{folder}/base.csv"
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_text("dados particulares", encoding="utf-8")
    assert not check_public_bundle(tmp_path, paths + [name]).ok
    placeholder = path.parent / ".gitkeep"
    placeholder.write_text("", encoding="utf-8")
    assert check_public_bundle(tmp_path, paths + [f"data/{folder}/.gitkeep"]).ok


@pytest.mark.parametrize("name", [
    "artifacts/auditoria.md", "artifacts/evidencia.jpg", ".venv-ci/pyvenv.cfg",
    ".venv313/Scripts/python.exe", "build/bundle.zip", "dist/site.zip",
])
def test_forced_local_evidence_environment_and_build_artifacts_are_rejected(tmp_path, name):
    paths = public_files(tmp_path)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("artefato local", encoding="utf-8")
    report = check_public_bundle(tmp_path, paths + [name])
    assert not report.ok
    assert any("Não publicável" in error and name in error for error in report.errors)


def test_demo_publication_is_refused_even_when_local_fixtures_are_verified(tmp_path):
    paths = public_files(tmp_path)
    demo_manifest(tmp_path)
    report = check_public_bundle(tmp_path, paths + ["data/demo/historical.csv"], include_demo=True)
    assert not report.ok and report.demo_verified_files == 23
    assert any("dataset sintético" in error for error in report.errors)


def test_demo_is_optional_and_verification_preserves_all_bytes(tmp_path):
    paths = public_files(tmp_path)
    assert check_public_bundle(tmp_path, paths).ok
    demo_manifest(tmp_path)
    originals = {name: (tmp_path / "data/demo" / name).read_bytes() for name in DEMO_FILENAMES}
    report = check_public_bundle(tmp_path, paths, include_demo=True)
    assert report.ok and report.demo_verified_files == 23
    assert originals == {name: (tmp_path / "data/demo" / name).read_bytes() for name in DEMO_FILENAMES}


def test_demo_lf_crlf_equivalence_changes_only_line_endings(tmp_path):
    demo_manifest(tmp_path)
    path = tmp_path / "data/demo/historical.csv"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert check_demo_manifest(tmp_path) == (23, [])
    path.write_bytes(path.read_bytes().replace(b"segunda", b"terceira"))
    verified, errors = check_demo_manifest(tmp_path)
    assert verified == 22 and any("divergente" in error for error in errors)


def test_demo_missing_file_and_corrupt_manifest_are_reported(tmp_path):
    assert check_demo_manifest(tmp_path)[0] == 0
    manifest = demo_manifest(tmp_path)
    (tmp_path / "data/demo/weather.csv").unlink()
    assert any("ausente" in error for error in check_demo_manifest(tmp_path)[1])
    manifest.write_text("not json", encoding="utf-8")
    assert check_demo_manifest(tmp_path)[0] == 0


@pytest.mark.parametrize("path", ["../outside.py", "/absolute.py", "C:\\Users\\example\\private.py", "C:relative.py", "data/../../private.py"])
def test_absolute_and_traversal_paths_are_rejected_portably(tmp_path, path):
    report = check_public_bundle(tmp_path, public_files(tmp_path) + [path])
    assert not report.ok and any("Caminho absoluto ou traversal" in error for error in report.errors)


def test_manifest_path_traversal_is_rejected_before_reading_outside(tmp_path):
    manifest_path = demo_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../private-secret.txt"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert any("traversal" in error for error in check_demo_manifest(tmp_path)[1])


def test_git_index_selects_committed_names_not_private_untracked_files(tmp_path):
    if not shutil.which("git"):
        pytest.skip("Git não disponível neste ambiente")
    public_files(tmp_path)
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", *REQUIRED_PUBLIC_FILES], check=True)
    (tmp_path / ".env").write_text("PRIVATE_UNTRACKED_VALUE", encoding="utf-8")
    report = check_public_bundle(tmp_path)
    assert report.ok and report.selection == "git_index"
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", ".env"], check=True)
    report = check_public_bundle(tmp_path)
    assert not report.ok and "PRIVATE_UNTRACKED_VALUE" not in json.dumps(asdict(report))
