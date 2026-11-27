"""Confere os MAEs e denominadores do destaque V5 com o detalhe completo local."""

import argparse
from collections import defaultdict
from hashlib import file_digest
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1] / "data" / "versions" / "entrega_painel_v5"
METHODS = {
    "ols_estabilizado": "y_pred",
    "sazonal_semanal": "y_baseline_semanal",
    "persistencia": "y_baseline_persistencia",
}


def audit(detail_dir: Path) -> dict:
    """Lê somente as colunas necessárias do OLS, uma partição por vez."""
    manifest = json.loads((ROOT / "MANIFESTO_v5.json").read_text(encoding="utf-8"))
    index = json.loads((detail_dir / "index.json").read_text(encoding="utf-8"))
    expected = {name: manifest["arquivos"][name]["sha256"] for name in ("previsoes_24h_v5.csv", "previsoes_48h_v5.csv")}
    if index["schema"] != 1 or index["source"] != expected:
        raise ValueError("Índice incompatível com o manifesto V5.")

    metrics_path = ROOT / "metricas_globais_v5.csv"
    with metrics_path.open("rb") as source:
        if file_digest(source, "sha256").hexdigest() != manifest["arquivos"][metrics_path.name]["sha256"]:
            raise ValueError("O hash das métricas globais diverge do manifesto.")
    keys = ["cenario", "etapa", "horizonte_h", "bloco_horas", "modelo"]
    table = pd.read_csv(metrics_path, float_precision="round_trip").set_index(keys)
    scoped = table.loc[table.index.get_level_values("modelo").isin(METHODS)]

    counts = defaultdict(int)
    mape_counts = defaultdict(int)
    absolute = defaultdict(list)
    seen = set()
    for entry in index["partitions"]:
        horizon, scenario, stage, month = (entry[key] for key in ("horizon", "scenario", "stage", "month"))
        filename = "__".join(map(str, (horizon, scenario, stage, month))) + ".parquet"
        if (horizon not in (24, 48) or filename != entry["file"] or Path(filename).name != filename or filename in seen):
            raise ValueError(f"Partição inválida ou repetida: {entry['file']}.")
        seen.add(filename)
        path = detail_dir / filename
        with path.open("rb") as source:
            if file_digest(source, "sha256").hexdigest() != entry["sha256"]:
                raise ValueError(f"O hash diverge para {filename}.")
        frame = pd.read_parquet(path, filters=[("modelo", "=", "ols_estabilizado")],
                                columns=["origem_t", "instante_alvo", "passo_h", "y_real", *METHODS.values()])
        steps = frame["passo_h"]
        delay = pd.to_datetime(frame["instante_alvo"], utc=True) - pd.to_datetime(frame["origem_t"], utc=True)
        origins = pd.to_datetime(frame["origem_t"], utc=True).dt.tz_convert("America/Sao_Paulo")
        if (frame.isna().any().any() or frame.duplicated(["origem_t", "passo_h"]).any()
                or not frame.groupby("origem_t").size().eq(horizon).all()
                or not (steps.between(1, horizon) & steps.mod(1).eq(0)).all()
                or not delay.eq(pd.to_timedelta(steps, unit="h")).all()
                or not origins.dt.strftime("%Y-%m").eq(month).all()):
            raise ValueError(f"Pares, passos, datas ou valores inválidos em {filename}.")
        blocks = [(1, 24)] if horizon == 24 else [(1, 24), (25, 48), (1, 48)]
        for start, stop in blocks:
            rows = frame.loc[steps.between(start, stop)]
            key = (scenario, stage, horizon, f"{start}–{stop} h")
            counts[key] += len(rows)
            mape_counts[key] += int(rows["y_real"].ne(0).sum())
            for model, column in METHODS.items():
                absolute[(*key, model)].append(rows["y_real"].sub(rows[column]).abs().sum())

    if set(scoped.index) != set(absolute):
        raise ValueError("Os agregados e o detalhe não cobrem os mesmos recortes.")
    for key, sums in absolute.items():
        row = scoped.loc[key, :]
        count = counts[key[:-1]]
        if (count != row.n_pares or mape_counts[key[:-1]] != row.n_mape_validos
                or not math.isclose(math.fsum(sums) / count, row.mae_mwmed, abs_tol=1e-8, rel_tol=0)):
            raise ValueError(f"MAE ou denominador divergente no recorte {key}.")
    return {"particoes_verificadas": len(seen), "recortes": len(counts), "maes_reproduzidos": len(absolute),
            "pares_bloco": sum(counts.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detail_dir", type=Path, help="Pasta do índice e das partições completas V5.")
    args = parser.parse_args()
    print(json.dumps(audit(args.detail_dir), ensure_ascii=False, indent=2))
