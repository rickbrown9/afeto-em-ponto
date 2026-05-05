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


@st.dialog("✏️ Editar contato")
def editar_contato(row):
    e1, e2 = st.columns(2)
    novo_nome     = e1.text_input("Nome *", value=str(row.get("nome", "")))
    novo_tel      = e2.text_input("Telefone", value=str(row.get("telefone", "")))
    novo_ig       = e1.text_input("Instagram (sem @)", value=str(row.get("instagram", "")))
    orig_atual    = str(row.get("origem", "Instagram"))
    novo_orig     = e2.selectbox(
        "Origem", ORIGEM_OPTS,
        index=ORIGEM_OPTS.index(orig_atual) if orig_atual in ORIGEM_OPTS else 0,
    )
    status_atual  = str(row.get("status", "lead"))
    novo_status   = e1.selectbox(
        "Status", STATUS_OPTS,
        index=STATUS_OPTS.index(status_atual) if status_atual in STATUS_OPTS else 0,
        format_func=lambda x: STATUS_LABEL.get(x, x),
    )
    novo_end      = e2.text_input("Endereço", value=str(row.get("endereco", "")))
    nova_nota     = st.text_area("Notas", value=str(row.get("notas", "")), height=80)
    b1, b2 = st.columns(2)
    if b1.button("💾 Salvar", type="primary", use_container_width=True):
        if not novo_nome.strip():
            st.error("Nome é obrigatório.")
        else:
            update_row("contatos", str(row["id"]), {
                "nome":      novo_nome.strip(),
                "telefone":  novo_tel.strip(),
                "instagram": novo_ig.strip(),
                "origem":    novo_orig,
                "status":    novo_status,
                "endereco":  novo_end.strip(),
                "notas":     nova_nota.strip(),
            })
            st.cache_data.clear()
            st.rerun()
    if b2.button("✖ Cancelar", use_container_width=True):
        st.rerun()

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
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(f"**Origem:** {row.get('origem', '—')}")
                if row.get("endereco"):
                    st.markdown(f"**Endereço:** {row['endereco']}")
                st.markdown(f"**Notas:** {row.get('notas', '—') or '—'}")
                st.markdown(f"**Desde:** {row.get('criado_em', '—')}")
            with col_btn:
                if st.button("✏️ Editar", key=f"edit_btn_{row['id']}", use_container_width=True):
                    editar_contato(row.to_dict())

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
    endereco  = st.text_input("Endereço (para entrega)", placeholder="Ex: Rua das Flores, 42 — Bairro, Cidade/UF")
    notas     = st.text_area("Notas", height=80)
    if st.form_submit_button("Adicionar contato", type="primary"):
        if not nome.strip():
            st.error("Nome é obrigatório.")
        else:
            append_row("contatos", {
                "nome":      nome.strip(),
                "telefone":  telefone.strip(),
                "instagram": instagram.strip(),
                "endereco":  endereco.strip(),
                "status":    status,
                "origem":    origem,
                "notas":     notas.strip(),
            })
            st.success(f"Contato **{nome}** adicionado!")
            st.rerun()
