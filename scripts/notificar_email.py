"""
Notificação por email — itens pendentes na Caixa de Entrada
============================================================
Envia um email resumo quando há sugestões pendentes de aprovação.
Usa Gmail SMTP com "senha de app" (gratuito, sem biblioteca externa).

Pré-requisito no secrets.toml:
    email_destino    = "seu@email.com"
    gmail_usuario    = "seu_email@gmail.com"
    gmail_senha_app  = "xxxx xxxx xxxx xxxx"

Como criar a senha de app no Gmail:
    1. Acesse myaccount.google.com
    2. Segurança → Verificação em 2 etapas (ative se não tiver)
    3. Pesquise "Senhas de app" → crie uma para "Email"
    4. Use a senha de 16 caracteres gerada

Uso:
    python scripts/notificar_email.py
"""

import sys
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import toml
secrets_path = ROOT / ".streamlit" / "secrets.toml"
if not secrets_path.exists():
    print("ERRO: .streamlit/secrets.toml não encontrado.")
    sys.exit(1)

secrets = toml.load(str(secrets_path))

EMAIL_DESTINO   = secrets.get("email_destino", "")
GMAIL_USUARIO   = secrets.get("gmail_usuario", "")
GMAIL_SENHA_APP = secrets.get("gmail_senha_app", "")

if not all([EMAIL_DESTINO, GMAIL_USUARIO, GMAIL_SENHA_APP]):
    print("Configure email_destino, gmail_usuario e gmail_senha_app no secrets.toml")
    sys.exit(0)

import gspread
import pandas as pd

SPREADSHEET_ID = secrets.get("spreadsheet_id", "")
COLS = ["id", "data", "fonte", "contato", "mensagem_resumo", "acao_sugerida", "dados_json", "status", "criado_em"]

ACAO_LABEL = {
    "novo_lead":           "➕ Novo lead",
    "novo_pedido":         "🛒 Novo pedido",
    "atualizar_pagamento": "💰 Atualizar pagamento",
    "ignorar":             "🚫 Ignorar",
}
FONTE_ICON = {"whatsapp": "📱", "instagram": "📸", "manual": "✏️"}


def get_pendentes() -> list[dict]:
    client = gspread.service_account_from_dict(dict(secrets["gcp_service_account"]))
    sp = client.open_by_key(SPREADSHEET_ID)
    existing = [ws.title for ws in sp.worksheets()]
    if "resumo_diario" not in existing:
        return []
    ws = sp.worksheet("resumo_diario")
    records = ws.get_all_records()
    if not records:
        return []
    df = pd.DataFrame(records)
    for col in COLS:
        if col not in df.columns:
            df[col] = ""
    pendentes = df[df["status"] == "pendente"]
    return pendentes.to_dict("records")


def montar_email(pendentes: list[dict]) -> tuple[str, str]:
    hoje = datetime.now().strftime("%d/%m/%Y")
    assunto = f"Afeto em Ponto — {len(pendentes)} conversa(s) para revisar ({hoje})"

    linhas = [
        f"<h2>📥 Caixa de Entrada — {hoje}</h2>",
        f"<p>Há <strong>{len(pendentes)}</strong> sugestão(ões) aguardando sua aprovação.</p>",
        "<hr>",
    ]

    for item in pendentes:
        fonte   = item.get("fonte", "")
        icone   = FONTE_ICON.get(fonte, "💬")
        contato = item.get("contato", "—")
        resumo  = item.get("mensagem_resumo", "")
        acao    = ACAO_LABEL.get(item.get("acao_sugerida", ""), item.get("acao_sugerida", ""))
        try:
            dados = json.loads(item.get("dados_json", "{}"))
        except Exception:
            dados = {}

        linhas.append(f"<h3>{icone} {contato} &mdash; {acao}</h3>")
        linhas.append(f"<p><em>{resumo}</em></p>")
        if dados:
            linhas.append("<ul>")
            for k, v in dados.items():
                if v:
                    linhas.append(f"<li><strong>{k}:</strong> {v}</li>")
            linhas.append("</ul>")
        linhas.append("<hr>")

    linhas.append("<p>Acesse o app → aba <strong>Sincronizar</strong> para aprovar ou rejeitar.</p>")

    corpo_html = "\n".join(linhas)
    return assunto, corpo_html


def enviar_email(assunto: str, corpo_html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = GMAIL_USUARIO
    msg["To"]      = EMAIL_DESTINO
    msg.attach(MIMEText(corpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USUARIO, GMAIL_SENHA_APP)
        server.sendmail(GMAIL_USUARIO, EMAIL_DESTINO, msg.as_string())


def main():
    print(f"Verificando pendentes — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    pendentes = get_pendentes()

    if not pendentes:
        print("Nenhum item pendente. Email não enviado.")
        return

    print(f"{len(pendentes)} itens pendentes. Enviando email para {EMAIL_DESTINO}...")
    assunto, corpo = montar_email(pendentes)
    enviar_email(assunto, corpo)
    print("✅ Email enviado!")


if __name__ == "__main__":
    main()
