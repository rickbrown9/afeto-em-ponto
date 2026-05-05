import streamlit as st
import pandas as pd
import calendar as cal_module
from datetime import datetime, date
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
PAG_COLOR    = {"pago": "#2E7D32", "parcial": "#F57C00", "pendente": "#C62828"}
MESES_PT     = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]


def reload():
    st.cache_data.clear()
    st.rerun()


@st.dialog("✏️ Editar peça")
def editar_peca(row):
    e1, e2 = st.columns(2)
    novo_cliente  = e1.text_input("Cliente", value=str(row.get("cliente", "")))
    novo_desc     = e2.text_input("Descrição", value=str(row.get("descricao_peca", "")))
    novo_tam      = e1.text_input("Tamanho", value=str(row.get("tamanho", "")))
    nova_data     = e2.text_input("Data prevista (DD/MM/AAAA)", value=str(row.get("data_prevista", "")))
    pag_opts      = ["pendente", "parcial", "pago"]
    pag_atual     = str(row.get("status_pagamento_ref", "pendente"))
    novo_pag      = e1.selectbox(
        "Pagamento", pag_opts,
        index=pag_opts.index(pag_atual) if pag_atual in pag_opts else 0,
        format_func=lambda x: f"{PAG_ICON[x]} {PAG_LABEL[x]}",
    )
    status_atual  = str(row.get("status_bordagem", "fila"))
    novo_status_b = e2.selectbox(
        "Coluna", STATUS_OPTS,
        index=STATUS_OPTS.index(status_atual) if status_atual in STATUS_OPTS else 0,
        format_func=lambda x: STATUS_LABEL[x],
    )
    novas_notas = st.text_input("Notas", value=str(row.get("notas", "")))
    b1, b2 = st.columns(2)
    if b1.button("💾 Salvar", type="primary", use_container_width=True):
        if not novo_cliente.strip() or not novo_desc.strip():
            st.error("Cliente e descrição são obrigatórios.")
        else:
            update_row("cronograma", str(row["id"]), {
                "cliente":              novo_cliente.strip(),
                "descricao_peca":       novo_desc.strip(),
                "tamanho":              novo_tam.strip(),
                "data_prevista":        nova_data.strip(),
                "status_pagamento_ref": novo_pag,
                "status_bordagem":      novo_status_b,
                "notas":                novas_notas.strip(),
            })
            st.cache_data.clear()
            st.rerun()
    if b2.button("✖ Cancelar", use_container_width=True):
        st.rerun()


def parse_date_br(date_str):
    try:
        parts = str(date_str).strip().split("/")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except Exception:
        pass
    return None


def render_calendar_html(year, month, pieces_df):
    monthly_cal = cal_module.monthcalendar(year, month)
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    today = date.today()

    by_date = {}
    if not pieces_df.empty:
        for _, row in pieces_df.iterrows():
            d = parse_date_br(row.get("data_prevista", ""))
            if d and d.year == year and d.month == month:
                if d not in by_date:
                    by_date[d] = []
                by_date[d].append(row)

    html = f"""
    <div style="font-family: sans-serif; overflow-x: auto;">
        <h3 style="text-align:center; color:#5D4037; margin-bottom:16px">
            {MESES_PT[month-1]} {year}
        </h3>
        <table style="width:100%; border-collapse: collapse; min-width:560px;">
            <thead><tr>
    """
    for d in dias_semana:
        html += (
            f'<th style="padding:8px 4px; background:#F5EBE0; color:#5D4037; '
            f'text-align:center; font-size:0.8rem; border:1px solid #e0d5cc">{d}</th>'
        )
    html += "</tr></thead><tbody>"

    for week in monthly_cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += (
                    '<td style="padding:4px; background:#FAFAFA; border:1px solid #eee; '
                    'min-height:80px; vertical-align:top;"></td>'
                )
            else:
                d = date(year, month, day)
                is_today = d == today
                bg = "#FFFDE7" if is_today else "white"
                pieces = by_date.get(d, [])

                if is_today:
                    day_num = (
                        f'<div style="background:#C4665A;color:white;border-radius:50%;'
                        f'width:22px;height:22px;display:inline-flex;align-items:center;'
                        f'justify-content:center;font-size:0.75rem;font-weight:700">{day}</div>'
                    )
                else:
                    day_num = (
                        f'<div style="font-size:0.8rem;font-weight:600;color:#555;padding:2px 0">'
                        f'{day}</div>'
                    )

                pieces_html = ""
                for p in pieces:
                    pag = p.get("status_pagamento_ref", "pendente")
                    color = PAG_COLOR.get(pag, "#888")
                    status_bord = p.get("status_bordagem", "")
                    status_icon = {"fila": "📋", "bordando": "🪡", "entregue": "✅"}.get(status_bord, "")
                    nome = str(p.get("cliente", ""))
                    desc = str(p.get("descricao_peca", ""))[:18]
                    pieces_html += (
                        f'<div style="background:{color}18; border-left:3px solid {color}; '
                        f'padding:2px 5px; margin:3px 0; border-radius:4px; font-size:0.68rem; '
                        f'color:#333; line-height:1.4">'
                        f'{status_icon} <strong>{nome}</strong><br>'
                        f'<span style="color:#666">{desc}</span></div>'
                    )

                html += (
                    f'<td style="padding:5px; background:{bg}; border:1px solid #eee; '
                    f'vertical-align:top; min-width:80px;">'
                    f'{day_num}{pieces_html}</td>'
                )
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


