import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from utils.sheets import read_sheet, append_row, update_row, is_configured

st.set_page_config(page_title="CMV — Afeto em Ponto", page_icon="📦", layout="wide")
st.title("📦 CMV — Custo de Mercadoria Vendida")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

MES_NOMES = {
    "2026-01": "Janeiro", "2026-02": "Fevereiro", "2026-03": "Março",
    "2026-04": "Abril",   "2026-05": "Maio",       "2026-06": "Junho",
    "2026-07": "Julho",   "2026-08": "Agosto",     "2026-09": "Setembro",
    "2026-10": "Outubro", "2026-11": "Novembro",   "2026-12": "Dezembro",
}

# ── CMV padrão ─────────────────────────────────────────────────────────────────
CMV_PADRAO = {
    "Bastidor":      13.00,
    "Linha":          2.50,
    "Tecido":         2.50,
    "Caixa + seda":   3.00,
    "Etiqueta":       1.50,
    "Impressão":      2.00,
}
CUSTO_MIDIA_PADRAO = 300.00


def extrair_qtd(row) -> int:
    v = str(row.get("qtd_pecas", "")).strip()
    if v.isdigit():
        return int(v)
    m = re.search(r"(\d+)\s*pe[çc]", str(row.get("descricao", "")), re.IGNORECASE)
    return int(m.group(1)) if m else 1


def carregar_cmv_config() -> tuple[dict, float]:
    """Retorna (custos_por_peca, custo_midia). Usa padrão se vazio."""
    try:
        df = read_sheet("cmv_config")
        if df.empty:
            return dict(CMV_PADRAO), CUSTO_MIDIA_PADRAO
        custos = {}
        midia = CUSTO_MIDIA_PADRAO
        for _, row in df.iterrows():
            try:
                if row["item"] == "__midia__":
                    midia = float(row["valor"])
                else:
                    custos[row["item"]] = float(row["valor"])
            except Exception:
                pass
        return (custos if custos else dict(CMV_PADRAO)), midia
    except Exception:
        return dict(CMV_PADRAO), CUSTO_MIDIA_PADRAO


def salvar_cmv_config(custos: dict, midia: float):
    """Substitui toda a config de CMV no Sheets."""
    from utils.sheets import _worksheet, read_sheet as rs, COLUMNS
    from datetime import datetime
    import uuid
    ws = _worksheet("cmv_config")
    existing = rs("cmv_config")
    if not existing.empty:
        for i in range(len(existing), 0, -1):
            ws.delete_rows(i + 1)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for item, valor in custos.items():
        ws.append_row([str(uuid.uuid4())[:8].upper(), item, str(valor), now], value_input_option="USER_ENTERED")
    # Custo de mídia salvo com chave especial
    ws.append_row([str(uuid.uuid4())[:8].upper(), "__midia__", str(midia), now], value_input_option="USER_ENTERED")
    read_sheet.clear()


# ── Carrega custos e pedidos ────────────────────────────────────────────────────
custos_config, custo_midia = carregar_cmv_config()
cmv_por_peca = sum(custos_config.values())

pedidos = read_sheet("pedidos")
if not pedidos.empty:
    pedidos["valor_total"] = pd.to_numeric(pedidos["valor_total"], errors="coerce").fillna(0)
    pedidos["valor_pago"]  = pd.to_numeric(pedidos["valor_pago"],  errors="coerce").fillna(0)
    pedidos["qtd"]         = pedidos.apply(extrair_qtd, axis=1)

# ══════════════════════════════════════════════════════════════════════════════
# 1 — Tabela de custos por peça
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🧾 Custo por peça")

col_tab, col_total = st.columns([3, 1])
with col_tab:
    df_custos = pd.DataFrame(
        [{"Item": k, "Tipo": "CMV (por peça)", "Custo (R$)": f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")}
         for k, v in custos_config.items()] +
        [{"Item": "Mídia / Marketing", "Tipo": "Fixo (mensal)", "Custo (R$)": f"R$ {custo_midia:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")}]
    )
    st.dataframe(df_custos, hide_index=True, use_container_width=True)

with col_total:
    st.metric("CMV por peça", f"R$ {cmv_por_peca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Custo fixo/mês", f"R$ {custo_midia:,.0f}".replace(",", "."))

