
"""Gera a camada de consulta por cenário, etapa, horizonte e mês civil."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SMALL = ROOT / "data" / "versions"
DETAIL = SMALL / "detail"
V5 = "entrega_painel_v5"
SCENARIOS = {"hipotese_UTC", "hipotese_Sao_Paulo"}
STAGES = {"validacao_1s2025", "teste_2025", "retrospectiva_2026"}
PAYLOAD = [
    "origem_t", "instante_alvo", "modelo", "passo_h", "eh_selecionado", "y_real", "y_pred",
    "y_baseline_semanal", "y_baseline_persistencia", "fim_de_semana", "eh_feriado",
    "eh_ponto_facultativo", "evento_versao_ids",
]
IDENTITY = {"alvo_id": "ONS_SECO_piloto", "unidade": "MWmed", "versao": "v5", "escopo_avaliacao": "retrospectiva_nao_cego"}
AGGREGATE_NAMES = ("globais", "por_passo", "por_hora", "por_mes")


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def manifest(nested, folder, filename):
    return json.loads(nested.read(f"{folder}/{filename}"))


def copy_checked(nested, folder, filename, metadata, target):
    with nested.open(f"{folder}/{filename}") as member, target.open("wb") as output:
        shutil.copyfileobj(member, output, length=1024 * 1024)
    if digest(target) != metadata["sha256"]:
        raise ValueError(f"SHA-256 divergente: {filename}")


def package_small(source):
    for archive, members in (
        ("metricas_versoes_anteriores", [f"metricas_{n}.csv" for n in AGGREGATE_NAMES] + ["disponibilidade_metricas.csv"]),
        (V5, [f"metricas_{n}_v5.csv" for n in AGGREGATE_NAMES] + [
            "comparacao_v4_v5_pares_comuns.csv", "serie_horaria_auditada_v5.csv",
            "eventos_calendario_v5.csv", "eventos_pendentes_v5.csv"
        ]),
    ):
        with source.open(archive + ".zip") as stream, ZipFile(stream) as nested:
            name = "MANIFESTO_v5.json" if archive == V5 else "MANIFESTO_metricas_versoes_anteriores.json"
            m = manifest(nested, archive, name)
            target = SMALL / archive
            target.mkdir(parents=True, exist_ok=True)
            (target / name).write_bytes(nested.read(f"{archive}/{name}"))
            for filename in members:
                copy_checked(nested, archive, filename, m.get("arquivos", m.get("saidas"))[filename], target / filename)
            if archive == V5:
                for doc in ("DICIONARIO_DADOS_v5.md", "INSTRUCOES_PAINEL_v5.md"):
                    (target / doc).write_bytes(nested.read(f"{archive}/{doc}"))


def chunks(csv_path, horizon):
    cols = [*PAYLOAD, *IDENTITY, "cenario", "etapa", "horizonte_h"]
    numeric = {k: "int64" for k in ("passo_h", "horizonte_h", "eh_selecionado", "fim_de_semana", "eh_feriado", "eh_ponto_facultativo")}
    numeric.update({k: "float64" for k in PAYLOAD if k.startswith("y_")})
    dtypes = {k: numeric.get(k, "string") for k in cols}
    for chunk in pd.read_csv(csv_path, usecols=cols, dtype=dtypes, chunksize=80_000, float_precision="round_trip"):
        for k, value in IDENTITY.items():
            if not chunk[k].eq(value).fillna(False).all():
                raise ValueError(f"Identidade inválida em {k}.")
        issue = pd.to_datetime(chunk["origem_t"], utc=True, errors="raise")
        target = pd.to_datetime(chunk["instante_alvo"], utc=True, errors="raise")
        if not (
            chunk["horizonte_h"].eq(horizon).all() and chunk["passo_h"].between(1, horizon).all()
            and chunk["modelo"].fillna("").str.fullmatch(r"[a-z0-9_]+").all()
            and chunk["cenario"].isin(SCENARIOS).all() and chunk["etapa"].isin(STAGES).all()
            and chunk["origem_t"].str.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ").fillna(False).all()
            and chunk["instante_alvo"].str.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ").fillna(False).all()
            and (target - issue).eq(pd.to_timedelta(chunk["passo_h"], unit="h")).all()
            and np.isfinite(chunk[[k for k in PAYLOAD if k.startswith("y_")]]).all().all()
            and all(chunk[k].isin((0, 1)).all() for k, kind in numeric.items() if kind == "int64" and k not in ("passo_h", "horizonte_h"))
        ):
            raise ValueError(f"Domínio, unidade, fuso ou grade inválida em {csv_path.name}.")
        chunk["month"] = issue.dt.tz_convert("America/Sao_Paulo").dt.strftime("%Y-%m")
        chunk["evento_versao_ids"] = chunk["evento_versao_ids"].fillna("")
        yield chunk


def build_horizon(csv_path, directory, horizon, expected_count):
    info = {}
    with ExitStack() as stack:
        count = 0
        for chunk in chunks(csv_path, horizon):
            count += len(chunk)
            for key, group in chunk.groupby(["cenario", "etapa", "month"], sort=False):
                if key not in info:
                    path = directory / f"{horizon}__{'__'.join(key)}.parquet"
                    table = pa.Table.from_pandas(group[PAYLOAD], preserve_index=False)
                    writer = stack.enter_context(pq.ParquetWriter(path, table.schema, compression="zstd"))
                    info[key] = (path, writer)
                path, writer = info[key]
                writer.write_table(pa.Table.from_pandas(group[PAYLOAD], preserve_index=False))
        if count != expected_count:
            raise ValueError(f"Contagem divergente para {horizon} h: {count} vs. {expected_count}.")
    for (scenario, stage, month), (path, _) in sorted(info.items()):
        keys = pd.read_parquet(path, columns=["modelo", "origem_t", "passo_h", "eh_selecionado"])
        if keys.duplicated(["modelo", "origem_t", "passo_h"]).any():
            raise ValueError(f"Passos duplicados em {path.name}.")
        counts = keys.groupby(["modelo", "origem_t"], sort=False).agg(
            rows=("passo_h", "size"), selected=("eh_selecionado", "nunique")
        )
        if not (counts["rows"].eq(horizon).all() and counts["selected"].eq(1).all()):
            raise ValueError(f"Emissão incompleta em {path.name}.")
        yield dict(file=path.name, sha256=digest(path), bytes=path.stat().st_size, horizon=horizon,
                   scenario=scenario, stage=stage, month=month, rows=len(keys))


def build(source, target):
    if (target / "index.json").exists():
        raise FileExistsError(f"Já existe um índice em {target}. Escolha outro diretório para atualizar.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temp, source.open(V5 + ".zip") as stream, ZipFile(stream) as nested:
        scratch = Path(temp)
        target.mkdir(exist_ok=True)
        meta = manifest(nested, V5, "MANIFESTO_v5.json")
        if any(meta.get(k) != v for k, v in IDENTITY.items()) or meta.get("versao_esquema") != "1.0.0":
            raise ValueError("Manifesto V5 incompatível.")
        entries = []
        for horizon in (24, 48):
            name = f"previsoes_{horizon}h_v5.csv"
            csv_path = scratch / name
            print(f"Verificando e indexando {name}...", flush=True)
            copy_checked(nested, V5, name, meta["arquivos"][name], csv_path)
            entries.extend(build_horizon(csv_path, scratch, horizon, meta["arquivos"][name]["linhas"]))
            csv_path.unlink()
        for entry in entries:
            (scratch / entry["file"]).replace(target / entry["file"])
        value = {"schema": 1, "source": {name: meta["arquivos"][name]["sha256"] for name in (
            "previsoes_24h_v5.csv", "previsoes_48h_v5.csv"
        )}, "partitions": entries}
        index = scratch / "index.json"
        index.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        legacy = scratch / "painel.zip"
        with source.open(legacy.name) as member, legacy.open("wb") as output:
            shutil.copyfileobj(member, output, length=1024 * 1024)
        if digest(legacy) != "b10830eaae445d958d42f05f00551b66a500126af7cbfdfd7d981f34f7e7f9d7":
            raise ValueError("SHA-256 divergente no pacote legado V1.")
        legacy.replace(target / legacy.name)
        index.replace(target / "index.json")
        print(f"{len(entries)} partições, {sum(e['rows'] for e in entries)} linhas. SHA-256 do índice: {digest(target / 'index.json')}")


def build_preview(directory, target):
    """Publica somente as emissões selecionadas identificadas no manifesto V5."""
    from collections import defaultdict

    index = json.loads((directory / "index.json").read_text(encoding="utf-8"))
    meta = json.loads((SMALL / V5 / "MANIFESTO_v5.json").read_text(encoding="utf-8"))
    by_key = {(e["horizon"], e["scenario"], e["stage"], e["month"]): e for e in index["partitions"]}
    groups = defaultdict(list)
    for sample in meta["amostras_leitor"]:
        issue = sample["origem_t"]
        month = pd.Timestamp(issue).tz_convert("America/Sao_Paulo").strftime("%Y-%m")
        key = (sample["horizonte_h"], sample["cenario"], sample["etapa"], month)
        groups[key].append(issue)
    target.mkdir(parents=True, exist_ok=True)
    entries = []
    for key, issues in groups.items():
        entry = by_key[key]
        source = directory / entry["file"]
        if digest(source) != entry["sha256"]:
            raise ValueError(f"Partição alterada: {source.name}.")
        view = pd.read_parquet(source, filters=[("origem_t", "in", issues), ("eh_selecionado", "=", 1)])
        for issue in issues:
            steps = view.loc[view["origem_t"].eq(issue), "passo_h"]
            if sorted(steps.tolist()) != list(range(1, key[0] + 1)):
                raise ValueError(f"Emissão selecionada inválida: {issue}.")
        path = target / source.name
        view.to_parquet(path, index=False, compression="zstd")
        entries.append({**entry, "sha256": digest(path), "bytes": path.stat().st_size, "rows": len(view)})
    value = {"schema": 1, "source": index["source"], "coverage": "manifest_samples", "partitions": entries}
    (target / "index.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Prévia: {len(entries)} partições, {sum(e['rows'] for e in entries)} alvos.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--small", action="store_true", help="Atualiza somente os CSVs compactos e manifestos do projeto.")
    mode.add_argument("--preview", action="store_true", help="Gera a amostra V5 a partir das partições já preparadas.")
    parser.add_argument("--detail-dir", type=Path, default=DETAIL)
    args = parser.parse_args()
    if args.preview:
        build_preview(args.detail_dir, SMALL / 'preview')
        return
    if args.zip is None:
        parser.error("Informe o ZIP de origem para preparar os dados.")
    with ZipFile(args.zip) as source:
        if args.small:
            package_small(source)
        else:
            build(source, args.detail_dir)


if __name__ == "__main__":
    main()
