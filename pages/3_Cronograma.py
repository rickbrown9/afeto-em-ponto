import streamlit as st
import pandas as pd
from utils.sheets import read_sheet, append_row, update_row, delete_row, is_configured

st.set_page_config(page_title="Cronograma — Afeto em Ponto", page_icon="🪡", layout="wide")
st.title("🪡 Cronograma de Bordagem")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

STATUS_BORDAGEM = ["fila", "bordando", "entregue"]
STATUS_EMOJI    = {"fila": "📋 Fila", "bordando": "🪡 Bordando", "entregue": "✅ Entregue"}
PAG_EMOJI       = {"pago": "✅", "parcial": "🟡", "pendente": "🔴"}

cronograma = read_sheet("cronograma")

# ── Kanban view ────────────────────────────────────────────────────────────────
col_fila, col_bord, col_entr = st.columns(3)

def render_card(row):
    pag_ic = PAG_EMOJI.get(row.get("status_pagamento_ref", ""), "⚪")
    st.markdown(f"""
**{row['cliente']}**
{row.get('descricao_peca', '')}
{('📐 ' + row.get('tamanho', '')) if row.get('tamanho') else ''}
{('📅 ' + row.get('data_prevista', '')) if row.get('data_prevista') else ''}
Pagamento: {pag_ic} {row.get('status_pagamento_ref', '—')}
{('📝 ' + row.get('notas', '')) if row.get('notas') else ''}
""")

def render_column(col, status_key, df):
    with col:
        st.markdown(f"### {STATUS_EMOJI[status_key]}")
        st.markdown(f"*{len(df)} peça(s)*")
        st.divider()
        if df.empty:
            st.caption("Nenhuma peça aqui.")
        for _, row in df.iterrows():
            with st.container(border=True):
                render_card(row)
                outros = [s for s in STATUS_BORDAGEM if s != status_key]
                with st.popover("Mover / Editar"):
                    with st.form(key=f"mv_{row['id']}"):
                        novo_s = st.selectbox("Novo status", STATUS_BORDAGEM,
                                              index=STATUS_BORDAGEM.index(status_key),
                                              format_func=lambda x: STATUS_EMOJI[x])
                        nova_nota = st.text_input("Notas", value=row.get("notas", ""))
                        c_save, c_del = st.columns(2)
                        salvar  = c_save.form_submit_button("Salvar")
                        excluir = c_del.form_submit_button("Excluir", type="secondary")
                    if salvar:
                        update_row("cronograma", row["id"], {"status_bordagem": novo_s, "notas": nova_nota})
                        st.rerun()
                    if excluir:
                        delete_row("cronograma", row["id"])
                        st.rerun()

if not cronograma.empty:
    for status in STATUS_BORDAGEM:
        sub = cronograma[cronograma["status_bordagem"] == status].reset_index(drop=True)
        col = {"fila": col_fila, "bordando": col_bord, "entregue": col_entr}[status]
        render_column(col, status, sub)
else:
    with col_fila:
        st.markdown("### 📋 Fila")
        st.info("Nenhuma peça cadastrada ainda.")
    with col_bord:
        st.markdown("### 🪡 Bordando")
    with col_entr:
        st.markdown("### ✅ Entregue")

st.divider()

# ── Adicionar peça ─────────────────────────────────────────────────────────────
st.subheader("Adicionar peça ao cronograma")

# Pega nomes dos pedidos para sugestão
pedidos = read_sheet("pedidos")
clientes_sugestao = sorted(pedidos["contato_nome"].dropna().unique().tolist()) if not pedidos.empty else []

with st.form("nova_peca", clear_on_submit=True):
    c1, c2 = st.columns(2)
    cliente = c1.selectbox("Cliente", [""] + clientes_sugestao) if clientes_sugestao else c1.text_input("Cliente")
    if isinstance(cliente, str) and cliente == "":
        cliente_manual = c1.text_input("Ou digite o nome manualmente")
        cliente_final  = cliente_manual.strip()
    else:
        cliente_final = cliente

    descricao_peca  = c2.text_input("Descrição da peça *", placeholder="Ex: Bordado Lenine, Composição Um Lar...")
    tamanho         = c1.text_input("Tamanho", placeholder="Ex: 20x20, 30x30")
    data_prevista   = c2.text_input("Data prevista", placeholder="Ex: 10/04/2026")
    status_bordagem = c1.selectbox("Status inicial", STATUS_BORDAGEM, format_func=lambda x: STATUS_EMOJI[x])
    status_pag_ref  = c2.selectbox("Status de pagamento", ["pendente", "parcial", "pago"],
                                   format_func=lambda x: PAG_EMOJI.get(x, "") + " " + x.capitalize())
    notas           = st.text_input("Notas", placeholder="Observações opcionais")

    if st.form_submit_button("Adicionar peça", type="primary"):
        nome_final = cliente_final if cliente_final else (cliente if isinstance(cliente, str) and cliente else "")
        if not nome_final or not descricao_peca.strip():
            st.error("Cliente e descrição são obrigatórios.")
        else:
            append_row("cronograma", {
                "pedido_id": "",
                "cliente": nome_final,
                "descricao_peca": descricao_peca.strip(),
                "tamanho": tamanho.strip(),
                "data_prevista": data_prevista.strip(),
                "status_bordagem": status_bordagem,
                "status_pagamento_ref": status_pag_ref,
                "notas": notas.strip(),
            })
            st.success(f"Peça de **{nome_final}** adicionada ao cronograma!")
            st.rerun()
