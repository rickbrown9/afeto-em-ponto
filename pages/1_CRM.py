import streamlit as st
import pandas as pd
from datetime import datetime
from utils.sheets import read_sheet, append_row, update_row, is_configured

st.set_page_config(page_title="CRM — Afeto em Ponto", page_icon="👥", layout="wide")
st.title("👥 CRM — Contatos")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

STATUS_OPTS   = ["lead", "lead_qualificado", "cliente"]
ORIGEM_OPTS   = ["Instagram", "WhatsApp", "Indicação", "Loja", "Outro"]
STATUS_LABEL  = {
    "lead": "🔵 Lead",
    "lead_qualificado": "🟡 Lead Qualificado",
    "cliente": "🟢 Cliente",
}
STATUS_COLOR  = {
    "lead": "#1565c0",
    "lead_qualificado": "#e65100",
    "cliente": "#2e7d32",
}

contatos = read_sheet("contatos")

# ── Filtros ────────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 5])
with col_f1:
    filtro = st.selectbox("Filtrar por status", ["todos"] + STATUS_OPTS,
                          format_func=lambda x: "Todos" if x == "todos" else STATUS_LABEL.get(x, x))
with col_f2:
    busca = st.text_input("Buscar por nome", placeholder="Digite parte do nome...")

df = contatos.copy() if not contatos.empty else pd.DataFrame(columns=contatos.columns if not contatos.empty else [])

if not df.empty:
    if filtro != "todos":
        df = df[df["status"] == filtro]
    if busca:
        df = df[df["nome"].str.contains(busca, case=False, na=False)]

# ── Lista de contatos ──────────────────────────────────────────────────────────
st.markdown(f"**{len(df)} contato(s) encontrado(s)**")

if df.empty:
    st.info("Nenhum contato encontrado.")
else:
    for _, row in df.iterrows():
        with st.expander(
            f"{STATUS_LABEL.get(row['status'], row['status'])}  ·  **{row['nome']}**  "
            f"{'· ' + row['telefone'] if row.get('telefone') else ''}  "
            f"{'· @' + row['instagram'] if row.get('instagram') else ''}"
        ):
            col_info, col_edit = st.columns([3, 2])
            with col_info:
                st.markdown(f"**Origem:** {row.get('origem', '—')}")
                st.markdown(f"**Notas:** {row.get('notas', '—') or '—'}")
                st.markdown(f"**Desde:** {row.get('criado_em', '—')}")
            with col_edit:
                with st.form(key=f"edit_{row['id']}"):
                    novo_status = st.selectbox("Status", STATUS_OPTS,
                                               index=STATUS_OPTS.index(row["status"]) if row["status"] in STATUS_OPTS else 0,
                                               format_func=lambda x: STATUS_LABEL.get(x, x))
                    nova_nota   = st.text_area("Notas", value=row.get("notas", ""), height=80)
                    if st.form_submit_button("Salvar"):
                        update_row("contatos", row["id"], {"status": novo_status, "notas": nova_nota})
                        st.success("Atualizado!")
                        st.rerun()

st.divider()

# ── Adicionar novo contato ─────────────────────────────────────────────────────
st.subheader("Adicionar contato")
with st.form("novo_contato", clear_on_submit=True):
    c1, c2 = st.columns(2)
    nome      = c1.text_input("Nome *")
    telefone  = c2.text_input("Telefone")
    instagram = c1.text_input("Instagram (sem @)")
    status    = c2.selectbox("Status", STATUS_OPTS, format_func=lambda x: STATUS_LABEL.get(x, x))
    origem    = c1.selectbox("Origem", ORIGEM_OPTS)
    notas     = st.text_area("Notas", height=80)
    if st.form_submit_button("Adicionar contato", type="primary"):
        if not nome.strip():
            st.error("Nome é obrigatório.")
        else:
            append_row("contatos", {
                "nome": nome.strip(),
                "telefone": telefone.strip(),
                "instagram": instagram.strip(),
                "status": status,
                "origem": origem,
                "notas": notas.strip(),
            })
            st.success(f"Contato **{nome}** adicionado!")
            st.rerun()
