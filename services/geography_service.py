"""Auditoria territorial independente dos rótulos declarados nos arquivos.

Não altera fontes nem transforma uma série regional em municipal. A evidência
numérica abaixo é vinculada ao hash do pacote auditado e ao ano comparado.
Estações desconhecidas não recebem município por associação com a carga.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import unicodedata

import pandas as pd

from services.data_loader import DataBundle, empty_observations, empty_weather


TARGET_REGION = "Município do Rio de Janeiro"
KNOWN_REGIONAL_ARCHIVE_SHA256 = "b10830eaae445d958d42f05f00551b66a500126af7cbfdfd7d981f34f7e7f9d7"
ONS_SOURCE_URL = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/balanco_energia_subsistema_ho/BALANCO_ENERGIA_SUBSISTEMA_2024.csv"
INMET_SOURCE_URL = "https://apitempo.inmet.gov.br/estacoes/T"
STATION_METADATA = {
    "A621": {"name": "RIO DE JANEIRO - VILA MILITAR", "municipality": "Rio de Janeiro",
             "municipality_code": "3304557", "latitude": -22.86138888, "longitude": -43.41138888},
    "A601": {"name": "SEROPEDICA-ECOLOGIA AGRICOLA", "municipality": "Seropédica",
             "municipality_code": "3305554", "latitude": -22.75777777, "longitude": -43.68472221},
}
_MUNICIPAL_NAMES = {
    "municipio do rio de janeiro", "rio de janeiro (municipio)",
    "rio de janeiro - municipio", "rio de janeiro - rj (municipio)",
}
_REGIONAL_EVIDENCE = {
    "archive_sha256": KNOWN_REGIONAL_ARCHIVE_SHA256,
    "source_url": ONS_SOURCE_URL,
    "dataset_url": "https://dados.ons.org.br/dataset/balanco-energia-subsistema",
    "official_file_sha256": "cb63c58aa9b0d45e5099471e6c91da3147dd511f2f9950f129f92a4354ca62bb",
    "official_value_column": "val_carga",
    "official_timestamp_column": "din_instante",
    "local_value_column": "carga_mwmed",
    "checked_period_start": "2024-01-01 00:00:00",
    "checked_period_end": "2024-12-31 23:00:00",
    "matched_hours": 8784,
    "matching_hours_within_1e_5": 8784,
    "max_absolute_difference_mwmed": 1.000444171950221e-8,
    "official_subsystem_id": "SE",
    "official_subsystem_name": "SUDESTE/CENTRO-OESTE",
    "retrieved_date": "2026-11-16",
    "limitation": "Comparação independente de 2024; os demais anos e o protocolo de treino não foram certificados por esta comparação.",
}


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold().split())


def _source_regions(bundle: DataBundle) -> list[str]:
    regions = set()
    declared = bundle.provenance.get("region")
    if isinstance(declared, str) and declared.strip():
        regions.add(declared.strip())
    regions.update(forecast.region.strip() for forecast in bundle.forecasts if forecast.region.strip())
    for frame in (bundle.observations, bundle.prediction_rows, bundle.reported_metrics, bundle.weather, bundle.calendar):
        if "region" in frame:
            regions.update(str(value).strip() for value in frame["region"].dropna().unique() if str(value).strip())
    return sorted(regions)


def _station_status(bundle: DataBundle) -> dict:
    stations = sorted(str(value) for value in bundle.weather.get("station", pd.Series(dtype=str)).dropna().unique())
    return {
        "municipality_weather_stations": [station for station in stations if station == "A621"],
        "outside_municipality_weather_stations": [station for station in stations if station == "A601"],
        "unverified_weather_stations": [station for station in stations if station not in STATION_METADATA],
        "weather_station_metadata": {station: deepcopy(STATION_METADATA[station]) for station in stations if station in STATION_METADATA},
        "weather_evidence_url": INMET_SOURCE_URL,
    }


def _source_signature(record: dict) -> str:
    fields = {key: record[key] for key in (
        "mode", "archive_sha256", "source_regions", "source_region", "reason", "source_counts",
    )}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def _quarantined_audit(bundle: DataBundle) -> dict | None:
    """Reconhece uma visão já esvaziada sem perder a identidade da fonte."""
    audit = bundle.provenance.get("geographic_audit")
    record = bundle.provenance.get("geographic_quarantine")
    if not isinstance(audit, dict) or not isinstance(record, dict):
        return None
    if audit.get("status") != "incompatible" or record.get("mode") != bundle.mode:
        return None
    if bundle.forecasts or any(not frame.empty for frame in (bundle.observations, bundle.prediction_rows, bundle.reported_metrics)):
        return None
    digest = str(bundle.provenance.get("archive_sha256") or bundle.provenance.get("sha256") or "").lower()
    if record.get("archive_sha256") != digest:
        return None
    if any(record.get(key) != audit.get(key) for key in ("source_regions", "source_region", "reason")):
        return None
    source_regions = record.get("source_regions")
    if not isinstance(source_regions, list) or any(not isinstance(region, str) for region in source_regions):
        return None
    if not set(_source_regions(bundle)).issubset(set(source_regions)):
        return None
    try:
        if record.get("signature") != _source_signature(record) or audit.get("source_signature") != record["signature"]:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return deepcopy(audit)


def geographic_status(bundle: DataBundle) -> dict:
    """Distingue demonstração, incompatibilidade comprovada e mera declaração."""
    previous = _quarantined_audit(bundle)
    station_status = _station_status(bundle)
    if previous:
        # A filtragem de A601 não apaga a informação de que ela existia na fonte.
        station_keys = ("municipality_weather_stations", "outside_municipality_weather_stations", "unverified_weather_stations")
        codes = {station for key in station_keys for station in station_status[key]}
        for key in station_keys:
            if isinstance(previous.get(key), list):
                codes.update(station for station in previous[key] if isinstance(station, str))
        # Reclassificar pelos metadados oficiais; um rótulo anterior editado
        # jamais autoriza A601 como estação municipal.
        station_status.update({
            "municipality_weather_stations": sorted(codes & {"A621"}),
            "outside_municipality_weather_stations": sorted(codes & {"A601"}),
            "unverified_weather_stations": sorted(codes.difference(STATION_METADATA)),
            "weather_station_metadata": {code: deepcopy(STATION_METADATA[code]) for code in sorted(codes) if code in STATION_METADATA},
        })
    result = {
        "status": "unverified", "target_region": TARGET_REGION, "source_region": None,
        "reason": "Não há metadados suficientes para identificar a abrangência territorial da fonte.",
        "source_regions": previous["source_regions"] if previous else _source_regions(bundle),
        "evidence_url": None, "evidence": {}, **station_status,
    }
    digest = str(bundle.provenance.get("archive_sha256") or bundle.provenance.get("sha256") or "").lower()
    if digest == KNOWN_REGIONAL_ARCHIVE_SHA256:
        result.update({
            "status": "incompatible", "source_region": "Subsistema Sudeste/Centro-Oeste",
            "reason": "A carga de 2024 deste pacote coincide nas 8.784 horas com o subsistema Sudeste/Centro-Oeste do ONS. Essa série e seus resultados não podem ser apresentados como carga municipal do Rio de Janeiro.",
            "evidence_url": ONS_SOURCE_URL, "evidence": deepcopy(_REGIONAL_EVIDENCE),
        })
        return result
    if previous:
        return {**previous, **station_status}
    if bundle.mode == "demo":
        result.update({
            "status": "synthetic", "source_region": "Cenário sintético de demonstração",
            "reason": "Dados artificiais para demonstração; não são medições nem resultados municipais reais.",
            "municipality_weather_stations": [], "outside_municipality_weather_stations": [],
            "unverified_weather_stations": [],
        })
        return result
    regions = _source_regions(bundle)
    if not regions:
        return result
    result["source_region"] = "; ".join(regions)
    if any(_normalize(region) not in _MUNICIPAL_NAMES for region in regions):
        result.update({
            "status": "incompatible",
            "reason": "O recorte declarado da fonte não corresponde exclusivamente ao Município do Rio de Janeiro. Não se pode corrigir a abrangência apenas alterando o rótulo.",
        })
    else:
        result.update({
            "status": "declared",
            "reason": "O município foi declarado nos metadados; essa declaração não constitui comprovação independente da origem dos dados.",
        })
    return result


def municipal_bundle(bundle: DataBundle) -> DataBundle:
    """Retorna visão municipal defensiva, preservando o DataBundle bruto.

    Na incompatibilidade, carga, previsões e métricas ficam indisponíveis. A621
    pode permanecer como contexto sem carga; A601 e estações não verificadas
    nunca entram na média municipal. Dados sintéticos continuam identificados.
    """
    audit = geographic_status(bundle)
    quarantine = None
    if audit["status"] == "incompatible":
        if _quarantined_audit(bundle):
            quarantine = deepcopy(bundle.provenance["geographic_quarantine"])
        else:
            quarantine = {
                "mode": bundle.mode,
                "archive_sha256": str(bundle.provenance.get("archive_sha256") or bundle.provenance.get("sha256") or "").lower(),
                "source_regions": list(audit["source_regions"]), "source_region": audit["source_region"],
                "reason": audit["reason"],
                "source_counts": {"forecasts": len(bundle.forecasts), "observations": len(bundle.observations),
                                  "prediction_rows": len(bundle.prediction_rows), "reported_metrics": len(bundle.reported_metrics)},
            }
            quarantine["signature"] = _source_signature(quarantine)
        audit["source_signature"] = quarantine["signature"]
    provenance = dict(bundle.provenance, geographic_audit=deepcopy(audit), geographic_status=audit["status"])
    if quarantine:
        provenance["geographic_quarantine"] = quarantine
    issues = list(bundle.issues)
    if audit["status"] == "synthetic":
        return replace(bundle, provenance=provenance, issues=issues)
    if "station" in bundle.weather:
        weather = bundle.weather.loc[bundle.weather["station"].isin(audit["municipality_weather_stations"])].copy()
    else:
        weather = empty_weather()
    removed = audit["outside_municipality_weather_stations"] + audit["unverified_weather_stations"]
    if removed:
        message = "Estações fora do recorte municipal ou sem localização verificada ficaram indisponíveis na visão municipal: " + ", ".join(removed) + "."
        if message not in issues:
            issues.append(message)
    if audit["status"] == "incompatible":
        if audit["reason"] not in issues:
            issues.append(audit["reason"])
        return replace(
            bundle, forecasts=[], observations=empty_observations(),
            prediction_rows=bundle.prediction_rows.iloc[0:0].copy(),
            reported_metrics=bundle.reported_metrics.iloc[0:0].copy(),
            weather=weather, calendar=bundle.calendar.copy(), issues=issues, provenance=provenance,
        )
    return replace(bundle, weather=weather, issues=issues, provenance=provenance)