with st.expander("✏️ Editar custos"):
    with st.form("editar_cmv"):
        novos = {}
        cols_form = st.columns(3)
        for i, (item, val) in enumerate(custos_config.items()):
            novos[item] = cols_form[i % 3].number_input(item, value=float(val), min_value=0.0, step=0.50)
        nova_midia = st.number_input("Custo de Mídia / Marketing (R$/mês)", value=float(custo_midia), min_value=0.0, step=10.0)
        if st.form_submit_button("Salvar custos", type="primary"):
            salvar_cmv_config(novos, nova_midia)
            st.toast("Custos atualizados!", icon="✅")
            st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 2 — Resumo por mês
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Resultado por mês")

if pedidos.empty:
    st.info("Nenhum pedido cadastrado ainda.")
    st.stop()

meses = sorted(pedidos["mes_ref"].dropna().unique().tolist(), reverse=True)
col_sel, _ = st.columns([2, 5])
mes_sel = col_sel.selectbox("Mês", meses, format_func=lambda x: MES_NOMES.get(x, x))

df_mes = pedidos[pedidos["mes_ref"] == mes_sel]
fat        = df_mes["valor_total"].sum()
pecas      = int(df_mes["qtd"].sum())
cmv_total   = pecas * cmv_por_peca
margem_bruta = fat - cmv_total
lucro_liq   = margem_bruta - custo_midia
margem_pct  = (margem_bruta / fat * 100) if fat else 0
lucro_pct   = (lucro_liq / fat * 100) if fat else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Faturado",      f"R$ {fat:,.0f}".replace(",", "."),          f"{pecas} peças")
c2.metric("CMV total",     f"R$ {cmv_total:,.0f}".replace(",", "."),    f"R$ {cmv_por_peca:.2f}/peça")
c3.metric("Custo de mídia",f"R$ {custo_midia:,.0f}".replace(",", "."),  "fixo mensal")
c4.metric("Margem bruta",  f"R$ {margem_bruta:,.0f}".replace(",", "."), f"{margem_pct:.1f}%")
c5.metric("Lucro líquido", f"R$ {lucro_liq:,.0f}".replace(",", "."),    f"{lucro_pct:.1f}% do fat.")
c6.metric("CMV %",         f"{(cmv_total/fat*100):.1f}%" if fat else "—")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 3 — CMV por pedido
# ══════════════════════════════════════════════════════════════════════════════
st.subheader(f"📋 CMV por pedido — {MES_NOMES.get(mes_sel, mes_sel)}")

df_det = df_mes[["contato_nome", "descricao", "qtd", "valor_total"]].copy()
df_det["cmv"]     = df_det["qtd"] * cmv_por_peca
df_det["margem"]  = df_det["valor_total"] - df_det["cmv"]
df_det["mrg_pct"] = df_det.apply(
    lambda r: f"{(r['margem']/r['valor_total']*100):.1f}%" if r["valor_total"] else "—", axis=1
)

display = df_det.copy()
display.columns = ["Cliente", "Descrição", "Peças", "Faturado", "CMV", "Margem", "Margem %"]
for col in ["Faturado", "CMV", "Margem"]:
    display[col] = display[col].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.dataframe(display, hide_index=True, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 4 — Evolução mensal
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📈 Evolução mensal")

resumo = (
    pedidos.groupby("mes_ref")
    .agg(Faturado=("valor_total", "sum"), Pecas=("qtd", "sum"))
    .reset_index()
    .sort_values("mes_ref")
)
resumo["CMV"]         = resumo["Pecas"] * cmv_por_peca
resumo["Margem bruta"] = resumo["Faturado"] - resumo["CMV"]
resumo["Lucro líquido"] = resumo["Margem bruta"] - custo_midia
resumo["Mês"]          = resumo["mes_ref"].map(lambda x: MES_NOMES.get(x, x))

fig = go.Figure()
fig.add_bar(x=resumo["Mês"], y=resumo["Faturado"],       name="Faturado",       marker_color="#D4956A")
fig.add_bar(x=resumo["Mês"], y=resumo["CMV"],            name="CMV",            marker_color="#C62828")
fig.add_bar(x=resumo["Mês"], y=resumo["Margem bruta"],   name="Margem bruta",   marker_color="#1565C0")
fig.add_bar(x=resumo["Mês"], y=resumo["Lucro líquido"],  name="Lucro líquido",  marker_color="#2E7D32")
fig.update_layout(
    barmode="group",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=1.1),
    margin=dict(t=10, b=0, l=0, r=0),
    yaxis_tickprefix="R$ ",
    height=320,
)
st.plotly_chart(fig, use_container_width=True)
