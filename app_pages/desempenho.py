"""Comparação compacta, cobertura recolhível e investigação de erros."""

import pandas as pd
import streamlit as st

from components.charts import degradation_chart
from components.page_frame import DAY_LABELS, SCOPE_LABELS, SPLIT_LABELS, get_catalog, page_header
from components.tables import csv_bytes, data_table
from services.analysis_service import build_evaluation_rows, comparison_metrics, error_by_lead, forecast_identifier, largest_errors
from services.archive_analysis import prepare_archive_evaluation, fast_comparison_metrics, fast_error_by_lead, merge_reported_metrics

SEGMENTS = [(24, "1–24 h"), (48, "1–24 h"), (48, "25–48 h"), (48, "1–48 h")]


def _comparison_table(detail, reference, unit, synthetic):
    records = []
    selections = [(h, segment, "Modelo", f"Modelo {h} h · {segment}") for h, segment in SEGMENTS]
    selections += [(reference[0], reference[1], method, f"{method} · {reference[0]} h / {reference[1]}") for method in ("Persistência", "Sazonal semanal")]
    for horizon, segment, method, label in selections:
        candidates = detail.loc[(detail["horizon_hours"] == horizon) & (detail["segment"] == segment) & (detail["method"] == method)]
        row = candidates.iloc[0] if not candidates.empty else None
        origin = "N/D" if row is None else ("Sintético" if synthetic else ("Resumo" if "resumo" in str(row["metric_origin"]).lower() else "Calculado"))
        records.append({
            "Modelo / janela": label,
            f"MAE ({unit})": row["mae"] if row is not None else None,
            f"RMSE ({unit})": row["rmse"] if row is not None else None,
            "MAPE (%)": row["mape"] if row is not None else None, "Origem": origin,
        })
    return pd.DataFrame(records)