cronograma = read_sheet("cronograma")

# ── Filtros ─────────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=False):
    fc1, fc2, fc3, fc4 = st.columns(4)
    clientes_lista = sorted(cronograma["cliente"].dropna().unique().tolist()) if not cronograma.empty else []
    filt_cliente = fc1.multiselect("Cliente", clientes_lista, placeholder="Todos os clientes")
    filt_pag     = fc2.multiselect(
        "Pagamento", ["pago", "parcial", "pendente"],
        format_func=lambda x: f"{PAG_ICON[x]} {PAG_LABEL[x]}",
        placeholder="Todos os status",
    )
    filt_de  = fc3.date_input("Data prevista — de", value=None)
    filt_ate = fc4.date_input("Data prevista — até", value=None)

# Aplica filtros
df_filtered = cronograma.copy() if not cronograma.empty else pd.DataFrame()
if not df_filtered.empty:
    if filt_cliente:
        df_filtered = df_filtered[df_filtered["cliente"].isin(filt_cliente)]
    if filt_pag:
        df_filtered = df_filtered[df_filtered["status_pagamento_ref"].isin(filt_pag)]
    if filt_de or filt_ate:
        def in_range(d_str):
            d = parse_date_br(str(d_str))
            if d is None:
                return not (filt_de or filt_ate)
            if filt_de and d < filt_de:
                return False
            if filt_ate and d > filt_ate:
                return False
            return True
        df_filtered = df_filtered[df_filtered["data_prevista"].apply(in_range)]

# ── Abas: Kanban | Calendário ────────────────────────────────────────────────────
tab_kanban, tab_cal = st.tabs(["📋 Kanban", "📅 Calendário"])

