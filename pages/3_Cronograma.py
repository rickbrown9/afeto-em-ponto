import streamlit as st
import pandas as pd
from utils.sheets import read_sheet, append_row, update_row, delete_row, is_configured

st.set_page_config(page_title="Cronograma — Afeto em Ponto", page_icon="🪡", layout="wide")

st.markdown("""
<style>
/* Colunas do kanban */
.kanban-header {
    text-align: center;
    padding: 10px;
    border-radius: 10px 10px 0 0;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.header-fila     { background: #E3F2FD; color: #1565C0; }
.header-bordando { background: #FFF8E1; color: #E65100; }
.header-entregue { background: #E8F5E9; color: #2E7D32; }

/* Cards kanban */
.kanban-card {
    background: white;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 5px solid #ccc;
    font-size: 0.88rem;
    line-height: 1.5;
}
.card-pago     { border-left-color: #2E7D32; }
.card-parcial  { border-left-color: #F57C00; }
.card-pendente { border-left-color: #C62828; }

.card-cliente   { font-weight: 700; font-size: 1rem; margin-bottom: 4px; color: #3D2B1F; }
.card-peca      { color: #555; margin-bottom: 4px; }
.card-meta      { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 6px; }
.card-tag       { background: #F5EBE0; padding: 2px 8px; border-radius: 20px; font-size: 0.78rem; color: #5D4037; }
.card-tag-pago  { background: #E8F5E9; color: #2E7D32; }
.card-tag-parcial { background: #FFF3E0; color: #E65100; }
.card-tag-pend  { background: #FFEBEE; color: #C62828; }

/* Coluna */
.kanban-col {
    background: #F8F4F0;
    border-radius: 10px;
    padding: 10px;
    min-height: 200px;
}
</style>
""", unsafe_allow_html=True)

st.title("🪡 Cronograma de Bordagem")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

STATUS_BORDAGEM = ["fila", "bordando", "entregue"]
PAG_LABEL = {"pago": "✅ Pago", "parcial": "🟡 Sinal", "pendente": "🔴 Pendente"}
PAG_TAG   = {"pago": "card-tag-pago", "parcial": "card-tag-parcial", "pendente": "card-tag-pend"}

def reload():
    st.cache_data.clear()
    st.rerun()

cronograma = read_sheet("cronograma")

# ── Kanban ─────────────────────────────────────────────────────────────────────
col_fila, col_bord, col_entr = st.columns(3)

COLS = {
    "fila":     (col_fila,  "📋 Fila",     "header-fila"),
    "bordando": (col_bord,  "🪡 Bordando",  "header-bordando"),
    "entregue": (col_entr,  "✅ Entregue",  "header-entregue"),
}

for status, (col, label, hdr_class) in COLS.items():
    subset = cronograma[cronograma["status_bordagem"] == status].reset_index(drop=True) \
             if not cronograma.empty else pd.DataFrame()

    with col:
        count = len(subset)
        st.markdown(
            f'<div class="kanban-header {hdr_class}">{label} &nbsp;<span style="font-weight:400;font-size:.85rem;">({count})</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="kanban-col">', unsafe_allow_html=True)

        if subset.empty:
            st.markdown("<p style='color:#aaa;text-align:center;padding:20px 0'>Nenhuma peça</p>", unsafe_allow_html=True)
        else:
            for _, row in subset.iterrows():
                pag = row.get("status_pagamento_ref", "pendente")
                pag_class = PAG_TAG.get(pag, "card-tag")
                tamanho   = row.get("tamanho", "")
                data      = row.get("data_prevista", "")
                notas     = row.get("notas", "")

                card_html = f"""
<div class="kanban-card card-{pag}">
  <div class="card-cliente">{row['cliente']}</div>
  <div class="card-peca">{row['descricao_peca']}</div>
  <div class="card-meta">
    {f'<span class="card-tag">📐 {tamanho}</span>' if tamanho else ''}
    {f'<span class="card-tag">📅 {data}</span>' if data else ''}
    <span class="card-tag {pag_class}">{PAG_LABEL.get(pag, pag)}</span>
    {f'<span class="card-tag">📝 {notas}</span>' if notas else ''}
  </div>
</div>"""
                st.markdown(card_html, unsafe_allow_html=True)

                # Botões de ação abaixo do card
                btn_cols = st.columns([1, 1, 1])
                outros = [s for s in STATUS_BORDAGEM if s != status]
                mover_labels = {
                    "fila":     ("▶ Bordando", None),
                    "bordando": ("◀ Fila",     "▶ Entregue"),
                    "entregue": ("◀ Bordando", None),
                }
                esq, dir_ = mover_labels[status]

                with btn_cols[0]:
                    if esq and st.button(esq, key=f"esq_{row['id']}", use_container_width=True):
                        destino = "fila" if "Fila" in esq else "bordando"
                        update_row("cronograma", row["id"], {"status_bordagem": destino})
                        reload()

                with btn_cols[1]:
                    if dir_ and st.button(dir_, key=f"dir_{row['id']}", use_container_width=True):
                        update_row("cronograma", row["id"], {"status_bordagem": "entregue"})
                        reload()

                with btn_cols[2]:
                    if st.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                        delete_row("cronograma", row["id"])
                        reload()

                st.markdown("---", unsafe_allow_html=False)

        st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ── Adicionar peça ─────────────────────────────────────────────────────────────
with st.expander("➕ Adicionar nova peça ao cronograma"):
    pedidos = read_sheet("pedidos")
    clientes = sorted(pedidos["contato_nome"].dropna().unique().tolist()) if not pedidos.empty else []

    with st.form("nova_peca", clear_on_submit=True):
        c1, c2 = st.columns(2)
        if clientes:
            cliente_sel = c1.selectbox("Cliente", ["— digitar manualmente —"] + clientes)
            cliente_manual = c1.text_input("Nome (se não estiver na lista)") if cliente_sel == "— digitar manualmente —" else ""
            cliente_final = cliente_manual.strip() if cliente_sel == "— digitar manualmente —" else cliente_sel
        else:
            cliente_final = c1.text_input("Cliente *")

        descricao_peca  = c2.text_input("Descrição da peça *", placeholder="Ex: Bordado Lenine")
        tamanho         = c1.text_input("Tamanho", placeholder="Ex: 20x20")
        data_prevista   = c2.text_input("Data prevista", placeholder="Ex: 15/04/2026")
        status_bordagem = c1.selectbox("Coluna inicial", STATUS_BORDAGEM,
                                       format_func=lambda x: {"fila": "📋 Fila", "bordando": "🪡 Bordando", "entregue": "✅ Entregue"}[x])
        status_pag_ref  = c2.selectbox("Status de pagamento", ["pendente", "parcial", "pago"],
                                       format_func=lambda x: PAG_LABEL[x])
        notas           = st.text_input("Notas")

        if st.form_submit_button("Adicionar peça", type="primary"):
            nome = cliente_final if isinstance(cliente_final, str) else ""
            if not nome or not descricao_peca.strip():
                st.error("Cliente e descrição são obrigatórios.")
            else:
                append_row("cronograma", {
                    "pedido_id": "",
                    "cliente": nome,
                    "descricao_peca": descricao_peca.strip(),
                    "tamanho": tamanho.strip(),
                    "data_prevista": data_prevista.strip(),
                    "status_bordagem": status_bordagem,
                    "status_pagamento_ref": status_pag_ref,
                    "notas": notas.strip(),
                })
                st.success(f"Peça de **{nome}** adicionada!")
                reload()
