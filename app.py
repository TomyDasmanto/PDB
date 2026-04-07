import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

st.set_page_config(
    page_title="Model Framework Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Konfigurasi sumber file ----------
# Opsi 1 (paling mudah untuk Streamlit dari GitHub):
# Letakkan file `dashboard PDB.xlsx` di root repo yang sama dengan app.py.
REPO_FILE_NAME = "dashboard PDB.xlsx"

# Opsi 2 (opsional): isi RAW URL GitHub jika file tidak disimpan lokal di repo.
# Contoh: https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dashboard%20PDB.xlsx
GITHUB_RAW_XLSX_URL = st.secrets.get("github_raw_xlsx_url", "") if hasattr(st, "secrets") else ""

# ---------- Styling ----------
PRIMARY = "#3E6DB5"
ACCENT = "#E07B39"
CELL_A = "#D7DBEA"
CELL_B = "#E8EBF4"
CELL_ORANGE = "#EFD9CF"
BG = "#F6F7FB"
TEXT = "#1F2937"
GRID = "rgba(31,41,55,0.12)"

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
    "pdb": ["Konsumsi RT", "Konsumsi LNPRT", "PMTB", "Change in Stocks", "Ekspor", "Impor"],
    "moneter": ["PUAB", "Kredit", "DPK", "M0", "OMO"],
    "fiskal": ["Pendapatan", "Belanja", "Pembiayaan", "Defisit"],
}

BLOCK_TITLES = {
    "simulasi": "Hasil Simulasi PDB & Kesejahteraan",
    "makro": "Blok Makro",
    "pdb": "Accounting / PDB",
    "moneter": "Blok Moneter",
    "fiskal": "Blok Fiskal",
}

BLOCK_NOTES = {
    "simulasi": "Tabel utama untuk membaca hasil simulasi PDB dan kesejahteraan per periode proyeksi.",
    "makro": "Tabel indikator makro per periode proyeksi.",
    "pdb": "Accounting / PDB dibaca otomatis dari file GitHub `dashboard PDB.xlsx`. Tabel hanya menampilkan proyeksi 2026: Outlook Q1–Q4 dan Full Year, memakai nama komponen asli dari file Excel.",
    "moneter": "Tabel variabel moneter per periode proyeksi.",
    "fiskal": "Tabel komponen fiskal per periode proyeksi.",
}

PDB_COMPONENTS = ["Konsumsi RT", "Konsumsi LNPRT", "PMTB", "Change in Stocks", "Ekspor", "Impor"]

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
        .section-card {{
            border: 1px solid rgba(62,109,181,0.14);
            border-radius: 14px;
            padding: 0.7rem 0.8rem 0.5rem 0.8rem;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            margin-bottom: 0.9rem;
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


def coerce_schema(df: pd.DataFrame, block: str) -> pd.DataFrame:
    df = normalize_columns(df)
    expected = EXPECTED_SHEETS[block]
    if "indikator" not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "indikator"})
    for col in expected:
        if col not in df.columns:
            df[col] = None
    return df[expected].copy()


def open_excel_source(source):
    if isinstance(source, (bytes, bytearray)):
        return pd.ExcelFile(BytesIO(source), engine="openpyxl")
    return pd.ExcelFile(source, engine="openpyxl")


def detect_excel_source() -> Tuple[Optional[object], str]:
    local_path = Path(__file__).resolve().parent / REPO_FILE_NAME
    if local_path.exists():
        return str(local_path), f"Sumber data otomatis: file lokal repo `{REPO_FILE_NAME}`"
    if GITHUB_RAW_XLSX_URL:
        return GITHUB_RAW_XLSX_URL, "Sumber data otomatis: GitHub Raw URL dari st.secrets['github_raw_xlsx_url']"
    return None, (
        "File Excel belum ditemukan. Simpan `dashboard PDB.xlsx` di root repo yang sama dengan `app.py`, "
        "atau isi `st.secrets['github_raw_xlsx_url']` dengan raw URL GitHub file tersebut."
    )


def derive_pdb_from_realisasi(source):
    xls = open_excel_source(source)
    sheet_map = {s.lower().strip(): s for s in xls.sheet_names}
    if "realisasi" not in sheet_map:
        return empty_df("pdb"), None

    df = pd.read_excel(xls, sheet_name=sheet_map["realisasi"], engine="openpyxl")
    if df.empty:
        return empty_df("pdb"), None

    date_col = df.columns[0]
    df = df.rename(columns={date_col: "tanggal"}).copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df = df.dropna(subset=["tanggal"]).sort_values("tanggal")

    available = [c for c in PDB_COMPONENTS if c in df.columns]
    if not available:
        return empty_df("pdb"), None

    for c in available:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["year"] = df["tanggal"].dt.year
    df["quarter"] = df["tanggal"].dt.quarter

    data_2026 = df[df["year"] == 2026].copy()
    quarter_name_map = {1: "out_tw1", 2: "out_tw2", 3: "out_tw3", 4: "out_tw4"}

    rows = []
    for comp in PDB_COMPONENTS:
        row = {"indikator": comp, "out_tw1": None, "out_tw2": None, "out_tw3": None, "out_tw4": None, "full_year": None}
        if comp in data_2026.columns:
            for q in [1, 2, 3, 4]:
                qdf = data_2026[data_2026["quarter"] == q]
                if not qdf.empty:
                    row[quarter_name_map[q]] = qdf.iloc[0][comp]
            row["full_year"] = data_2026[comp].sum(min_count=1)
        rows.append(row)
    table = pd.DataFrame(rows)

    hist_cols = [c for c in PDB_COMPONENTS if c in df.columns]
    hist = df.melt(id_vars="tanggal", value_vars=hist_cols, var_name="komponen", value_name="nilai")
    hist = hist.dropna(subset=["nilai"]).sort_values(["komponen", "tanggal"])
    return table, hist


