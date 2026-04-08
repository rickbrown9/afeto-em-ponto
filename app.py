import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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
    .status-pago    { color: #2e7d32; font-weight: 600; }
    .status-parcial { color: #e65100; font-weight: 600; }
    .status-pendente{ color: #c62828; font-weight: 600; }
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
    with st.expander("Ver instruções rápidas"):
        st.markdown("""
1. Siga o `SETUP.md` para criar a Service Account no Google Cloud
2. Preencha o `.streamlit/secrets.toml` com as credenciais
3. Crie a planilha Google Sheets e compartilhe com o e-mail da Service Account
4. Rode `python seed_data.py` para popular os dados iniciais
5. Reinicie o app
        """)
    st.stop()

# ── Carrega dados ──────────────────────────────────────────────────────────────
pedidos = read_sheet("pedidos")

MES_ATUAL = datetime.now().strftime("%Y-%m")
MES_NOMES = {
    "2026-01": "Janeiro", "2026-02": "Fevereiro", "2026-03": "Março",
    "2026-04": "Abril",   "2026-05": "Maio",       "2026-06": "Junho",
    "2026-07": "Julho",   "2026-08": "Agosto",     "2026-09": "Setembro",
    "2026-10": "Outubro", "2026-11": "Novembro",   "2026-12": "Dezembro",
}

def nome_mes(m: str) -> str:
    return MES_NOMES.get(m, m)

if pedidos.empty:
    st.info("Nenhum pedido cadastrado ainda. Acesse a página **Financeiro** para adicionar.")
    st.stop()

# Converte valores numéricos
pedidos["valor_total"] = pd.to_numeric(pedidos["valor_total"], errors="coerce").fillna(0)
pedidos["valor_pago"]  = pd.to_numeric(pedidos["valor_pago"],  errors="coerce").fillna(0)
pedidos["pendente"]    = pedidos["valor_total"] - pedidos["valor_pago"]

# ── Filtro de mês no topo ──────────────────────────────────────────────────────
meses_disponiveis = sorted(pedidos["mes_ref"].dropna().unique().tolist(), reverse=True)
col_sel, _ = st.columns([2, 5])
with col_sel:
    mes_sel = st.selectbox(
        "Mês",
        options=meses_disponiveis,
        format_func=nome_mes,
        index=0,
    )

df = pedidos[pedidos["mes_ref"] == mes_sel]

# ── Métricas principais ────────────────────────────────────────────────────────
fat   = df["valor_total"].sum()
pago  = df["valor_pago"].sum()
pend  = df["pendente"].sum()
nv    = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturado",   f"R$ {fat:,.0f}".replace(",", "."), f"{nv} vendas")
c2.metric("Recebido",   f"R$ {pago:,.0f}".replace(",", "."))
c3.metric("Pendente",   f"R$ {pend:,.0f}".replace(",", "."))
c4.metric("Receb. %",   f"{(pago/fat*100):.0f}%" if fat else "—")

st.divider()

# ── Gráficos ───────────────────────────────────────────────────────────────────
col_bar, col_pie = st.columns([3, 2])

# Barras: evolução mensal
with col_bar:
    st.subheader("Evolução mensal")
    resumo = (
        pedidos.groupby("mes_ref")
        .agg(Faturado=("valor_total", "sum"), Recebido=("valor_pago", "sum"))
        .reset_index()
        .sort_values("mes_ref")
    )
    resumo["Mês"] = resumo["mes_ref"].map(nome_mes)
    fig_bar = go.Figure()
    fig_bar.add_bar(x=resumo["Mês"], y=resumo["Faturado"], name="Faturado",
                    marker_color="#D4956A")
    fig_bar.add_bar(x=resumo["Mês"], y=resumo["Recebido"], name="Recebido",
                    marker_color="#8B4513")
    fig_bar.update_layout(
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=10, b=0, l=0, r=0),
        yaxis_tickprefix="R$ ",
        height=300,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Pizza: status do mês selecionado
with col_pie:
    st.subheader(f"Status — {nome_mes(mes_sel)}")
    status_counts = df.groupby("status_pagamento")["valor_total"].sum().reset_index()
    status_counts.columns = ["Status", "Valor"]
    color_map = {"pago": "#2e7d32", "parcial": "#e65100", "pendente": "#c62828"}
    fig_pie = px.pie(
        status_counts,
        names="Status",
        values="Valor",
        color="Status",
        color_discrete_map=color_map,
        hole=0.4,
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=0, l=0, r=0),
        height=300,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ── Tabela de pedidos do mês ───────────────────────────────────────────────────
st.subheader(f"Pedidos — {nome_mes(mes_sel)}")

STATUS_EMOJI = {"pago": "✅ Pago", "parcial": "🟡 Sinal", "pendente": "🔴 Pendente"}

display = df[["contato_nome", "descricao", "valor_total", "valor_pago", "pendente", "status_pagamento"]].copy()
display.columns = ["Cliente", "Descrição", "Total (R$)", "Pago (R$)", "Falta (R$)", "Status"]
display["Status"] = display["Status"].map(STATUS_EMOJI).fillna(display["Status"])
display["Total (R$)"] = display["Total (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
display["Pago (R$)"]  = display["Pago (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
display["Falta (R$)"] = display["Falta (R$)"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))

st.dataframe(display, use_container_width=True, hide_index=True)
