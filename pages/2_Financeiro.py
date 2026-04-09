import streamlit as st
import pandas as pd
from datetime import datetime
from utils.sheets import read_sheet, append_row, update_row, is_configured, sync_cronograma_pagamento

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

CATEGORIAS_CUSTO = [
    "Fios / Linhas", "Tecido / Bastidor", "Embalagem",
    "Transporte", "Marketing", "Ferramentas", "Outros",
]

MES_ATUAL  = datetime.now().strftime("%Y-%m")
MESES_FORM = [f"2026-{m:02d}" for m in range(1, 13)]

# ── Carrega dados ──────────────────────────────────────────────────────────────
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

# ── Sumário ────────────────────────────────────────────────────────────────────
if not df.empty:
    fat  = df["valor_total"].sum()
    pago = df["valor_pago"].sum()
    pend = df["pendente"].sum()
    c1m, c2m, c3m, c4m = st.columns(4)
    c1m.metric("Faturado", f"R$ {fat:,.0f}".replace(",", "."), f"{len(df)} pedidos")
    c2m.metric("Recebido", f"R$ {pago:,.0f}".replace(",", "."))
    c3m.metric("Pendente", f"R$ {pend:,.0f}".replace(",", "."))
    c4m.metric("Receb. %", f"{(pago/fat*100):.0f}%" if fat else "—")

st.divider()

# ── Pedidos ────────────────────────────────────────────────────────────────────
st.subheader("Pedidos")

if df.empty:
    st.info("Nenhum pedido para os filtros selecionados.")