def load_dashboard_data():
    data = {k: empty_df(k) for k in EXPECTED_SHEETS.keys()}
    hist_pdb = None
    source, source_status = detect_excel_source()
    if source is None:
        return data, hist_pdb, source_status

    try:
        xls = open_excel_source(source)
        lower_sheet_map = {s.lower().strip(): s for s in xls.sheet_names}

        for block in ["simulasi", "makro", "moneter", "fiskal"]:
            if block in lower_sheet_map:
                df = pd.read_excel(xls, sheet_name=lower_sheet_map[block], engine="openpyxl")
                data[block] = coerce_schema(df, block)

        if "realisasi" in lower_sheet_map:
            data["pdb"], hist_pdb = derive_pdb_from_realisasi(source)
        elif "pdb" in lower_sheet_map:
            df = pd.read_excel(xls, sheet_name=lower_sheet_map["pdb"], engine="openpyxl")
            data["pdb"] = coerce_schema(df, "pdb")

        return data, hist_pdb, source_status
    except Exception as e:
        return data, hist_pdb, f"Gagal membaca sumber Excel otomatis: {e}"


def format_display(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    ordered_cols = ["indikator", *PERIOD_ORDER]
    for c in ordered_cols:
        if c not in view.columns:
            view[c] = None
    view = view[ordered_cols].rename(columns={"indikator": "Indikator", **PERIOD_MAP})
    return view.fillna("—")


def make_table(df: pd.DataFrame, header_fill: str, row_fill_1: str, row_fill_2: str, first_col_width=210, other_col_width=110, height=320):
    view = format_display(df)
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


def make_pdb_history_chart(hist_df: Optional[pd.DataFrame], selected_components: list[str]):
    if hist_df is None or hist_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Data historis PDB belum tersedia pada sumber Excel otomatis.",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
            font=dict(size=14, color="#6B7280")
        )
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    plot_df = hist_df[hist_df["komponen"].isin(selected_components)].copy()
    if plot_df.empty:
        plot_df = hist_df.copy()

    fig = px.line(
        plot_df,
        x="tanggal",
        y="nilai",
        color="komponen",
        markers=True,
        color_discrete_sequence=[PRIMARY, ACCENT, "#2A9D8F", "#8A5CF6", "#D14D72", "#F4A261"],
    )
    fig.update_traces(
        mode="lines+markers",
        line=dict(width=2.6),
        marker=dict(size=5.5),
        hovertemplate="<b>%{fullData.name}</b><br>%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
    )
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
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig


def block_card(title: str, note: Optional[str] = None):
    st.markdown(f'<div class="block-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)


def render_table_block(block_df: pd.DataFrame, accent: bool = False, block_key: str = ""):
    st.plotly_chart(
        make_table(
            block_df,
            ACCENT if accent else PRIMARY,
            CELL_ORANGE if accent else CELL_A,
            "#F4E5DE" if accent else CELL_B,
            first_col_width=230 if block_key == "pdb" else 210,
            other_col_width=112,
            height=300 if block_key == "simulasi" else 320,
        ),
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False},
    )


# ---------- Load otomatis dari repo/GitHub ----------
workbook, pdb_history, source_status = load_dashboard_data()

# ---------- Sidebar ----------
st.sidebar.markdown("## Pengaturan Dashboard")
show_preview = st.sidebar.toggle("Tampilkan preview data mentah", value=False)
st.sidebar.markdown("### Sumber Data")
st.sidebar.info(source_status)

# ---------- Header ----------
st.title("Dashboard Model Framework")
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
    "Accounting / PDB",
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
    render_table_block(workbook["pdb"], block_key="pdb")

    st.markdown("<div class='chart-note'>Grafik historis menggunakan nama komponen asli dari file Excel: Konsumsi RT, Konsumsi LNPRT, PMTB, Change in Stocks, Ekspor, dan Impor.</div>", unsafe_allow_html=True)
    selected_components = st.multiselect(
        "Pilih komponen historis yang ingin ditampilkan",
        options=PDB_COMPONENTS,
        default=PDB_COMPONENTS,
        key="hist_components_pdb",
    )
    selected_components = selected_components or PDB_COMPONENTS
    st.plotly_chart(
        make_pdb_history_chart(pdb_history, selected_components),
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False},
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
        tab_names = ["Simulasi", "Makro", "PDB", "Moneter", "Fiskal"]
        tabs = st.tabs(tab_names)
        for tab, key in zip(tabs, ["simulasi", "makro", "pdb", "moneter", "fiskal"]):
            with tab:
                st.dataframe(workbook[key], use_container_width=True, hide_index=True)
        if pdb_history is not None:
            st.markdown("### Preview historis komponen PDB")
            st.dataframe(pdb_history, use_container_width=True, hide_index=True)
