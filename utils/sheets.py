import gspread
import pandas as pd
import streamlit as st
from datetime import datetime
import uuid

# Colunas de cada aba
COLUMNS = {
    "contatos": [
        "id", "nome", "telefone", "instagram",
        "status", "origem", "notas", "criado_em", "atualizado_em",
    ],
    "pedidos": [
        "id", "contato_nome", "mes_ref", "descricao",
        "valor_total", "valor_pago", "status_pagamento",
        "data_entrega", "criado_em",
    ],
    "cronograma": [
        "id", "pedido_id", "cliente", "descricao_peca",
        "tamanho", "data_prevista", "status_bordagem",
        "status_pagamento_ref", "notas",
    ],
    "custos": [
        "id", "data", "categoria", "descricao", "valor", "criado_em",
    ],
    "resumo_diario": [
        "id", "data", "fonte", "contato",
        "mensagem_resumo", "acao_sugerida",
        "dados_json", "status", "criado_em",
    ],
    "cmv_config": ["id", "item", "valor", "atualizado_em"],
}


def is_configured() -> bool:
    return (
        "gcp_service_account" in st.secrets
        and str(st.secrets["gcp_service_account"].get("project_id", "")) not in ("", "SEU_PROJECT_ID")
    )


@st.cache_resource
def _get_spreadsheet():
    creds_info = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(creds_info)
    # Abre por ID se disponível (mais confiável), senão por nome
    spreadsheet_id = st.secrets.get("spreadsheet_id", "")
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    return client.open(st.secrets["spreadsheet_name"])


def _worksheet(sheet_name: str):
    return _get_spreadsheet().worksheet(sheet_name)


@st.cache_data(ttl=30)
def read_sheet(sheet_name: str) -> pd.DataFrame:
    ws = _worksheet(sheet_name)
    records = ws.get_all_records()
    cols = COLUMNS[sheet_name]
    if not records:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    for col in cols:
        if col not in df.columns:
            df[col] = ""
    return df[cols]


def _new_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def append_row(sheet_name: str, row_dict: dict) -> str:
    row_dict = dict(row_dict)
    row_id = _new_id()
    row_dict["id"] = row_id
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row_dict.setdefault("criado_em", now)
    if "atualizado_em" in COLUMNS[sheet_name]:
        row_dict["atualizado_em"] = now
    ordered = [str(row_dict.get(col, "")) for col in COLUMNS[sheet_name]]
    _worksheet(sheet_name).append_row(ordered, value_input_option="USER_ENTERED")
    read_sheet.clear()
    return row_id


def update_row(sheet_name: str, row_id: str, updates: dict):
    ws = _worksheet(sheet_name)
    df = read_sheet(sheet_name)
    if df.empty:
        return
    matches = df.index[df["id"] == row_id].tolist()
    if not matches:
        return
    row_num = matches[0] + 2  # +1 zero-index, +1 header
    cols = COLUMNS[sheet_name]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "atualizado_em" in cols:
        updates = {**updates, "atualizado_em": now}
    for col, val in updates.items():
        if col in cols:
            ws.update_cell(row_num, cols.index(col) + 1, str(val))
    read_sheet.clear()


def delete_row(sheet_name: str, row_id: str):
    ws = _worksheet(sheet_name)
    df = read_sheet(sheet_name)
    if df.empty:
        return
    matches = df.index[df["id"] == row_id].tolist()
    if not matches:
        return
    ws.delete_rows(matches[0] + 2)
    read_sheet.clear()


def sync_cronograma_pagamento(contato_nome: str, status_pagamento: str):
    """Atualiza status_pagamento_ref em todas as peças do cronograma para este cliente."""
    df = read_sheet("cronograma")
    if df.empty:
        return
    for _, row in df[df["cliente"] == contato_nome].iterrows():
        update_row("cronograma", row["id"], {"status_pagamento_ref": status_pagamento})


def ensure_headers():
    """Cria cabeçalhos nas abas se ainda estiverem vazias."""
    sp = _get_spreadsheet()
    existing = [ws.title for ws in sp.worksheets()]
    for sheet_name, cols in COLUMNS.items():
        if sheet_name not in existing:
            ws = sp.add_worksheet(title=sheet_name, rows=500, cols=len(cols))
        else:
            ws = sp.worksheet(sheet_name)
        first_row = ws.row_values(1)
        if not first_row:
            ws.append_row(cols)
    read_sheet.clear()
