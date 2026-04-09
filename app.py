import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
from utils.sheets import read_sheet, is_configured

st.set_page_config(
    page_title="Afeto em Ponto",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetricValue"] { color: #8B4513 !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
    h1 { color: #8B4513 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧵 Afeto em Ponto")

# ── Verificação de configuração ────────────────────────────────────────────────
if not is_configured():
    st.warning(
        "Sistema ainda não configurado com Google Sheets. "
        "Siga o arquivo **SETUP.md** para conectar o banco de dados."
    )
    st.stop()

# ── Carrega dados ──────────────────────────────────────────────────────────────
pedidos = read_sheet("pedidos")

MES_NOMES = {
    "2026-01": "Janeiro", "2026-02": "Fevereiro", "2026-03": "Março",
    "2026-04": "Abril",   "2026-05": "Maio",       "2026-06": "Junho",
    "2026-07": "Julho",   "2026-08": "Agosto",     "2026-09": "Setembro",
    "2026-10": "Outubro", "2026-11": "Novembro",   "2026-12": "Dezembro",
}

def nome_mes(m: str) -> str:
    return MES_NOMES.get(m, m)

def extrair_qtd(row) -> int:
    """Lê qtd_pecas; se vazio, tenta extrair do campo descricao."""
    v = str(row.get("qtd_pecas", "")).strip()
    if v.isdigit():
        return int(v)
    m = re.search(r"(\d+)\s*pe[çc]", str(row.get("descricao", "")), re.IGNORECASE)
    return int(m.group(1)) if m else 1

if pedidos.empty:
    st.info("Nenhum pedido cadastrado ainda. Acesse a página **Financeiro** para adicionar.")
    st.stop()

# Converte valores numéricos
pedidos["valor_total"] = pd.to_numeric(pedidos["valor_total"], errors="coerce").fillna(0)
pedidos["valor_pago"]  = pd.to_numeric(pedidos["valor_pago"],  errors="coerce").fillna(0)
pedidos["pendente"]    = pedidos["valor_total"] - pedidos["valor_pago"]
pedidos["qtd"]         = pedidos.apply(extrair_qtd, axis=1)

# ── Filtro de mês ──────────────────────────────────────────────────────────────
meses_disponiveis = sorted(pedidos["mes_ref"].dropna().unique().tolist(), reverse=True)
col_sel, _ = st.columns([2, 5])
with col_sel:
    mes_sel = st.selectbox("Mês", options=meses_disponiveis, format_func=nome_mes, index=0)

df = pedidos[pedidos["mes_ref"] == mes_sel]

# ── Métricas ───────────────────────────────────────────────────────────────────
fat        = df["valor_total"].sum()
pago       = df["valor_pago"].sum()
pend       = df["pendente"].sum()
nv         = len(df)
total_pecas = df["qtd"].sum()
media_pecas = round(df["qtd"].mean(), 1) if nv else 0
ticket_medio = round(fat / nv, 0) if nv else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Faturado",        f"R$ {fat:,.0f}".replace(",", "."),  f"{nv} vendas")
c2.metric("Recebido",        f"R$ {pago:,.0f}".replace(",", "."))
c3.metric("Pendente",        f"R$ {pend:,.0f}".replace(",", "."))
c4.metric("Receb. %",        f"{(pago/fat*100):.0f}%" if fat else "—")
c5.metric("Bordados no mês", f"{total_pecas} peças",             f"{media_pecas} por venda")
c6.metric("Ticket médio",    f"R$ {ticket_medio:,.0f}".replace(",", "."), f"por pedido")

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
col_bar, col_pie = st.columns([3, 2])

with col_bar:
    st.subheader("Evolução mensal")
    resumo = (
        pedidos.groupby("mes_ref")
        .agg(
            Faturado=("valor_total", "sum"),
            Recebido=("valor_pago", "sum"),
            Pecas=("qtd", "sum"),
        )
        .reset_index()
        .sort_values("mes_ref")
    )
    resumo["Mês"] = resumo["mes_ref"].map(nome_mes)

    fig_bar = go.Figure()
    fig_bar.add_bar(x=resumo["Mês"], y=resumo["Faturado"], name="Faturado",  marker_color="#D4956A")
    fig_bar.add_bar(x=resumo["Mês"], y=resumo["Recebido"], name="Recebido",  marker_color="#8B4513")
    fig_bar.update_layout(
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=10, b=0, l=0, r=0),
        yaxis_tickprefix="R$ ",
        height=280,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Gráfico de barras: bordados por mês
    st.subheader("Bordados por mês")
    fig_pecas = go.Figure()
    fig_pecas.add_bar(x=resumo["Mês"], y=resumo["Pecas"], name="Peças", marker_color="#C4956A")
    fig_pecas.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=0, l=0, r=0),
        yaxis_title="Nº de peças",
        height=220,
    )
    st.plotly_chart(fig_pecas, use_container_width=True)

with col_pie:
    st.subheader(f"Status — {nome_mes(mes_sel)}")
    status_counts = df.groupby("status_pagamento")["valor_total"].sum().reset_index()
    status_counts.columns = ["Status", "Valor"]
    color_map = {"pago": "#2e7d32", "parcial": "#e65100", "pendente": "#c62828"}
    fig_pie = px.pie(
        status_counts, names="Status", values="Valor",
        color="Status", color_discrete_map=color_map, hole=0.4,
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=0, l=0, r=0), height=280,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # Distribuição de peças por pedido
    st.subheader(f"Peças por pedido — {nome_mes(mes_sel)}")
    fig_dist = px.bar(
        df.sort_values("qtd", ascending=False),
        x="contato_nome", y="qtd",
        color="status_pagamento",
        color_discrete_map=color_map,
        labels={"contato_nome": "Cliente", "qtd": "Peças", "status_pagamento": "Status"},
    )
    fig_dist.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=0, l=0, r=0),
        showlegend=False,
        height=220,
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig_dist, use_container_width=True)

st.divider()

# ── Tabela de pedidos do mês ───────────────────────────────────────────────────
st.subheader(f"Pedidos — {nome_mes(mes_sel)}")

STATUS_EMOJI = {"pago": "✅ Pago", "parcial": "🟡 Sinal", "pendente": "🔴 Pendente"}

display = df[["contato_nome", "descricao", "qtd", "valor_total", "valor_pago", "pendente", "status_pagamento"]].copy()
display.columns = ["Cliente", "Descrição", "Peças", "Total (R$)", "Pago (R$)", "Falta (R$)", "Status"]
display["Status"]     = display["Status"].map(STATUS_EMOJI).fillna(display["Status"])
display["Total (R$)"] = display["Total (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
display["Pago (R$)"]  = display["Pago (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
display["Falta (R$)"] = display["Falta (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))

st.dataframe(display, use_container_width=True, hide_index=True)
