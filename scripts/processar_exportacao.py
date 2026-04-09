"""
Parser de exportações do WhatsApp Business (.txt / .zip)
=========================================================
Lida com os dois formatos que o WhatsApp exporta:

Formato iOS/novo:
    [08/04/2026, 14:32:51] Fulano: mensagem

Formato Android/antigo:
    08/04/2026 14:32 - Fulano: mensagem

Uso como módulo (importado pelo Sincronizar):
    from scripts.processar_exportacao import parse_whatsapp_txt, parse_whatsapp_zip

Uso direto (linha de comando para testar):
    python scripts/processar_exportacao.py arquivo.txt
"""

import re
import zipfile
import io
from pathlib import Path
from typing import Union


# ── Regex patterns ──────────────────────────────────────────────────────────────

# Formato iOS: [08/04/2026, 14:32:51] Nome: texto
PATTERN_IOS = re.compile(
    r"^\[(\d{2}/\d{2}/\d{4}),\s*\d{2}:\d{2}(?::\d{2})?\]\s+([^:]+?):\s+(.*)"
)

# Formato Android: 08/04/2026 14:32 - Nome: texto
PATTERN_ANDROID = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}\s+-\s+([^:]+?):\s+(.*)"
)

# Mensagens do sistema a ignorar
SYSTEM_MSGS = [
    "mensagens e chamadas são protegidos",
    "messages and calls are end-to-end encrypted",
    "<arquivo de mídia oculto>",
    "<media omitted>",
    "imagem omitida",
    "vídeo omitido",
    "áudio omitido",
    "figurinha omitida",
    "documento omitido",
]


def _is_system_msg(texto: str) -> bool:
    t = texto.lower().strip()
    return any(s in t for s in SYSTEM_MSGS)


def parse_whatsapp_txt(conteudo: Union[str, bytes]) -> dict:
    """
    Parseia o texto de uma exportação do WhatsApp.
    Retorna: {"contato": str, "mensagens": list[str]}
    - contato: nome do contato principal (não é "você")
    - mensagens: lista de mensagens no formato "Nome: texto"
    """
    if isinstance(conteudo, bytes):
        # Tenta UTF-8, depois latin-1 (WhatsApp Android às vezes usa)
        try:
            texto = conteudo.decode("utf-8")
        except UnicodeDecodeError:
            texto = conteudo.decode("latin-1", errors="replace")
    else:
        texto = conteudo

    linhas = texto.splitlines()
    participantes: dict[str, int] = {}
    mensagens: list[str] = []
    buffer_nome = None
    buffer_texto = ""

    def flush():
        nonlocal buffer_nome, buffer_texto
        if buffer_nome and buffer_texto.strip() and not _is_system_msg(buffer_texto):
            mensagens.append(f"{buffer_nome}: {buffer_texto.strip()}")
            participantes[buffer_nome] = participantes.get(buffer_nome, 0) + 1
        buffer_nome = None
        buffer_texto = ""

    for linha in linhas:
        m = PATTERN_IOS.match(linha) or PATTERN_ANDROID.match(linha)
        if m:
            flush()
            # grupos: (data, nome, texto)
            buffer_nome = m.group(2).strip()
            buffer_texto = m.group(3)
        elif buffer_nome:
            # Continuação de mensagem multi-linha
            buffer_texto += " " + linha.strip()

    flush()

    if not participantes:
        return {"contato": "Desconhecido", "mensagens": mensagens}

    # O contato principal é quem mais mandou mensagens (exceto "você"/"voce")
    nomes_proprios = {
        k: v for k, v in participantes.items()
        if k.lower() not in ("você", "voce", "you")
    }
    if nomes_proprios:
        contato = max(nomes_proprios, key=nomes_proprios.get)
    else:
        contato = list(participantes.keys())[0]

    return {"contato": contato, "mensagens": mensagens}


def parse_whatsapp_zip(dados: bytes) -> dict:
    """
    Extrai o .txt de dentro de um .zip exportado pelo WhatsApp
    e chama parse_whatsapp_txt.
    """
    with zipfile.ZipFile(io.BytesIO(dados)) as zf:
        txts = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txts:
            return {"contato": "Desconhecido", "mensagens": []}
        with zf.open(txts[0]) as f:
            return parse_whatsapp_txt(f.read())


# ── CLI para teste ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python scripts/processar_exportacao.py <arquivo.txt|arquivo.zip>")
        sys.exit(1)

    path = Path(sys.argv[1])
    dados = path.read_bytes()

    if path.suffix == ".zip":
        resultado = parse_whatsapp_zip(dados)
    else:
        resultado = parse_whatsapp_txt(dados)

    print(f"Contato: {resultado['contato']}")
    print(f"Mensagens: {len(resultado['mensagens'])}")
    print("\n--- Últimas 10 mensagens ---")
    for msg in resultado["mensagens"][-10:]:
        print(msg)
