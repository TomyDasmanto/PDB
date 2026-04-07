import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Model Framework Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
PRIMARY = "#3E6DB5"
ACCENT = "#E07B39"
CELL_A = "#D7DBEA"
CELL_B = "#E8EBF4"
CELL_ORANGE = "#EFD9CF"
BG = "#F6F7FB"
TEXT = "#1F2937"

PERIOD_MAP = {
    "baseline": "Baseline",
    "out_tw1": "Outlook Q1",
    "out_tw2": "Outlook Q2",
    "out_tw3": "Outlook Q3",
    "out_tw4": "Outlook Q4",
    "full_year": "Full Year",
}
PERIOD_ORDER = list(PERIOD_MAP.keys())

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
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Config ----------
EXPECTED_SHEETS = {
    "simulasi": ["indikator", "baseline", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "makro": ["indikator", "baseline", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "pdb": ["indikator", "baseline", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "moneter": ["indikator", "baseline", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
    "fiskal": ["indikator", "baseline", "out_tw1", "out_tw2", "out_tw3", "out_tw4", "full_year"],
}

DEFAULT_ROWS = {
    "simulasi": ["Consumption", "Investment", "Govt. Spending", "Export", "Import", "Unemployment"],
    "makro": ["Inflasi", "Rupiah", "Yield SBN", "ICP", "Nikel", "Coal", "CPO", "Lifting"],
    "pdb": ["Konsumsi RT", "Konsumsi LNPRT", "PKP", "PMTB", "Ekspor", "Impor", "Change in Stock", "Statistical Discrepancy", "PDB Agregate"],
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
    "simulasi": "Tabel utama untuk membaca hasil simulasi PDB dan kesejahteraan per periode.",
    "makro": "Tabel indikator makro per periode.",
    "pdb": "Tabel komponen accounting / PDB per periode.",
    "moneter": "Tabel variabel moneter per periode.",
    "fiskal": "Tabel komponen fiskal per periode.",
}

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
    return pd.DataFrame({
        "indikator": rows,
        "baseline": [None] * len(rows),
        "out_tw1": [None] * len(rows),
        "out_tw2": [None] * len(rows),
        "out_tw3": [None] * len(rows),
        "out_tw4": [None] * len(rows),
        "full_year": [None] * len(rows),
    })


def coerce_schema(df: pd.DataFrame, block: str) -> pd.DataFrame:
    df = normalize_columns(df)
    expected = EXPECTED_SHEETS[block]
    if "indikator" not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "indikator"})
    for col in expected:
        if col not in df.columns:
            df[col] = None
    return df[expected].copy()


def load_workbook(uploaded_file) -> dict:
    if uploaded_file is None:
        return {k: empty_df(k) for k in EXPECTED_SHEETS.keys()}

    data = {}
    xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
    lower_sheet_map = {s.lower().strip(): s for s in xls.sheet_names}

    for block in EXPECTED_SHEETS.keys():
        matched_sheet = None
        for candidate in [block, block.capitalize(), block.upper()]:
            if candidate.lower().strip() in lower_sheet_map:
                matched_sheet = lower_sheet_map[candidate.lower().strip()]
                break
        if matched_sheet:
            df = pd.read_excel(xls, sheet_name=matched_sheet, engine="openpyxl")
            data[block] = coerce_schema(df, block)
        else:
            data[block] = empty_df(block)
    return data


def format_display(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    ordered_cols = ["indikator", *PERIOD_ORDER]
    view = view[ordered_cols].rename(columns={"indikator": "Indikator", **PERIOD_MAP})
    return view.fillna("—")


def make_table(df: pd.DataFrame, header_fill: str, row_fill_1: str, row_fill_2: str, first_col_width=170, other_col_width=105, height=320):
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


def block_card(title: str, note: str | None = None):
    st.markdown(f'<div class="block-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)


def render_block(block_key: str, accent: bool = False):
    df = workbook[block_key]
    st.plotly_chart(
        make_table(
            df,
            ACCENT if accent else PRIMARY,
            CELL_ORANGE if accent else CELL_A,
            "#F4E5DE" if accent else CELL_B,
            first_col_width=220 if block_key == "simulasi" else 170,
            other_col_width=105,
            height=300 if block_key == "simulasi" else 320,
        ),
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False},
    )


# ---------- Sidebar ----------
st.sidebar.markdown("## Pengaturan Dashboard")
uploaded = st.sidebar.file_uploader("Unggah file Excel (.xlsx)", type=["xlsx"])
show_preview = st.sidebar.toggle("Tampilkan preview data mentah", value=False)

workbook = load_workbook(uploaded)

# ---------- Header ----------
st.title("Dashboard Model Framework")
st.markdown("---")

# ---------- Main Simulation Block ----------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
block_card("Tabel Utama — Hasil Simulasi PDB & Kesejahteraan", BLOCK_NOTES["simulasi"])
render_block("simulasi", accent=True)
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
    render_block("makro")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_pdb:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["pdb"], BLOCK_NOTES["pdb"])
    render_block("pdb")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_moneter:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["moneter"], BLOCK_NOTES["moneter"])
    render_block("moneter")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_fiskal:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    block_card(BLOCK_TITLES["fiskal"], BLOCK_NOTES["fiskal"])
    render_block("fiskal")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Optional preview ----------
with st.expander("Lihat struktur sheet Excel yang diharapkan"):
    info = pd.DataFrame({
        "Sheet": list(EXPECTED_SHEETS.keys()),
        "Kolom Wajib": [", ".join(v) for v in EXPECTED_SHEETS.values()],
        "Contoh baris indikator": [", ".join(DEFAULT_ROWS[k][:4]) + ("..." if len(DEFAULT_ROWS[k]) > 4 else "") for k in EXPECTED_SHEETS.keys()],
    })
    st.dataframe(info, use_container_width=True, hide_index=True)

if show_preview:
    with st.expander("Preview data yang berhasil dimuat", expanded=False):
        tab_names = ["Simulasi", "Makro", "PDB", "Moneter", "Fiskal"]
        tabs = st.tabs(tab_names)
        for tab, key in zip(tabs, ["simulasi", "makro", "pdb", "moneter", "fiskal"]):
            with tab:
                st.dataframe(workbook[key], use_container_width=True, hide_index=True)