def render() -> None:
    if st.session_state.get("version_catalog_mode"):
        from components.model_versions_views import render_evolution

        render_evolution()
        return
    bundle, settings = page_header("Avaliação de Desempenho e Erros")
    catalog = get_catalog(bundle, settings)
    if catalog.empty:
        st.info("Nenhuma previsão disponível para avaliação.")
        return
    chosen_ids = []
    choices = {}
    for horizon in (24, 48):
        runs = catalog.loc[catalog["horizon_hours"] == horizon]
        choices[horizon] = (runs, sorted(set(zip(runs["model_name"], runs["model_version"]))))
    multiple_models = any(len(models) > 1 for _, models in choices.values())
    if multiple_models:
        with st.expander("Modelos", expanded=True):
            columns = st.columns(2)
            for column, (horizon, (runs, models)) in zip(columns, choices.items()):
                with column:
                    if models:
                        selected_model = st.selectbox(f"Modelo {horizon} h", models, format_func=lambda value: f"{value[0]} · {value[1]}", key=f"comparison_model_{horizon}_{settings.mode}")
                        chosen_ids.extend(runs.loc[(runs["model_name"] == selected_model[0]) & (runs["model_version"] == selected_model[1]), "forecast_id"])
    else:
        chosen_ids = catalog["forecast_id"].tolist()
    weather = bundle.weather
    if settings.station is not None and not weather.empty:
        weather = weather.loc[weather["station"] == settings.station]
    try:
        with st.spinner("Preparando a avaliação…"):
            if not bundle.prediction_rows.empty:
                source = bundle.prediction_rows.loc[bundle.prediction_rows["forecast_id"].isin(chosen_ids)]
                rows = prepare_archive_evaluation(source, bundle.observations, weather, bundle.calendar, settings.region, settings.unit)
                summary = fast_comparison_metrics(rows, common_sample=True)
            else:
                chosen = set(chosen_ids)
                forecasts = [run for run in bundle.forecasts if forecast_identifier(run) in chosen]
                rows = build_evaluation_rows(forecasts, bundle.observations, weather, bundle.calendar, settings.region, settings.unit)
                summary = comparison_metrics(rows, common_sample=True)
            if not bundle.reported_metrics.empty:
                summary = merge_reported_metrics(summary, bundle.reported_metrics, region=settings.region, unit=settings.unit)
            elif "metric_origin" not in summary:
                summary["metric_origin"] = "Recalculada dos pares disponíveis"
    except ValueError as exc:
        st.error(f"Avaliação indisponível: {exc}")
        return
    if summary.empty:
        st.info("Nenhum par disponível para avaliação.")
        return
    splits = [value for value in ("test_2025", "forecast_2026", "validation_2025", "unspecified") if value in set(summary["dataset_split"])]
    controls = st.columns([1, 1.6])
    with controls[0]:
        split = st.selectbox("Conjunto", splits, format_func=lambda value: SPLIT_LABELS[value], key=f"performance_split_{settings.mode}")
    detail = summary.loc[summary["dataset_split"] == split]
    selected = rows.loc[rows["dataset_split"] == split]
    reference_options = [(h, segment) for h, segment in SEGMENTS if ((detail["horizon_hours"] == h) & (detail["segment"] == segment)).any()]
    with controls[1]:
        reference = st.selectbox("Janela das referências", reference_options or [(24, "1–24 h")], format_func=lambda value: f"{value[0]} h · passos {value[1]}")
    models = detail.loc[(detail["method"] == "Modelo") & (detail["segment"] == "1–24 h")]
    paired = models["horizon_hours"].nunique() == 2 and models.get("comparison_verified", pd.Series(False, index=models.index)).fillna(False).all()
    aggregate_only = selected.empty
    if aggregate_only:
        st.warning("Métricas agregadas fornecidas. O pareamento ponto a ponto não foi verificado.")
        title = "Resultados informados"
    elif not paired:
        st.warning("Sem pareamento verificado entre os horizontes. Os resultados são descritivos por modelo, sem comparação entre 24 h e 48 h.")
        title = "Resultados por modelo"
    else:
        title = "Comparação dos Modelos"
    st.subheader(title)
    data_table(_comparison_table(detail, reference, settings.unit, bundle.mode == "demo"))
    with st.expander("Amostra e cobertura"):
        coverage = detail[["model_label", "segment", "method", "n_pairs", "total_targets", "coverage", "n_issuances", "available_issuances", "mape_valid_pairs", "mape_excluded_zeros", "metric_origin"]].copy()
        coverage["coverage"] *= 100
        data_table(coverage.rename(columns={"model_label": "Modelo", "segment": "Passos", "method": "Método", "n_pairs": "Pares", "total_targets": "Alvos", "coverage": "Cobertura (%)", "n_issuances": "Emissões", "available_issuances": "Disponíveis", "mape_valid_pairs": "Pares MAPE", "mape_excluded_zeros": "Zeros MAPE", "metric_origin": "Origem"}), integer_columns=("Pares", "Alvos", "Emissões", "Disponíveis", "Pares MAPE", "Zeros MAPE"))
        for policy in detail["sample_policy"].dropna().unique():
            st.write(policy)
        st.write("N/D indica quantidade não verificável. Resumos agregados não confirmam cobertura nem correspondência dos pares.")
        st.download_button("Exportar avaliação completa", csv_bytes(summary.assign(data_source=bundle.mode)), file_name=f"{'sintetico_' if bundle.mode == 'demo' else ''}avaliacao_por_conjunto.csv", mime="text/csv")
    with st.expander("Detalhes metodológicos"):
        st.write("MAE e RMSE estão na unidade da carga; MAPE está em %. Observados iguais a zero são excluídos apenas do MAPE. Positivos próximos de zero são mantidos e podem ampliar o percentual; não há corte arbitrário.")
        st.write("Persistência repete a última carga observada até t₀, com defasagem máxima de 1 h. Sazonal semanal usa o alvo menos 168 h, disponível em t₀. Nenhuma referência consulta carga posterior à emissão.")
        st.write("Modelo e referências usam a interseção dos pares disponíveis de cada segmento. Os primeiros 24 passos dos dois modelos usam pares comuns quando verificáveis. Conjuntos, regiões e unidades não são misturados.")
        st.write("Passo é a posição inteira de 1 a 48; a antecedência efetiva pode ser fracionária. Emissões sobrepostas não são amostras independentes. Os rótulos de validação/teste não certificam ausência de vazamento no treinamento.")
        if bundle.mode == "demo":
            st.write("Todas as métricas são ilustrativas, calculadas sobre dados sintéticos.")
    if aggregate_only:
        st.info("Sem previsões individuais deste conjunto: curva por passo e episódios de erro indisponíveis.")
        return
    st.subheader("Erro por Horizonte")
    metric = st.radio("Métrica", ["MAE", "RMSE", "MAPE"], horizontal=True, key="degradation_metric")
    try:
        by_lead = fast_error_by_lead(selected) if not bundle.prediction_rows.empty else error_by_lead(selected)
        if by_lead.empty:
            st.info("Sem pares detalhados válidos para a curva.")
        else:
            figure = degradation_chart(by_lead, unit=settings.unit, metric=metric.lower())
            figure.update_layout(title_text=None, margin={"t": 20})
            st.plotly_chart(figure, width="stretch", config={"displaylogo": False})
    except ValueError as exc:
        st.error(f"Curva indisponível: {exc}")
    st.subheader("Maiores Erros")
    filters = st.columns([1, 1.15, 1.4, 1.6])
    with filters[0]:
        month = st.selectbox("Mês", [None] + sorted(selected["month"].dropna().astype(int).unique().tolist()), format_func=lambda value: "Todos" if value is None else f"{value:02d}", key=f"error_month_{settings.mode}_{split}")
    with filters[1]:
        weekday = st.selectbox("Dia da semana", [None] + list(range(7)), format_func=lambda value: "Todos" if value is None else ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][value], key=f"error_weekday_{settings.mode}_{split}")
    with filters[2]:
        day_types = st.multiselect("Calendário", sorted(selected["day_type"].unique()), format_func=lambda value: DAY_LABELS.get(value, value), placeholder="Todos", key=f"error_days_{settings.mode}_{split}")
    temp_range = None
    with filters[3]:
        temperatures = selected["temperature_c"].dropna()
        if not temperatures.empty and temperatures.min() < temperatures.max():
            limits = (float(temperatures.min()), float(temperatures.max()))
            chosen_temp = st.slider("Temperatura (°C)", limits[0], limits[1], limits, key=f"error_temp_{settings.mode}_{split}", help="Sem alterar a faixa, inclui também pares sem temperatura. Ao restringir, usa apenas leituras correspondentes.")
            if chosen_temp != limits:
                temp_range = chosen_temp
        else:
            st.caption("Temperatura: N/D")
    worst = largest_errors(selected, month=month, weekday=weekday, day_types=day_types or None, temp_range=temp_range, limit=30)
    if worst.empty:
        st.info("Nenhum episódio atende aos filtros.")
        return
    display = worst.copy()
    for column in ("timestamp", "issued_at"):
        display[column] = display[column].dt.tz_convert(settings.timezone).dt.strftime("%d/%m/%Y %H:%M %z")
    display["day_type"] = display["day_type"].map(DAY_LABELS).fillna("Não informado")
    display["holiday_scope"] = display["holiday_scope"].map(SCOPE_LABELS).fillna("Não informado")
    columns = ["issued_at", "timestamp", "model_label", "forecast_step", "observed_load", "predicted_load", "absolute_error", "day_type", "holiday_scope", "temperature_c"]
    data_table(display[columns].rename(columns={"issued_at": "Emissão t₀", "timestamp": "Instante previsto", "model_label": "Horizonte", "forecast_step": "Passo", "observed_load": f"Real ({settings.unit})", "predicted_load": f"Previsto ({settings.unit})", "absolute_error": f"Erro absoluto ({settings.unit})", "day_type": "Calendário", "holiday_scope": "Âmbito", "temperature_c": "Temp. (°C)"}), height=390)
    st.download_button("Exportar episódios", csv_bytes(worst.assign(data_source=bundle.mode)), file_name=f"{'sintetico_' if bundle.mode == 'demo' else ''}maiores_erros_{split}.csv", mime="text/csv")