else:
    for _, row in df.iterrows():
        status_atual = row["status_pagamento"]
        status_label = STATUS_EMOJI.get(status_atual, status_atual)
        with st.expander(
            f"{status_label}  ·  **{row['contato_nome']}** — {row['descricao'][:50]}  "
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
                    idx = STATUS_OPTS.index(status_atual) if status_atual in STATUS_OPTS else 0
                    novo_status = st.selectbox("Status", STATUS_OPTS, index=idx,
                                              format_func=lambda x: STATUS_EMOJI.get(x, x))
                    novo_pago = st.number_input("Valor pago (R$)", value=float(row["valor_pago"]),
                                               min_value=0.0, step=10.0)
                    if st.form_submit_button("Salvar pagamento", type="primary"):
                        status_calc = "pago" if novo_pago >= row["valor_total"] else \
                                      ("parcial" if novo_pago > 0 else "pendente")
                        update_row("pedidos", row["id"], {
                            "valor_pago": novo_pago,
                            "status_pagamento": status_calc,
                        })
                        sync_cronograma_pagamento(row["contato_nome"], status_calc)
                        st.toast("Pagamento atualizado!", icon="✅")
                        st.rerun()

st.divider()

# ── Novo pedido ────────────────────────────────────────────────────────────────
st.subheader("Registrar novo pedido")

with st.form("novo_pedido", clear_on_submit=True):
    c1, c2 = st.columns(2)
    cliente      = c1.text_input("Nome do cliente *")
    mes_ref      = c2.selectbox("Mês de referência", MESES_FORM,
                                index=MESES_FORM.index(MES_ATUAL) if MES_ATUAL in MESES_FORM else 0,
                                format_func=lambda x: MES_NOMES.get(x, x))
    c3, c4       = st.columns([3, 1])
    descricao    = c3.text_input("Descrição do pedido *", placeholder="Ex: Composição Um Lar 20x20")
    qtd_pecas    = c4.number_input("Peças", min_value=1, step=1, value=1)
    c5, c6       = st.columns(2)
    valor_total  = c5.number_input("Valor total (R$)", min_value=0.0, step=10.0)
    valor_pago   = c6.number_input("Valor já pago (R$)", min_value=0.0, step=10.0)
    data_entrega = c1.text_input("Entrega prevista", placeholder="Ex: 20/04/2026")

    if st.form_submit_button("Adicionar pedido", type="primary"):
        if not cliente.strip() or not descricao.strip():
            st.error("Cliente e descrição são obrigatórios.")
        elif valor_pago > valor_total:
            st.error("Valor pago não pode ser maior que o total.")
        else:
            status_calc = "pago" if valor_pago >= valor_total else \
                          ("parcial" if valor_pago > 0 else "pendente")
            # Inclui qtd na descrição para extração automática no dashboard
            desc_final = f"{qtd_pecas} peça(s) — {descricao.strip()}" if qtd_pecas > 1 \
                         else descricao.strip()
            append_row("pedidos", {
                "contato_nome": cliente.strip(),
                "mes_ref": mes_ref,
                "descricao": desc_final,
                "valor_total": valor_total,
                "valor_pago": valor_pago,
                "status_pagamento": status_calc,
                "data_entrega": data_entrega.strip(),
            })
            st.toast(f"Pedido de {cliente} registrado!", icon="✅")
            st.rerun()

st.divider()

# ── Custos & Compras ───────────────────────────────────────────────────────────
st.subheader("🛒 Custos & Compras")
st.caption("Registre aqui os gastos do ateliê. Você também pode editar direto na aba 'custos' do Google Sheets.")

custos = read_sheet("custos")

if not custos.empty:
    custos["valor"] = pd.to_numeric(custos["valor"], errors="coerce").fillna(0)
    # Extrai mês de referência da data (formato DD/MM/YYYY ou YYYY-MM-DD)
    def mes_do_custo(data_str):
        try:
            if "/" in str(data_str):
                parts = str(data_str).split("/")
                return f"2026-{parts[1].zfill(2)}"
            return str(data_str)[:7]
        except Exception:
            return ""
    custos["mes_ref_c"] = custos["data"].apply(mes_do_custo)

    # Filtro por mês (usa mesmo seletor da página)
    df_c = custos[custos["mes_ref_c"] == mes_sel] if mes_sel != "todos" else custos

    total_custo = df_c["valor"].sum()
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        if df_c.empty:
            st.caption("Nenhum custo registrado para este mês.")
        else:
            display_c = df_c[["data", "categoria", "descricao", "valor"]].copy()
            display_c.columns = ["Data", "Categoria", "Descrição", "Valor (R$)"]
            display_c["Valor (R$)"] = display_c["Valor (R$)"].map(
                lambda x: f"R$ {x:,.0f}".replace(",", "."))
            st.dataframe(display_c, use_container_width=True, hide_index=True)
    with cc2:
        st.metric("Total custos", f"R$ {total_custo:,.0f}".replace(",", "."))
        fat_mes = df["valor_total"].sum() if not df.empty else 0
        lucro = fat_mes - total_custo
        st.metric("Lucro estimado", f"R$ {lucro:,.0f}".replace(",", "."),
                  delta=f"{'▲' if lucro >= 0 else '▼'} do faturado")
else:
    st.caption("Nenhum custo registrado ainda.")

with st.expander("➕ Registrar custo"):
    with st.form("novo_custo", clear_on_submit=True):
        cc1, cc2 = st.columns(2)
        data_custo  = cc1.text_input("Data *", placeholder="Ex: 10/04/2026",
                                     value=datetime.now().strftime("%d/%m/%Y"))
        categoria   = cc2.selectbox("Categoria", CATEGORIAS_CUSTO)
        desc_custo  = st.text_input("Descrição *", placeholder="Ex: Meada de linha de seda rosa")
        valor_custo = st.number_input("Valor (R$)", min_value=0.0, step=5.0)

        if st.form_submit_button("Registrar custo", type="primary"):
            if not desc_custo.strip() or valor_custo <= 0:
                st.error("Descrição e valor são obrigatórios.")
            else:
                append_row("custos", {
                    "data": data_custo.strip(),
                    "categoria": categoria,
                    "descricao": desc_custo.strip(),
                    "valor": valor_custo,
                })
                st.toast("Custo registrado!", icon="🛒")
                st.rerun()
