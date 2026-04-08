import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils.sheets import read_sheet, append_row, update_row, is_configured

st.set_page_config(page_title="Financeiro — Afeto em Ponto", page_icon="💰", layout="wide")
st.title("💰 Financeiro — Pedidos e Pagamentos")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

MES_NOMES = {
    "2026-01": "Janeiro/2026", "2026-02": "Fevereiro/2026", "2026-03": "Março/2026",
    "2026-04": "Abril/2026",   "2026-05": "Maio/2026",       "2026-06": "Junho/2026",
    "2026-07": "Julho/2026",   "2026-08": "Agosto/2026",     "2026-09": "Setembro/2026",
    "2026-10": "Outubro/2026", "2026-11": "Novembro/2026",   "2026-12": "Dezembro/2026",
}
STATUS_OPTS  = ["pendente", "parcial", "pago"]
STATUS_EMOJI = {"pago": "✅ Pago", "parcial": "🟡 Sinal pago", "pendente": "🔴 Pendente"}

pedidos = read_sheet("pedidos")

if pedidos.empty:
    meses = []
else:
    pedidos["valor_total"] = pd.to_numeric(pedidos["valor_total"], errors="coerce").fillna(0)
    pedidos["valor_pago"]  = pd.to_numeric(pedidos["valor_pago"],  errors="coerce").fillna(0)
    pedidos["pendente"]    = pedidos["valor_total"] - pedidos["valor_pago"]
    meses = sorted(pedidos["mes_ref"].dropna().unique().tolist(), reverse=True)

# ── Filtros ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([2, 2])
with c1:
    mes_sel = st.selectbox("Mês", ["todos"] + meses,
                           format_func=lambda x: "Todos os meses" if x == "todos" else MES_NOMES.get(x, x))
with c2:
    status_sel = st.selectbox("Status", ["todos"] + STATUS_OPTS,
                              format_func=lambda x: "Todos" if x == "todos" else STATUS_EMOJI.get(x, x))

df = pedidos.copy() if not pedidos.empty else pd.DataFrame()

if not df.empty:
    if mes_sel != "todos":
        df = df[df["mes_ref"] == mes_sel]
    if status_sel != "todos":
        df = df[df["status_pagamento"] == status_sel]

# ── Sumário rápido ─────────────────────────────────────────────────────────────
if not df.empty:
    fat   = df["valor_total"].sum()
    pago  = df["valor_pago"].sum()
    pend  = df["pendente"].sum()
    c1m, c2m, c3m, c4m = st.columns(4)
    c1m.metric("Faturado",  f"R$ {fat:,.0f}".replace(",", "."), f"{len(df)} pedidos")
    c2m.metric("Recebido",  f"R$ {pago:,.0f}".replace(",", "."))
    c3m.metric("Pendente",  f"R$ {pend:,.0f}".replace(",", "."))
    c4m.metric("Receb. %",  f"{(pago/fat*100):.0f}%" if fat else "—")

st.divider()

# ── Tabela editável ────────────────────────────────────────────────────────────
st.subheader("Pedidos")

if df.empty:
    st.info("Nenhum pedido para os filtros selecionados.")
else:
    for _, row in df.iterrows():
        with st.expander(
            f"{STATUS_EMOJI.get(row['status_pagamento'], row['status_pagamento'])}  ·  "
            f"**{row['contato_nome']}** — {row['descricao'][:50]}  "
            f"· R$ {row['valor_total']:,.0f}".replace(",", ".")
        ):
            col_info, col_pag = st.columns([2, 2])
            with col_info:
                st.markdown(f"**Mês:** {MES_NOMES.get(row['mes_ref'], row['mes_ref'])}")
                st.markdown(f"**Descrição:** {row['descricao']}")
                st.markdown(f"**Total:** R$ {row['valor_total']:,.0f}".replace(",", "."))
                st.markdown(f"**Pago:** R$ {row['valor_pago']:,.0f}".replace(",", "."))
                st.markdown(f"**Falta:** R$ {row['pendente']:,.0f}".replace(",", "."))
                if row.get("data_entrega"):
                    st.markdown(f"**Entrega prevista:** {row['data_entrega']}")
            with col_pag:
                with st.form(key=f"pag_{row['id']}"):
                    st.markdown("**Atualizar pagamento**")
                    novo_status = st.selectbox(
                        "Status", STATUS_OPTS,
                        index=STATUS_OPTS.index(row["status_pagamento"]) if row["status_pagamento"] in STATUS_OPTS else 0,
                        format_func=lambda x: STATUS_EMOJI.get(x, x),
                    )
                    novo_pago = st.number_input("Valor pago (R$)", value=float(row["valor_pago"]), min_value=0.0, step=10.0)
                    if st.form_submit_button("Salvar pagamento", type="primary"):
                        status_calc = "pago" if novo_pago >= row["valor_total"] else ("parcial" if novo_pago > 0 else "pendente")
                        update_row("pedidos", row["id"], {
                            "valor_pago": novo_pago,
                            "status_pagamento": status_calc,
                        })
                        st.success("Pagamento atualizado!")
                        st.rerun()

st.divider()

# ── Novo pedido ────────────────────────────────────────────────────────────────
st.subheader("Registrar novo pedido")

MES_ATUAL = datetime.now().strftime("%Y-%m")
MESES_FORM = [f"2026-{m:02d}" for m in range(1, 13)]

with st.form("novo_pedido", clear_on_submit=True):
    c1, c2 = st.columns(2)
    cliente    = c1.text_input("Nome do cliente *")
    mes_ref    = c2.selectbox("Mês de referência", MESES_FORM,
                              index=MESES_FORM.index(MES_ATUAL) if MES_ATUAL in MESES_FORM else 0,
                              format_func=lambda x: MES_NOMES.get(x, x))
    descricao  = st.text_input("Descrição do pedido *", placeholder="Ex: 3 peças Composição Um Lar 20x20")
    c3, c4 = st.columns(2)
    valor_total = c3.number_input("Valor total (R$)", min_value=0.0, step=10.0)
    valor_pago  = c4.number_input("Valor já pago (R$)", min_value=0.0, step=10.0)
    data_entrega = c1.text_input("Entrega prevista", placeholder="Ex: 20/04/2026")

    if st.form_submit_button("Adicionar pedido", type="primary"):
        if not cliente.strip() or not descricao.strip():
            st.error("Cliente e descrição são obrigatórios.")
        elif valor_pago > valor_total:
            st.error("Valor pago não pode ser maior que o total.")
        else:
            status_calc = "pago" if valor_pago >= valor_total else ("parcial" if valor_pago > 0 else "pendente")
            append_row("pedidos", {
                "contato_nome": cliente.strip(),
                "mes_ref": mes_ref,
                "descricao": descricao.strip(),
                "valor_total": valor_total,
                "valor_pago": valor_pago,
                "status_pagamento": status_calc,
                "data_entrega": data_entrega.strip(),
            })
            st.success(f"Pedido de **{cliente}** registrado!")
            st.rerun()
