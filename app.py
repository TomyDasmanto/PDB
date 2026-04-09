import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.request import urlopen
import math

st.set_page_config(
    page_title="Model Framework Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Konfigurasi sumber file ----------
REPO_FILE_NAME = "dashboard PDB.xlsx"
try:
    GITHUB_RAW_XLSX_URL = st.secrets.get("github_raw_xlsx_url", "")
except Exception:
    GITHUB_RAW_XLSX_URL = ""

# ---------- Styling ----------
PRIMARY = "#3E6DB5"
ACCENT = "#E07B39"
SUCCESS = "#2A9D8F"
PURPLE = "#8A5CF6"
NEGATIVE = "#D14D72"
POS_LIGHT = "#DCEFEA"
NEG_LIGHT = "#F8E1E8"
NEUTRAL_LIGHT = "#F3F4F6"
CELL_A = "#D7DBEA"
CELL_B = "#E8EBF4"
CELL_ORANGE = "#EFD9CF"
BG = "#F6F7FB"
TEXT = "#1F2937"
GRID = "rgba(31,41,55,0.12)"
TABLE_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}
CHART_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}

PERIOD_MAP = {
    "out_tw1": "Outlook Q1",
    "out_tw2": "Outlook Q2",
    "out_tw3": "Outlook Q3",
    "out_tw4": "Outlook Q4",
    "full_year": "Full Year",
}
PERIOD_ORDER = list(PERIOD_MAP.keys())

