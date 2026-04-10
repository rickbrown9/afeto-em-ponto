"""
Script para popular o Google Sheets com dados de exemplo para demonstração.
Execute UMA VEZ após configurar o secrets.toml:

    python seed_data.py

ATENÇÃO: Este script usa dados fictícios para demonstração.
Os dados reais são inseridos diretamente pelo app.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import toml
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
secrets = toml.load(secrets_path)

import gspread
from datetime import datetime

# Lido do secrets.toml — nunca hardcoded no código
SPREADSHEET_ID = secrets.get("spreadsheet_id", "")
if not SPREADSHEET_ID:
    print("ERRO: spreadsheet_id não encontrado no secrets.toml")
    sys.exit(1)

COLUMNS = {
    "contatos":   ["id", "nome", "telefone", "instagram", "status", "origem", "notas", "criado_em", "atualizado_em"],
    "pedidos":    ["id", "contato_nome", "mes_ref", "descricao", "valor_total", "valor_pago", "status_pagamento", "data_entrega", "criado_em"],
    "cronograma": ["id", "pedido_id", "cliente", "descricao_peca", "tamanho", "data_prevista", "status_bordagem", "status_pagamento_ref", "notas"],
}

def get_spreadsheet():
    client = gspread.service_account_from_dict(dict(secrets["gcp_service_account"]))
    return client.open_by_key(SPREADSHEET_ID)

def ensure_sheets(sp):
    existing = [ws.title for ws in sp.worksheets()]
    for name, cols in COLUMNS.items():
        if name not in existing:
            ws = sp.add_worksheet(title=name, rows=500, cols=len(cols))
            ws.append_row(cols)
            print(f"  Aba '{name}' criada.")
        else:
            ws = sp.worksheet(name)
            if not ws.row_values(1):
                ws.append_row(cols)
                print(f"  Cabeçalho adicionado em '{name}'.")
            else:
                print(f"  Aba '{name}' já existe.")

def seed(sp):
    import uuid
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def new_id():
        return str(uuid.uuid4())[:8].upper()

    def row(sheet, d):
        cols = COLUMNS[sheet]
        return [str(d.get(c, "")) for c in cols]

    ws_c = sp.worksheet("contatos")
    ws_p = sp.worksheet("pedidos")
    ws_k = sp.worksheet("cronograma")

    # ── CONTATOS (dados fictícios para demonstração) ────────────────────────────
    contatos = [
        # Mês 1
        {"nome": "Cliente A",        "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente B",        "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente C",        "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente D",        "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente E",        "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente F",        "status": "cliente", "origem": "WhatsApp", "notas": "Pagamento pendente"},
        # Mês 2
        {"nome": "Cliente G (RJ)",   "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente H (RJ)",   "status": "cliente", "origem": "WhatsApp"},
        {"nome": "Cliente I",        "status": "cliente", "origem": "WhatsApp", "notas": "Sinal pago, falta restante"},
        {"nome": "Cliente J (SP)",   "status": "cliente", "origem": "WhatsApp", "notas": "Sinal pago, falta restante"},
        {"nome": "Cliente K",        "status": "cliente", "origem": "WhatsApp", "notas": "Pagamento pendente"},
        {"nome": "Cliente L",        "status": "cliente", "origem": "WhatsApp", "notas": "Pagamento pendente"},
        {"nome": "Cliente M",        "status": "cliente", "origem": "WhatsApp", "notas": "Pagamento pendente"},
    ]
    contato_ids = {}
    for c in contatos:
        cid = new_id()
        contato_ids[c["nome"]] = cid
        ws_c.append_row(row("contatos", {
            "id": cid, "nome": c["nome"], "telefone": c.get("telefone", ""),
            "instagram": c.get("instagram", ""), "status": c["status"],
            "origem": c.get("origem", ""), "notas": c.get("notas", ""),
            "criado_em": now, "atualizado_em": now,
        }))
    print(f"  {len(contatos)} contatos inseridos.")

    # ── PEDIDOS (dados fictícios para demonstração) ─────────────────────────────
    pedidos = [
        # MÊS 1
        {"contato_nome": "Cliente A", "mes_ref": "2026-03", "descricao": "2 peças bordado",           "valor_total": 180, "valor_pago": 180, "status_pagamento": "pago"},
        {"contato_nome": "Cliente B", "mes_ref": "2026-03", "descricao": "1 peça bordado",            "valor_total": 70,  "valor_pago": 70,  "status_pagamento": "pago"},
        {"contato_nome": "Cliente C", "mes_ref": "2026-03", "descricao": "1 peça bordado",            "valor_total": 90,  "valor_pago": 90,  "status_pagamento": "pago"},
        {"contato_nome": "Cliente D", "mes_ref": "2026-03", "descricao": "1 peça bordado",            "valor_total": 90,  "valor_pago": 90,  "status_pagamento": "pago"},
        {"contato_nome": "Cliente E", "mes_ref": "2026-03", "descricao": "3 peças bordado",           "valor_total": 220, "valor_pago": 220, "status_pagamento": "pago"},
        {"contato_nome": "Cliente F", "mes_ref": "2026-03", "descricao": "2 peças bordado",           "valor_total": 150, "valor_pago": 0,   "status_pagamento": "pendente"},
        # MÊS 2
        {"contato_nome": "Cliente G (RJ)", "mes_ref": "2026-04", "descricao": "Bordado Deixe a Felicidade Entrar", "valor_total": 90,  "valor_pago": 90,  "status_pagamento": "pago",    "data_entrega": "02/04/2026"},
        {"contato_nome": "Cliente H (RJ)", "mes_ref": "2026-04", "descricao": "3 peças Composição Um Lar",         "valor_total": 215, "valor_pago": 215, "status_pagamento": "pago",    "data_entrega": "13/04/2026"},
        {"contato_nome": "Cliente I",      "mes_ref": "2026-04", "descricao": "Bordado de casamento",              "valor_total": 90,  "valor_pago": 50,  "status_pagamento": "parcial", "data_entrega": "04/04/2026"},
        {"contato_nome": "Cliente J (SP)", "mes_ref": "2026-04", "descricao": "3 peças Composição 1",              "valor_total": 240, "valor_pago": 120, "status_pagamento": "parcial"},
        {"contato_nome": "Cliente K",      "mes_ref": "2026-04", "descricao": "Bordado temático",                  "valor_total": 90,  "valor_pago": 0,   "status_pagamento": "pendente", "data_entrega": "03/04/2026"},
        {"contato_nome": "Cliente L",      "mes_ref": "2026-04", "descricao": "2 peças bordado",                   "valor_total": 180, "valor_pago": 0,   "status_pagamento": "pendente"},
        {"contato_nome": "Cliente M",      "mes_ref": "2026-04", "descricao": "Bordado 30x30",                     "valor_total": 100, "valor_pago": 0,   "status_pagamento": "pendente", "data_entrega": "09/04/2026"},
    ]
    for p in pedidos:
        pid = new_id()
        ws_p.append_row(row("pedidos", {"id": pid, **p, "criado_em": now}))
    print(f"  {len(pedidos)} pedidos inseridos.")

    # ── CRONOGRAMA (dados fictícios para demonstração) ──────────────────────────
    cronograma = [
        {"cliente": "Cliente G (RJ)", "descricao_peca": "Deixe a Felicidade Entrar", "tamanho": "",      "data_prevista": "02/04/2026", "status_bordagem": "entregue", "status_pagamento_ref": "pago"},
        {"cliente": "Cliente K",      "descricao_peca": "Bordado temático",           "tamanho": "",      "data_prevista": "03/04/2026", "status_bordagem": "bordando", "status_pagamento_ref": "pendente"},
        {"cliente": "Cliente I",      "descricao_peca": "Bordado de casamento",       "tamanho": "",      "data_prevista": "04/04/2026", "status_bordagem": "bordando", "status_pagamento_ref": "parcial"},
        {"cliente": "Cliente J (SP)", "descricao_peca": "Composição 1 — Peça 1",      "tamanho": "",      "data_prevista": "06/04/2026", "status_bordagem": "entregue", "status_pagamento_ref": "parcial"},
        {"cliente": "Cliente J (SP)", "descricao_peca": "Composição 1 — Peça 2",      "tamanho": "",      "data_prevista": "07/04/2026", "status_bordagem": "entregue", "status_pagamento_ref": "parcial"},
        {"cliente": "Cliente J (SP)", "descricao_peca": "Composição 1 — Peça 3",      "tamanho": "",      "data_prevista": "08/04/2026", "status_bordagem": "bordando", "status_pagamento_ref": "parcial"},
        {"cliente": "Cliente M",      "descricao_peca": "Bordado 30x30",              "tamanho": "30x30", "data_prevista": "09/04/2026", "status_bordagem": "fila",     "status_pagamento_ref": "pendente"},
        {"cliente": "Cliente H (RJ)", "descricao_peca": "Composição Um Lar — Peça 1", "tamanho": "",      "data_prevista": "10/04/2026", "status_bordagem": "fila",     "status_pagamento_ref": "pago"},
        {"cliente": "Cliente H (RJ)", "descricao_peca": "Composição Um Lar — Peça 2", "tamanho": "",      "data_prevista": "11/04/2026", "status_bordagem": "fila",     "status_pagamento_ref": "pago"},
        {"cliente": "Cliente H (RJ)", "descricao_peca": "Composição Um Lar — Peça 3", "tamanho": "",      "data_prevista": "13/04/2026", "status_bordagem": "fila",     "status_pagamento_ref": "pago"},
    ]
    for k in cronograma:
        ws_k.append_row(row("cronograma", {"id": new_id(), "pedido_id": "", "notas": "", **k}))
    print(f"  {len(cronograma)} peças no cronograma inseridas.")


if __name__ == "__main__":
    print("Conectando ao Google Sheets...")
    try:
        sp = get_spreadsheet()
        print("Planilha encontrada.")
        print("Criando abas...")
        ensure_sheets(sp)
        print("Inserindo dados de demonstração...")
        seed(sp)
        print("\nPronto! Acesse o app para ver os dados.")
    except Exception as e:
        print(f"\nERRO: {e}")
        print("\nVerifique se o secrets.toml está preenchido corretamente e se a planilha existe.")
