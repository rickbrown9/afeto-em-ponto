import streamlit as st
import pandas as pd
from utils.sheets import read_sheet, append_row, update_row, delete_row, is_configured

st.set_page_config(page_title="Cronograma — Afeto em Ponto", page_icon="🪡", layout="wide")

st.markdown("""
<style>
.kanban-header {
    text-align: center;
    padding: 10px 14px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 12px;
}
.header-fila     { background:#E3F2FD; color:#1565C0; }
.header-bordando { background:#FFF8E1; color:#E65100; }
.header-entregue { background:#E8F5E9; color:#2E7D32; }

.card-pago     { border-left: 5px solid #2E7D32 !important; }
.card-parcial  { border-left: 5px solid #F57C00 !important; }
.card-pendente { border-left: 5px solid #C62828 !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🪡 Cronograma de Bordagem")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

STATUS_OPTS  = ["fila", "bordando", "entregue"]
STATUS_LABEL = {"fila": "📋 Fila", "bordando": "🪡 Bordando", "entregue": "✅ Entregue"}
HDR_CLASS    = {"fila": "header-fila", "bordando": "header-bordando", "entregue": "header-entregue"}
PAG_ICON     = {"pago": "✅", "parcial": "🟡", "pendente": "🔴"}
PAG_LABEL    = {"pago": "Pago", "parcial": "Sinal pago", "pendente": "Não pago"}

def reload():
    st.cache_data.clear()
    st.rerun()

cronograma = read_sheet("cronograma")

# ── Kanban ─────────────────────────────────────────────────────────────────────
col_fila, col_bord, col_entr = st.columns(3)
COLS = {"fila": col_fila, "bordando": col_bord, "entregue": col_entr}

for status in STATUS_OPTS:
    col = COLS[status]
    subset = (
        cronograma[cronograma["status_bordagem"] == status].reset_index(drop=True)
        if not cronograma.empty else pd.DataFrame()
    )
    with col:
        st.markdown(
            f'<div class="kanban-header {HDR_CLASS[status]}">'
            f'{STATUS_LABEL[status]}  <span style="font-weight:400">({len(subset)})</span></div>',
            unsafe_allow_html=True,
        )

        if subset.empty:
            st.caption("Nenhuma peça aqui.")
        else:
            for _, row in subset.iterrows():
                pag      = row.get("status_pagamento_ref", "pendente")
                tamanho  = row.get("tamanho", "")
                data     = row.get("data_prevista", "")
                notas    = row.get("notas", "")

                with st.container(border=True):
                    # Linha 1: cliente + ícone pagamento
                    h_col, p_col = st.columns([4, 1])
                    h_col.markdown(f"**{row['cliente']}**")
                    p_col.markdown(
                        f"<div style='text-align:right;font-size:1.1rem'>{PAG_ICON.get(pag,'')}</div>",
                        unsafe_allow_html=True,
                    )

                    # Linha 2: descrição da peça
                    st.markdown(
                        f"<span style='font-size:0.88rem;color:#555'>{row['descricao_peca']}</span>",
                        unsafe_allow_html=True,
                    )

                    # Tags: tamanho, data, pagamento, notas
                    tags = []
                    if tamanho: tags.append(f"📐 {tamanho}")
                    if data:    tags.append(f"📅 {data}")
                    tags.append(f"{PAG_ICON.get(pag,'')} {PAG_LABEL.get(pag, pag)}")
                    if notas:   tags.append(f"📝 {notas}")

                    tag_html = " &nbsp;".join(
                        f'<span style="background:#F5EBE0;padding:2px 7px;border-radius:20px;'
                        f'font-size:0.75rem;color:#5D4037">{t}</span>'
                        for t in tags
                    )
                    st.markdown(tag_html, unsafe_allow_html=True)

                    st.write("")  # espaço antes dos botões

                    # Botões de ação
                    if status == "fila":
                        b1, b2 = st.columns([3, 1])
                        if b1.button("▶ Bordando", key=f"bord_{row['id']}", use_container_width=True):
                            update_row("cronograma", row["id"], {"status_bordagem": "bordando"})
                            reload()
                        if b2.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                            delete_row("cronograma", row["id"])
                            reload()

                    elif status == "bordando":
                        b1, b2, b3 = st.columns([2, 2, 1])
                        if b1.button("◀ Fila", key=f"fila_{row['id']}", use_container_width=True):
                            update_row("cronograma", row["id"], {"status_bordagem": "fila"})
                            reload()
                        if b2.button("✅ Entregar", key=f"entr_{row['id']}", use_container_width=True, type="primary"):
                            update_row("cronograma", row["id"], {"status_bordagem": "entregue"})
                            reload()
                        if b3.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                            delete_row("cronograma", row["id"])
                            reload()

                    elif status == "entregue":
                        b1, b2 = st.columns([3, 1])
                        if b1.button("◀ Bordando", key=f"volta_{row['id']}", use_container_width=True):
                            update_row("cronograma", row["id"], {"status_bordagem": "bordando"})
                            reload()
                        if b2.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                            delete_row("cronograma", row["id"])
                            reload()

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
        status_bordagem = c1.selectbox("Coluna inicial", STATUS_OPTS, format_func=lambda x: STATUS_LABEL[x])
        status_pag_ref  = c2.selectbox("Status de pagamento", ["pendente", "parcial", "pago"],
                                       format_func=lambda x: f"{PAG_ICON[x]} {PAG_LABEL[x]}")
        notas           = st.text_input("Notas")

        if st.form_submit_button("Adicionar peça", type="primary"):
            nome = cliente_final if isinstance(cliente_final, str) and cliente_final else ""
            if not nome or not descricao_peca.strip():
                st.error("Cliente e descrição são obrigatórios.")
            else:
                append_row("cronograma", {
                    "pedido_id": "", "cliente": nome,
                    "descricao_peca": descricao_peca.strip(),
                    "tamanho": tamanho.strip(),
                    "data_prevista": data_prevista.strip(),
                    "status_bordagem": status_bordagem,
                    "status_pagamento_ref": status_pag_ref,
                    "notas": notas.strip(),
                })
                st.success(f"Peça de **{nome}** adicionada!")
                reload()