EXPECTED_SHEETS = {
    "simulasi": ["indikator", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "makro": ["indikator", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "pdb": ["indikator", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "moneter": ["indikator", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "fiskal": ["indikator", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
}

DEFAULT_ROWS = {
    "simulasi": ["Consumption", "Investment", "Govt. Spending", "Export", "Import", "Unemployment"],
    "makro": ["Inflasi", "Rupiah", "Yield SBN", "ICP", "Nikel", "Coal", "CPO", "Lifting"],
    "pdb": ["Konsumsi RT", "Konsumsi LNPRT", "PMTB", "Change in Stocks", "Ekspor", "Impor", "PDB Aggregate"],
    "moneter": ["PUAB", "Kredit", "DPK", "M0", "OMO"],
    "fiskal": ["Pendapatan", "Belanja", "Pembiayaan", "Defisit"],
}

BLOCK_TITLES = {
    "simulasi": "Simulasi PDB & Kesejahteraan",
    "makro": "Blok Makro",
    "pdb": "Accounting / PDB",
    "moneter": "Blok Moneter",
    "fiskal": "Blok Fiskal",
}

BLOCK_NOTES = {
    "simulasi": "Hasil simulasi PDB dan kesejahteraan 2026.",
    "makro": "Indikator Makro.",
    "pdb": "Outlook PDB 2026.",
    "moneter": "Variabel Moneter.",
    "fiskal": "I-Account APBN.",
}

PDB_COMPONENTS = ["Konsumsi RT", "Konsumsi LNPRT", "PMTB", "Change in Stocks", "Ekspor", "Impor", "PDB Aggregate"]
EXCLUDE_GROWTH_ROWS = ["Change in Stocks"]

st.markdown(
    f"""
    <style>
        .main {{ background-color: {BG}; }}
        .block-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {TEXT};
            margin: 0.2rem 0 0.45rem 0;
        }}
        .sub-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: {TEXT};
            margin: 0.35rem 0 0.4rem 0;
        }}
        .section-card {{
            border: 1px solid rgba(62,109,181,0.14);
            border-radius: 14px;
            padding: 0.7rem 0.8rem 0.5rem 0.8rem;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            margin-bottom: 0.9rem;
            overflow: hidden;
        }}
        .section-note {{
            color: #6B7280;
            font-size: 0.88rem;
            margin-bottom: 0.35rem;
        }}
        .chart-note {{
            color: #6B7280;
            font-size: 0.84rem;
            margin-top: -0.1rem;
            margin-bottom: 0.4rem;
        }}
        .status-box {{
            border: 1px dashed rgba(62,109,181,0.30);
            border-radius: 12px;
            padding: 0.55rem 0.75rem;
            background: rgba(62,109,181,0.03);
            color: #374151;
            margin-bottom: 0.75rem;
            font-size: 0.86rem;
        }}
        div[data-testid="stPlotlyChart"] {{
            width: 100%;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Helpers ----------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapper = {}
    for c in df.columns:
        key = str(c).strip().lower().replace(" ", "_")
        key = key.replace(".", "").replace("-", "_")
        mapper[c] = key
    return df.rename(columns=mapper).copy()


def empty_df(block: str) -> pd.DataFrame:
    rows = DEFAULT_ROWS[block]
    payload = {"indikator": rows}
    for col in PERIOD_ORDER:
        payload[col] = [None] * len(rows)
    return pd.DataFrame(payload)


def ensure_indicator_rows(df: pd.DataFrame, block: str) -> pd.DataFrame:
    """Keep indicator list complete and in the desired order."""
    expected_rows = DEFAULT_ROWS.get(block, [])
    if not expected_rows or "indikator" not in df.columns:
        return df

    work = df.copy()
    work["indikator"] = work["indikator"].fillna("")
    work["indikator"] = work["indikator"].astype(str).str.strip()

    # If indicator names are blank, fill by row position as much as possible
    blank_idx = work.index[work["indikator"].eq("")].tolist()
    for i, idx in enumerate(blank_idx):
        if idx < len(expected_rows):
            work.at[idx, "indikator"] = expected_rows[idx]

    # Build final table in default order, taking existing rows when available
    rows = []
    numeric_cols = [c for c in work.columns if c != "indikator"]
    for ind in expected_rows:
        found = work.loc[work["indikator"] == ind]
        if not found.empty:
            rows.append(found.iloc[0].to_dict())
        else:
            row = {"indikator": ind}
            for c in numeric_cols:
                row[c] = None
            rows.append(row)
    return pd.DataFrame(rows)


def coerce_schema(df: pd.DataFrame, block: str) -> pd.DataFrame:
    df = normalize_columns(df)
    expected = EXPECTED_SHEETS[block]
    if "indikator" not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "indikator"})
    for col in expected:
        if col not in df.columns:
            df[col] = None
    df = df[expected].copy()
    df = ensure_indicator_rows(df, block)
    return df


def load_excel_bytes_from_url(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def open_excel_source(source: Union[str, bytes, bytearray]):
    if isinstance(source, (bytes, bytearray)):
        return pd.ExcelFile(BytesIO(source), engine="openpyxl")
    return pd.ExcelFile(source, engine="openpyxl")


def detect_excel_source() -> Tuple[Optional[Union[str, bytes]], str]:
    local_path = Path(__file__).resolve().parent / REPO_FILE_NAME
    if local_path.exists():
        return str(local_path), f"Sumber data otomatis: `{REPO_FILE_NAME}`"
    if GITHUB_RAW_XLSX_URL:
        return load_excel_bytes_from_url(GITHUB_RAW_XLSX_URL), "Sumber data otomatis: GitHub Raw URL dari st.secrets['github_raw_xlsx_url']"
    return None, (
        "File Excel belum ditemukan. Simpan `dashboard PDB.xlsx` di root repo yang sama dengan `app.py`, "
        "atau isi `st.secrets['github_raw_xlsx_url']` dengan raw URL GitHub file tersebut."
    )


def _format_id_number(val: float, decimals: int = 0) -> str:
    s = f"{float(val):,.{decimals}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def fmt_id0(val):
    if pd.isna(val) or val is None:
        return "—"
    try:
        return _format_id_number(val, decimals=0)
    except Exception:
        return str(val)


def fmt_pct_id2(val):
    if pd.isna(val) or val is None:
        return "—"
    try:
        return _format_id_number(val, decimals=2) + "%"
    except Exception:
        return str(val)


def make_tick_values(series: pd.Series, n: int = 6):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return [], []
    vmin = float(s.min())
    vmax = float(s.max())
    if math.isclose(vmin, vmax):
        if math.isclose(vmin, 0.0):
            vals = [0]
        else:
            pad = abs(vmin) * 0.1
            vals = [vmin - pad, vmin, vmin + pad]
    else:
        step = (vmax - vmin) / max(n - 1, 1)
        vals = [vmin + i * step for i in range(n)]
    return vals, [fmt_id0(v) for v in vals]


def make_tick_values_pct(series: pd.Series, n: int = 6):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return [], []
    vmin = float(s.min())
    vmax = float(s.max())
    base_min = min(vmin, 0.0)
    base_max = max(vmax, 0.0)
    if math.isclose(base_min, base_max):
        vals = [base_min - 1, base_min, base_min + 1]
    else:
        step = (base_max - base_min) / max(n - 1, 1)
        vals = [base_min + i * step for i in range(n)]
    return vals, [fmt_pct_id2(v) for v in vals]


def filter_growth_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return empty_df("pdb")
    return df[~df["indikator"].isin(EXCLUDE_GROWTH_ROWS)].copy()


def filter_growth_components(components: list[str]) -> list[str]:
    return [c for c in components if c not in EXCLUDE_GROWTH_ROWS]


def growth_color(value):
    if pd.isna(value) or value is None:
        return NEUTRAL_LIGHT
    try:
        v = float(value)
    except Exception:
        return NEUTRAL_LIGHT
    if v > 0:
        return POS_LIGHT
    if v < 0:
        return NEG_LIGHT
    return NEUTRAL_LIGHT


def derive_pdb_from_realisasi(source: Union[str, bytes]):
    xls = open_excel_source(source)
    sheet_map = {s.lower().strip(): s for s in xls.sheet_names}
    if "realisasi" not in sheet_map:
        return empty_df("pdb"), None, None, None

    df = pd.read_excel(xls, sheet_name=sheet_map["realisasi"], engine="openpyxl")
    if df.empty:
        return empty_df("pdb"), None, None, None

    date_col = df.columns[0]
    df = df.rename(columns={date_col: "tanggal"}).copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df = df.dropna(subset=["tanggal"]).sort_values("tanggal")

    available = [c for c in PDB_COMPONENTS if c in df.columns]
    if not available:
        return empty_df("pdb"), None, None, None

    for c in available:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["year"] = df["tanggal"].dt.year
    df["quarter"] = df["tanggal"].dt.quarter

    data_2026 = df[df["year"] == 2026].copy()
    data_2025 = df[df["year"] == 2025].copy()
    quarter_name_map = {1: "out_tw1", 2: "out_tw2", 3: "out_tw3", 4: "out_tw4"}

    nominal_rows, yoy_rows, qtq_rows = [], [], []

    for comp in PDB_COMPONENTS:
        nominal = {"indikator": comp, "out_tw1": None, "out_tw2": None, "out_tw3": None, "out_tw4": None, "full_year": None}
        yoy = {"indikator": comp, "out_tw1": None, "out_tw2": None, "out_tw3": None, "out_tw4": None, "full_year": None}
        qtq = {"indikator": comp, "out_tw1": None, "out_tw2": None, "out_tw3": None, "out_tw4": None, "full_year": None}

        if comp in data_2026.columns:
            for q in [1, 2, 3, 4]:
                qdf = data_2026[data_2026["quarter"] == q]
                if not qdf.empty:
                    curr_val = qdf.iloc[0][comp]
                    nominal[quarter_name_map[q]] = curr_val

                    prev_yoy = data_2025[data_2025["quarter"] == q]
                    if not prev_yoy.empty and pd.notna(prev_yoy.iloc[0][comp]) and prev_yoy.iloc[0][comp] != 0:
                        yoy[quarter_name_map[q]] = ((curr_val / prev_yoy.iloc[0][comp]) - 1) * 100

                    if q == 1:
                        prev_qtq = df[(df["year"] == 2025) & (df["quarter"] == 4)]
                    else:
                        prev_qtq = data_2026[data_2026["quarter"] == q - 1]
                    if not prev_qtq.empty and pd.notna(prev_qtq.iloc[0][comp]) and prev_qtq.iloc[0][comp] != 0:
                        qtq[quarter_name_map[q]] = ((curr_val / prev_qtq.iloc[0][comp]) - 1) * 100

            full_2026 = data_2026[comp].sum(min_count=1)
            nominal["full_year"] = full_2026
            full_2025 = data_2025[comp].sum(min_count=1) if comp in data_2025.columns else None
            if pd.notna(full_2026) and pd.notna(full_2025) and full_2025 not in [0, None]:
                yoy["full_year"] = ((full_2026 / full_2025) - 1) * 100
            qtq["full_year"] = None

        nominal_rows.append(nominal)
        yoy_rows.append(yoy)
        qtq_rows.append(qtq)

    nominal_table = pd.DataFrame(nominal_rows)
    yoy_table = pd.DataFrame(yoy_rows)
    qtq_table = pd.DataFrame(qtq_rows)

    hist_cols = [c for c in PDB_COMPONENTS if c in df.columns]
    hist = df[["tanggal", *hist_cols]].copy().sort_values("tanggal")
    hist_long = hist.melt(id_vars="tanggal", value_vars=hist_cols, var_name="komponen", value_name="nilai")
    hist_long = hist_long.dropna(subset=["nilai"]).sort_values(["komponen", "tanggal"])

    growth_frames = []
    for comp in hist_cols:
        temp = hist[["tanggal", comp]].rename(columns={comp: "nilai"}).copy().sort_values("tanggal")
        temp["komponen"] = comp
        temp["yoy"] = temp["nilai"].pct_change(4) * 100
        temp["qtq"] = temp["nilai"].pct_change(1) * 100
        growth_frames.append(temp)
    growth_df = pd.concat(growth_frames, ignore_index=True) if growth_frames else None

    history_bundle = {"level": hist_long, "growth": growth_df}
    tables_bundle = {"nominal": nominal_table, "yoy": yoy_table, "qtq": qtq_table}
    return nominal_table, history_bundle, tables_bundle, df


def load_dashboard_data():
    data = {k: empty_df(k) for k in EXPECTED_SHEETS.keys()}
    pdb_history = None
    pdb_tables = None
    source, source_status = detect_excel_source()
    if source is None:
        return data, pdb_history, pdb_tables, source_status

    try:
        xls = open_excel_source(source)
        lower_sheet_map = {s.lower().strip(): s for s in xls.sheet_names}

        for block in ["simulasi", "makro", "moneter", "fiskal"]:
            if block in lower_sheet_map:
                df = pd.read_excel(xls, sheet_name=lower_sheet_map[block], engine="openpyxl")
                data[block] = coerce_schema(df, block)

        if "realisasi" in lower_sheet_map:
            data["pdb"], pdb_history, pdb_tables, _ = derive_pdb_from_realisasi(source)
        elif "pdb" in lower_sheet_map:
            df = pd.read_excel(xls, sheet_name=lower_sheet_map["pdb"], engine="openpyxl")
            data["pdb"] = coerce_schema(df, "pdb")

        return data, pdb_history, pdb_tables, source_status
    except Exception as e:
        return data, pdb_history, pdb_tables, f"Gagal membaca sumber Excel otomatis: {e}"


def format_display(df: pd.DataFrame, value_formatter=fmt_id0) -> pd.DataFrame:
    view = df.copy()
    ordered_cols = ["indikator", *PERIOD_ORDER]
    for c in ordered_cols:
        if c not in view.columns:
            view[c] = None
    view = view[ordered_cols].rename(columns={"indikator": "Indikator", **PERIOD_MAP})
    for c in view.columns[1:]:
        view[c] = view[c].apply(value_formatter)
    return view.fillna("—")


def make_table(df: pd.DataFrame, header_fill: str, row_fill_1: str, row_fill_2: str, first_col_width=210, other_col_width=110, height=320, value_formatter=fmt_id0):
    view = format_display(df, value_formatter=value_formatter)
    cols = list(view.columns)
    row_colors = [row_fill_1 if i % 2 == 0 else row_fill_2 for i in range(len(view))]
    fill_matrix = [[c for c in row_colors] for _ in cols]
    widths = [first_col_width] + [other_col_width] * (len(cols) - 1)
    aligns = ["left"] + ["center"] * (len(cols) - 1)

    fig = go.Figure(
        data=[go.Table(
            columnwidth=widths,
            header=dict(
                values=[f"<b>{c}</b>" for c in cols],
                fill_color=header_fill,
                font=dict(color="white", size=12),
                align=aligns,
                height=34,
                line_color="white",
            ),
            cells=dict(
                values=[view[c] for c in cols],
                fill_color=fill_matrix,
                font=dict(color=TEXT, size=12),
                align=aligns,
                height=31,
                line_color="white",
            ),
        )]
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def make_growth_table(df: pd.DataFrame, header_fill: str, first_col_width=230, other_col_width=112, height=260, value_formatter=fmt_pct_id2):
    table_df = filter_growth_rows(df)
    view = format_display(table_df, value_formatter=value_formatter)
    cols = list(view.columns)
    raw_ordered = table_df[["indikator", *PERIOD_ORDER]].copy()

    fill_matrix = []
    indicator_colors = [NEUTRAL_LIGHT if i % 2 == 0 else "#FFFFFF" for i in range(len(view))]
    fill_matrix.append(indicator_colors)
    for col in PERIOD_ORDER:
        fill_matrix.append([growth_color(v) for v in raw_ordered[col].tolist()])

    widths = [first_col_width] + [other_col_width] * (len(cols) - 1)
    aligns = ["left"] + ["center"] * (len(cols) - 1)

    fig = go.Figure(
        data=[go.Table(
            columnwidth=widths,
            header=dict(
                values=[f"<b>{c}</b>" for c in cols],
                fill_color=header_fill,
                font=dict(color="white", size=12),
                align=aligns,
                height=34,
                line_color="white",
            ),
            cells=dict(
                values=[view[c] for c in cols],
                fill_color=fill_matrix,
                font=dict(color=TEXT, size=12),
                align=aligns,
                height=31,
                line_color="white",
            ),
        )]
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def placeholder_chart(msg: str, height: int = 380):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="#6B7280"))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def make_pdb_history_chart(pdb_history: Optional[dict], selected_components: list[str]):
    if not pdb_history or pdb_history.get("level") is None or pdb_history["level"].empty:
        return placeholder_chart("Data historis PDB belum tersedia pada sumber Excel otomatis.")

    plot_df = pdb_history["level"]
    plot_df = plot_df[plot_df["komponen"].isin(selected_components)].copy()
    if plot_df.empty:
        return placeholder_chart("Tidak ada komponen historis yang dipilih.")

    plot_df["nilai_fmt"] = plot_df["nilai"].apply(fmt_id0)
    fig = px.line(
        plot_df,
        x="tanggal",
        y="nilai",
        color="komponen",
        markers=True,
        color_discrete_sequence=[PRIMARY, ACCENT, SUCCESS, PURPLE, NEGATIVE, "#F4A261", "#4C78A8"],
        custom_data=["nilai_fmt"],
    )
    fig.update_traces(
        mode="lines+markers",
        line=dict(width=2.6),
        marker=dict(size=5.5),
        hovertemplate="<b>%{fullData.name}</b><br>%{x|%Y-%m-%d}: %{customdata[0]}<extra></extra>",
    )
    tickvals, ticktext = make_tick_values(plot_df["nilai"])
    fig.update_layout(
        title="Historis Komponen PDB",
        height=395,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        legend_title_text="Komponen",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, tickmode="array", tickvals=tickvals, ticktext=ticktext)
    return fig


def make_growth_chart(pdb_history: Optional[dict], selected_components: list[str], growth_col: str, title: str, colors=None):
    if not pdb_history or pdb_history.get("growth") is None or pdb_history["growth"].empty:
        return placeholder_chart("Data pertumbuhan PDB belum tersedia pada sumber Excel otomatis.")

    plot_df = pdb_history["growth"]
    plot_df = plot_df[plot_df["komponen"].isin(selected_components)].copy()
    plot_df = plot_df.dropna(subset=[growth_col])
    if plot_df.empty:
        return placeholder_chart("Belum ada observasi yang cukup untuk menghitung pertumbuhan.")

    plot_df["growth_fmt"] = plot_df[growth_col].apply(fmt_pct_id2)
    fig = px.line(
        plot_df,
        x="tanggal",
        y=growth_col,
        color="komponen",
        markers=True,
        color_discrete_sequence=colors or [PRIMARY, ACCENT, SUCCESS, PURPLE, NEGATIVE, "#F4A261", "#4C78A8"],
        custom_data=["growth_fmt"],
    )
    fig.update_traces(
        mode="lines+markers",
        line=dict(width=2.5),
        marker=dict(size=5.5),
        hovertemplate="<b>%{fullData.name}</b><br>%{x|%Y-%m-%d}: %{customdata[0]}<extra></extra>",
    )
    tickvals, ticktext = make_tick_values_pct(plot_df[growth_col])
    fig.update_layout(
        title=title,
        height=395,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        legend_title_text="Komponen",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=True, tickmode="array", tickvals=tickvals, ticktext=ticktext)
    return fig


def block_card(title: str, note: Optional[str] = None):
    st.markdown(f'<div class="block-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)


def sub_title(text: str):
    st.markdown(f'<div class="sub-title">{text}</div>', unsafe_allow_html=True)


def render_table_block(block_df: pd.DataFrame, accent: bool = False, block_key: str = ""):
    st.plotly_chart(
        make_table(
            block_df,
            header_fill=PRIMARY,
            row_fill_1=CELL_A if not accent else CELL_ORANGE,
            row_fill_2=CELL_B if not accent else "#F4E5DE",
            first_col_width=230 if block_key == "pdb" else 210,
            other_col_width=112,
            height=300 if block_key == "simulasi" else 320,
            value_formatter=fmt_id0,
        ),
        use_container_width=True,
        config=TABLE_CONFIG,
    )


def render_growth_table(df: pd.DataFrame, title: str, header_fill: str):
    sub_title(title)
    st.plotly_chart(
        make_growth_table(
            df,
            header_fill=PRIMARY,
            first_col_width=230,
            other_col_width=112,
            height=260,
            value_formatter=fmt_pct_id2,
        ),
        use_container_width=True,
        config=TABLE_CONFIG,
    )


# ---------- Load otomatis dari repo/GitHub ----------
workbook, pdb_history, pdb_tables, source_status = load_dashboard_data()

# ---------- Sidebar ----------
st.sidebar.markdown("## Pengaturan Dashboard")
show_preview = st.sidebar.toggle("Tampilkan preview data mentah", value=False)
st.sidebar.markdown("### Sumber Data")
st.sidebar.info(source_status)

# ---------- Header ----------
st.title("Dashboard Pemantauan PDB")
st.markdown("---")
st.markdown(f"<div class='status-box'>{source_status}</div>", unsafe_allow_html=True)

# ---------- Main Simulation Block ----------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
block_card("Tabel Utama — Hasil Simulasi PDB & Kesejahteraan", BLOCK_NOTES["simulasi"])
render_table_block(workbook["simulasi"], accent=True, block_key="simulasi")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- Tabs for supporting tables ----------
tab_makro, tab_pdb, tab_moneter, tab_fiskal = st.tabs([
    "Blok Makro",
    "Blok Accounting",
    "Blok Moneter",
    "Blok Fiskal",
])

with tab_makro:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["makro"], BLOCK_NOTES["makro"])
    render_table_block(workbook["makro"], block_key="makro")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_pdb:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["pdb"], BLOCK_NOTES["pdb"])

    sub_title("Tabel Nominal 2026")
    render_table_block(workbook["pdb"], block_key="pdb")

    if pdb_tables is not None:
        render_growth_table(
            pdb_tables.get("yoy", empty_df("pdb")),
            "Tabel Year on Year (YoY)",
            header_fill=PRIMARY,
        )
        render_growth_table(
            pdb_tables.get("qtq", empty_df("pdb")),
            "Tabel Quarter to Quarter (QtQ)",
            header_fill=PRIMARY,
        )

    st.markdown("<div class='chart-note'>Warna header tabel dibuat seragam. Modebar pada tabel dimatikan agar tidak muncul kotak kamera/fullscreen yang menutupi tabel. Daftar indikator juga dijaga agar tetap lengkap dan berurutan. Baris Change in Stocks dihilangkan dari tabel YoY dan QtQ. Format persen pada tabel pertumbuhan dan grafik pertumbuhan memakai 2 angka desimal. Warna hijau muncul untuk pertumbuhan positif, merah untuk pertumbuhan negatif, dan abu-abu untuk nilai nol/kosong. Kolom Full Year pada QtQ sengaja dibiarkan kosong karena tidak memiliki definisi baku yang setara dengan pertumbuhan tahunan.</div>", unsafe_allow_html=True)
    selected_components = st.multiselect(
        "Pilih komponen historis yang ingin ditampilkan",
        options=PDB_COMPONENTS,
        default=PDB_COMPONENTS,
        key="hist_components_pdb",
    )
    selected_components = selected_components or PDB_COMPONENTS
    selected_growth_components = filter_growth_components(selected_components)

    ch1, ch2, ch3 = st.tabs(["Historis Level", "Year on Year (YoY)", "Quarter to Quarter (QtQ)"])
    with ch1:
        st.plotly_chart(
            make_pdb_history_chart(pdb_history, selected_components),
            use_container_width=True,
            config=CHART_CONFIG,
        )
    with ch2:
        st.plotly_chart(
            make_growth_chart(
                pdb_history,
                selected_growth_components,
                "yoy",
                "Pertumbuhan Year on Year (YoY)",
                colors=[SUCCESS, ACCENT, PRIMARY, PURPLE, NEGATIVE, "#F4A261", "#4C78A8"],
            ),
            use_container_width=True,
            config=CHART_CONFIG,
        )
    with ch3:
        st.plotly_chart(
            make_growth_chart(
                pdb_history,
                selected_growth_components,
                "qtq",
                "Pertumbuhan Quarter to Quarter (QtQ)",
                colors=[PURPLE, SUCCESS, PRIMARY, ACCENT, NEGATIVE, "#F4A261", "#4C78A8"],
            ),
            use_container_width=True,
            config=CHART_CONFIG,
        )
    st.markdown('</div>', unsafe_allow_html=True)

with tab_moneter:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["moneter"], BLOCK_NOTES["moneter"])
    render_table_block(workbook["moneter"], block_key="moneter")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_fiskal:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["fiskal"], BLOCK_NOTES["fiskal"])
    render_table_block(workbook["fiskal"], block_key="fiskal")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Optional preview ----------
with st.expander("Lihat struktur sumber Excel"):
    info = pd.DataFrame({
        "Sumber": [REPO_FILE_NAME, "st.secrets['github_raw_xlsx_url'] (opsional)"],
        "Keterangan": [
            "File diletakkan di repo yang sama dengan app.py sehingga otomatis terbaca saat deploy Streamlit dari GitHub.",
            "Dipakai hanya bila file Excel tidak diletakkan langsung di repo lokal."
        ],
    })
    st.dataframe(info, use_container_width=True, hide_index=True)

if show_preview:
    with st.expander("Preview data yang berhasil dimuat", expanded=False):
        tab_names = ["Simulasi", "Makro", "PDB Nominal", "PDB YoY", "PDB QtQ", "Moneter", "Fiskal"]
        tabs = st.tabs(tab_names)
        preview_keys = [
            workbook["simulasi"],
            workbook["makro"],
            workbook["pdb"],
            filter_growth_rows(pdb_tables.get("yoy", empty_df("pdb"))) if pdb_tables else empty_df("pdb"),
            filter_growth_rows(pdb_tables.get("qtq", empty_df("pdb"))) if pdb_tables else empty_df("pdb"),
            workbook["moneter"],
            workbook["fiskal"],
        ]
        for tab, df in zip(tabs, preview_keys):
            with tab:
                st.dataframe(df, use_container_width=True, hide_index=True)
        if pdb_history is not None:
            st.markdown("### Preview historis komponen PDB")
            st.dataframe(pdb_history["level"], use_container_width=True, hide_index=True)
            st.markdown("### Preview pertumbuhan komponen PDB")
            st.dataframe(pdb_history["growth"], use_container_width=True, hide_index=True)
