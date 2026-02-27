import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import subprocess
import sys

DB_PATH = Path("data/prices.db")

st.set_page_config(page_title="Monitor PS5 Pro", layout="wide")
st.title("Monitoramento de Preços — PS5 Pro")

# --- ações ---
colA, colB, colC = st.columns([1, 1, 2])

with colA:
    if st.button("Coletar agora"):
        subprocess.run([sys.executable, "-m", "src.run_collect"], check=False)
        st.success("Coleta executada! Atualize/aguarde a tela recarregar.")

with colB:
    auto_refresh = st.checkbox("Auto-atualizar (10s)", value=False)

if auto_refresh:
    st.rerun()

# --- carregar dados ---
def load_data() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT ts, site, title, seller, price, shipping, available, image_url, url, raw
            FROM price_history
            ORDER BY ts DESC
            LIMIT 5000
            """,
            conn,
        )
    return df

df = load_data()

if df.empty:
    st.info("Sem dados ainda. Clique em **Coletar agora** ou rode `python -m src.run_collect`.")
    st.stop()

# --- tratamento ---
df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
df["available"] = df["available"].fillna(0).astype(int)

def brl(x) -> str:
    try:
        return f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"

# ==============================
# LABELS (NOMES BONITOS PRA UI)
# ==============================
SITE_LABELS = {
    "mercadolivre": "Mercado Livre",
    "amazon": "Amazon",
    "magalu": "Magazine Luiza",
    "kabum": "KaBuM!",
    "shopee": "Shopee",
    "carrefour": "Carrefour",
    "casasbahia": "Casas Bahia",
    "extra": "Extra",
}

def label_site(site: str) -> str:
    # fallback: capitaliza caso não esteja no dicionário
    return SITE_LABELS.get(site, str(site).replace("_", " ").title())

# ==============================
# SIDEBAR - FILTROS (ESQUERDA)
# ==============================
st.sidebar.header("Filtros")

sites = sorted(df["site"].dropna().unique().tolist())

# Mostra labels amigáveis, mas mantém o valor técnico internamente
labels = ["Todos"] + [label_site(s) for s in sites]
selected_label = st.sidebar.selectbox("Marketplace", labels)

if selected_label == "Todos":
    selected_site = "Todos"
else:
    # recupera o "site técnico" a partir do label escolhido
    selected_site = sites[labels.index(selected_label) - 1]  # -1 por causa do "Todos"

only_available = st.sidebar.checkbox("Apenas disponíveis", value=False)

sort_option = st.sidebar.selectbox(
    "Ordenar por",
    ["Mais recente", "Menor preço", "Maior preço"]
)

# ==============================
# APLICAR FILTROS
# ==============================
df_f = df.copy()

# Filtro marketplace
if selected_site != "Todos":
    df_f = df_f[df_f["site"] == selected_site]

# Filtro disponibilidade
if only_available:
    df_f = df_f[df_f["available"] == 1]

# Ordenação
if sort_option == "Mais recente":
    df_f = df_f.sort_values("ts", ascending=False)
elif sort_option == "Menor preço":
    df_f = df_f.sort_values("price", ascending=True, na_position="last")
elif sort_option == "Maior preço":
    df_f = df_f.sort_values("price", ascending=False, na_position="last")

# --- sessão: produto atual (imagem + marketplace + preço) ---
st.subheader("Produto monitorado (atual)")

latest = (
    df_f.dropna(subset=["price"])
       .sort_values("ts", ascending=False)
       .head(1)
)

if latest.empty:
    st.info("Sem registro com preço ainda. Clique em **Coletar agora**.")
else:
    r = latest.iloc[0]
    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        img = r.get("image_url")
        if isinstance(img, str) and img.strip():
            st.image(img, use_container_width=True)
        else:
            st.info("Sem imagem disponível.")

    with c2:
        st.markdown("**Marketplace**")
        st.write(label_site(r.get("site")) if r.get("site") else "-")

        st.markdown("**Preço atual**")
        st.write(brl(r.get("price")))

        st.markdown("**Coletado em (UTC)**")
        st.write(str(r.get("ts")))

        url = r.get("url")
        if isinstance(url, str) and url.strip():
            st.link_button("Abrir anúncio", url)

    with c3:
        st.markdown("**Produto**")
        st.write(r.get("title") or "-")
        if r.get("seller"):
            st.markdown("**Vendedor**")
            st.write(r.get("seller"))

# --- métricas ---
st.subheader("Resumo")

col1, col2, col3, col4 = st.columns(4)

last_row = df_f.dropna(subset=["price"]).sort_values("ts").tail(1)
last_price = last_row["price"].iloc[0] if len(last_row) else None
last_time = last_row["ts"].iloc[0] if len(last_row) else None

min_price = df_f["price"].min()
max_price = df_f["price"].max()
count_rows = len(df_f)

col1.metric("Registros", f"{count_rows:,}".replace(",", "."))
col2.metric("Menor preço", brl(min_price) if pd.notna(min_price) else "-")
col3.metric("Maior preço", brl(max_price) if pd.notna(max_price) else "-")
col4.metric("Último preço", brl(last_price) if last_price is not None else "-")

st.caption(f"Última coleta (UTC): {last_time} (se aparecer vazio, rode uma coleta).")

# --- tabela ---
st.subheader("Últimos registros")
st.dataframe(
    df_f[["ts", "site", "image_url", "title", "price", "shipping", "available", "url"]].head(50),
    use_container_width=True,
    column_config={
        "image_url": st.column_config.ImageColumn("Foto", width="small"),
        "url": st.column_config.LinkColumn("Link", display_text="Abrir"),
        "site": st.column_config.TextColumn("Marketplace"),
    },
)

st.caption("Observação: na tabela o campo 'site' ainda é o valor técnico (ex.: mercadolivre). Se quiser, eu ajusto para mostrar o label bonito também.")

# --- gráfico ---
st.subheader("Evolução do preço")
chart_df = df_f.dropna(subset=["price"]).sort_values("ts")
if len(chart_df) < 2:
    st.info("Ainda há poucos pontos para um gráfico. Faça mais coletas ao longo do tempo.")
else:
    st.line_chart(chart_df.set_index("ts")[["price"]])

st.divider()
st.caption("Dica: para auto-atualizar de verdade a cada 10s, instale `streamlit-autorefresh`.")