# ════════════════════════════════════════════════════════════════════════
# KANBAN
# ════════════════════════════════════════════════════════════════════════
with tab_kanban:
    col_fila, col_bord, col_entr = st.columns(3)
    COLS = {"fila": col_fila, "bordando": col_bord, "entregue": col_entr}

    for status in STATUS_OPTS:
        col = COLS[status]
        subset = (
            df_filtered[df_filtered["status_bordagem"] == status].reset_index(drop=True)
            if not df_filtered.empty else pd.DataFrame()
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
                    pag     = row.get("status_pagamento_ref", "pendente")
                    tamanho = row.get("tamanho", "")
                    data    = row.get("data_prevista", "")
                    notas   = row.get("notas", "")

                    with st.container(border=True):
                        # Cabeçalho: cliente + ícone pagamento
                        h_col, p_col = st.columns([4, 1])
                        h_col.markdown(f"**{row['cliente']}**")
                        p_col.markdown(
                            f"<div style='text-align:right;font-size:1.1rem'>{PAG_ICON.get(pag,'')}</div>",
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            f"<span style='font-size:0.88rem;color:#555'>{row['descricao_peca']}</span>",
                            unsafe_allow_html=True,
                        )

                        # Tags
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
                        st.write("")

                        # Botões de movimento + editar
                        if status == "fila":
                            b1, b_ed, b2 = st.columns([3, 1, 1])
                            if b1.button("▶ Bordando", key=f"bord_{row['id']}", use_container_width=True):
                                update_row("cronograma", row["id"], {"status_bordagem": "bordando"})
                                reload()
                            if b_ed.button("✏️", key=f"edit_btn_{row['id']}", use_container_width=True):
                                editar_peca(row.to_dict())
                            if b2.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                                delete_row("cronograma", row["id"])
                                reload()

                        elif status == "bordando":
                            b1, b2, b_ed, b3 = st.columns([2, 2, 1, 1])
                            if b1.button("◀ Fila", key=f"fila_{row['id']}", use_container_width=True):
                                update_row("cronograma", row["id"], {"status_bordagem": "fila"})
                                reload()
                            if b2.button("✅ Entregar", key=f"entr_{row['id']}", use_container_width=True, type="primary"):
                                update_row("cronograma", row["id"], {"status_bordagem": "entregue"})
                                reload()
                            if b_ed.button("✏️", key=f"edit_btn_{row['id']}", use_container_width=True):
                                editar_peca(row.to_dict())
                            if b3.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                                delete_row("cronograma", row["id"])
                                reload()

                        elif status == "entregue":
                            b1, b_ed, b2 = st.columns([3, 1, 1])
                            if b1.button("◀ Bordando", key=f"volta_{row['id']}", use_container_width=True):
                                update_row("cronograma", row["id"], {"status_bordagem": "bordando"})
                                reload()
                            if b_ed.button("✏️", key=f"edit_btn_{row['id']}", use_container_width=True):
                                editar_peca(row.to_dict())
                            if b2.button("🗑", key=f"del_{row['id']}", use_container_width=True):
                                delete_row("cronograma", row["id"])
                                reload()

# ════════════════════════════════════════════════════════════════════════
# CALENDÁRIO
# ════════════════════════════════════════════════════════════════════════
with tab_cal:
    now = datetime.now()
    cc1, cc2, cc3, _ = st.columns([1, 1, 1, 2])
    cal_month = cc1.selectbox(
        "Mês", range(1, 13),
        index=now.month - 1,
        format_func=lambda x: MESES_PT[x - 1],
        key="cal_month",
    )
    cal_year = int(cc2.number_input("Ano", min_value=2025, max_value=2028, value=now.year, key="cal_year"))
    dia_sel = cc3.date_input("Filtrar por dia", value=None, key="cal_dia")

    st.markdown(render_calendar_html(cal_year, cal_month, df_filtered), unsafe_allow_html=True)

    # Lista de peças: filtra por dia se selecionado, senão mostra todo o mês
    pieces_mes = []
    if not df_filtered.empty:
        for _, row in df_filtered.iterrows():
            d = parse_date_br(row.get("data_prevista", ""))
            if dia_sel:
                if d == dia_sel:
                    pieces_mes.append(row)
            elif d and d.year == cal_year and d.month == cal_month:
                pieces_mes.append(row)

    titulo_lista = (
        f"Peças em {dia_sel.strftime('%d/%m/%Y')}"
        if dia_sel
        else f"Peças em {MESES_PT[cal_month - 1]}/{cal_year}"
    )

    if pieces_mes:
        st.divider()
        st.subheader(titulo_lista)
        sorted_pieces = sorted(
            pieces_mes,
            key=lambda x: parse_date_br(x.get("data_prevista", "")) or date.max,
        )
        for p in sorted_pieces:
            pag = p.get("status_pagamento_ref", "pendente")
            c_info, c_btn = st.columns([6, 1])
            c_info.markdown(
                f"📅 **{p.get('data_prevista', '—')}** &nbsp;"
                f"{PAG_ICON.get(pag, '')} **{p.get('cliente', '')}** — "
                f"{p.get('descricao_peca', '')} · "
                f"{STATUS_LABEL.get(p.get('status_bordagem', ''), '')}",
                unsafe_allow_html=True,
            )
            if c_btn.button("✏️", key=f"cal_edit_{p['id']}", use_container_width=True):
                editar_peca(p.to_dict() if hasattr(p, "to_dict") else dict(p))
    elif not df_filtered.empty:
        msg = (
            f"Nenhuma peça para {dia_sel.strftime('%d/%m/%Y')}."
            if dia_sel
            else f"Nenhuma peça com data prevista em {MESES_PT[cal_month - 1]}/{cal_year}."
        )
        st.info(msg)

st.divider()

# ── Adicionar peça ─────────────────────────────────────────────────────────────
with st.expander("➕ Adicionar nova peça ao cronograma"):
    pedidos = read_sheet("pedidos")
    clientes = sorted(pedidos["contato_nome"].dropna().unique().tolist()) if not pedidos.empty else []

    with st.form("nova_peca", clear_on_submit=True):
        c1, c2 = st.columns(2)

        if clientes:
            cliente_sel    = c1.selectbox("Cliente", ["— digitar manualmente —"] + clientes)
            cliente_manual = c1.text_input("Nome (se não estiver na lista)") if cliente_sel == "— digitar manualmente —" else ""
            cliente_final  = cliente_manual.strip() if cliente_sel == "— digitar manualmente —" else cliente_sel
        else:
            cliente_final = c1.text_input("Cliente *")

        descricao_peca  = c2.text_input("Descrição da peça *", placeholder="Ex: Bordado Lenine")
        tamanho         = c1.text_input("Tamanho", placeholder="Ex: 20x20")
        data_prevista   = c2.text_input("Data prevista (DD/MM/AAAA)", placeholder="Ex: 15/04/2026")
        status_bordagem = c1.selectbox("Coluna inicial", STATUS_OPTS, format_func=lambda x: STATUS_LABEL[x])
        status_pag_ref  = c2.selectbox(
            "Status de pagamento", ["pendente", "parcial", "pago"],
            format_func=lambda x: f"{PAG_ICON[x]} {PAG_LABEL[x]}",
        )
        notas = st.text_input("Notas")

        if st.form_submit_button("Adicionar peça", type="primary"):
            nome = cliente_final if isinstance(cliente_final, str) and cliente_final else ""
            if not nome or not descricao_peca.strip():
                st.error("Cliente e descrição são obrigatórios.")
            else:
                append_row("cronograma", {
                    "pedido_id":            "",
                    "cliente":              nome,
                    "descricao_peca":       descricao_peca.strip(),
                    "tamanho":              tamanho.strip(),
                    "data_prevista":        data_prevista.strip(),
                    "status_bordagem":      status_bordagem,
                    "status_pagamento_ref": status_pag_ref,
                    "notas":                notas.strip(),
                })
                st.success(f"Peça de **{nome}** adicionada!")
                reload()
