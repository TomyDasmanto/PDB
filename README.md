# Dashboard Model Framework (Streamlit + Plotly)

Folder ini berisi kerangka awal dashboard Streamlit:
- Hasil Simulasi PDB & Kesejahteraan
- Blok Makro (kiri)
- Accounting / PDB (tengah)
- Blok Moneter (kanan)
- Blok Fiskal (bawah tengah)

## File
- `app.py` -> aplikasi Streamlit utama
- `requirements.txt` -> dependensi

## Menjalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struktur Excel yang dibaca
Workbook diharapkan memiliki sheet berikut:
- `simulasi`
- `makro`
- `pdb`
- `moneter`
- `fiskal`

Setiap sheet minimal memiliki kolom:
- `indikator`
- `baseline`
- `output Q1`
- `output Q1`
- `output Q1`
- `output Q1`

