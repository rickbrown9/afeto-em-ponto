import streamlit as st
import json
import re as _re
import sys
import os
from datetime import datetime
from utils.sheets import append_row, update_row, read_sheet, is_configured

# Garante que a raiz do projeto está no path (para importar scripts/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.processar_exportacao import parse_whatsapp_txt, parse_whatsapp_zip

ANTHROPIC_KEY = st.secrets.get("anthropic_api_key", "")
tem_ia = bool(ANTHROPIC_KEY and not ANTHROPIC_KEY.startswith("sk-ant-..."))

# ── Calcula pendentes para badge no título ──────────────────────────────────────
def _n_pendentes() -> int:
    try:
        df = read_sheet("resumo_diario")
        if df.empty or "status" not in df.columns:
            return 0
        return int((df["status"] == "pendente").sum())
    except Exception:
        return 0

n_pend = _n_pendentes()
titulo_pag = f"Sincronizar ({n_pend})" if n_pend else "Sincronizar — Afeto em Ponto"

st.set_page_config(page_title=titulo_pag, page_icon="💬", layout="wide")
st.title("💬 Sincronizar Conversas")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

if not tem_ia:
    st.info(
        "Para análise automática, adicione `anthropic_api_key` no `.streamlit/secrets.toml`."
    )

ACAO_LABEL = {
    "novo_lead":           "➕ Novo lead",
    "novo_pedido":         "🛒 Novo pedido",
    "atualizar_pagamento": "💰 Atualizar pagamento",
    "ignorar":             "🚫 Ignorar",
}
FONTE_ICON = {"whatsapp": "📱", "instagram": "📸", "manual": "✏️", "outro": "💬"}


# ── Executa ação aprovada no CRM ───────────────────────────────────────────────
def executar_aprovacao(item: dict):
    try:
        dados = json.loads(item.get("dados_json", "{}"))
    except Exception:
        dados = {}

    acao    = item.get("acao_sugerida", "ignorar")
    contato = item.get("contato", "")
    mes_ref = datetime.now().strftime("%Y-%m")

    if acao == "novo_lead":
        append_row("contatos", {
            "nome":      contato,
            "status":    dados.get("status", "lead"),
            "origem":    item.get("fonte", "").capitalize(),
            "notas":     dados.get("notas", item.get("mensagem_resumo", "")),
            "telefone":  "",
            "instagram": "",
        })

    elif acao == "novo_pedido":
        val_total = float(dados.get("valor_total", 0) or 0)
        val_pago  = float(dados.get("valor_pago", 0) or 0)
        if val_pago >= val_total > 0:
            status_p = "pago"
        elif val_pago > 0:
            status_p = "parcial"
        else:
            status_p = dados.get("status_pagamento", "pendente")
        append_row("contatos", {
            "nome": contato, "status": "cliente",
            "origem": item.get("fonte", "").capitalize(),
            "notas": "", "telefone": "", "instagram": "",
        })
        append_row("pedidos", {
            "contato_nome":     contato,
            "mes_ref":          mes_ref,
            "descricao":        dados.get("descricao", item.get("mensagem_resumo", "")),
            "valor_total":      val_total,
            "valor_pago":       val_pago,
            "status_pagamento": status_p,
            "data_entrega":     "",
        })

    elif acao == "atualizar_pagamento":
        pedidos   = read_sheet("pedidos")
        nome_alvo = dados.get("contato_existente", contato)
        matches   = pedidos[pedidos["contato_nome"] == nome_alvo]
        if not matches.empty:
            pid      = matches.iloc[-1]["id"]
            novo_val = float(dados.get("novo_valor_pago", 0) or 0)
            novo_st  = dados.get("novo_status", "parcial")
            update_row("pedidos", pid, {
                "valor_pago":       novo_val,
                "status_pagamento": novo_st,
            })

    update_row("resumo_diario", item["id"], {"status": "aprovado"})


# ── Chama Claude e retorna dict analisado ──────────────────────────────────────
def analisar_com_claude(texto_conversa: str, fonte: str) -> dict | None:
    if not tem_ia:
        return None
    import anthropic
    client_ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt = f"""Você é assistente de CRM do ateliê de bordados Afeto em Ponto.
Analise a conversa abaixo (canal: {fonte}) e retorne APENAS um JSON válido (sem markdown):
{{
  "contato": "nome",
  "acao_sugerida": "novo_lead|novo_pedido|atualizar_pagamento|ignorar",
  "resumo": "uma frase",
  "dados": {{}}
}}
Regras para dados:
- novo_lead: {{"status": "lead|lead_qualificado|cliente", "notas": "..."}}
- novo_pedido: {{"descricao": "...", "valor_total": 0, "valor_pago": 0, "status_pagamento": "pendente|parcial|pago"}}
- atualizar_pagamento: {{"contato_existente": "nome", "novo_valor_pago": 0, "novo_status": "parcial|pago"}}
- ignorar: {{}}

Conversa:
{texto_conversa}"""
    resp = client_ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    raw = _re.sub(r"^```(?:json)?\n?", "", raw)
    raw = _re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def salvar_na_caixa(resultado: dict, fonte: str, contato_fallback: str = ""):
    append_row("resumo_diario", {
        "data":            datetime.now().strftime("%Y-%m-%d"),
        "fonte":           fonte,
        "contato":         resultado.get("contato", contato_fallback),
        "mensagem_resumo": resultado.get("resumo", ""),
        "acao_sugerida":   resultado.get("acao_sugerida", "ignorar"),
        "dados_json":      json.dumps(resultado.get("dados", {}), ensure_ascii=False),
        "status":          "pendente",
    })


# ══════════════════════════════════════════════════════════════════════════════
# 1 — Caixa de Entrada
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📥 Caixa de Entrada")
st.caption(
    "Sugestões pendentes geradas pelo upload de conversas. "
    "Aprove para salvar no CRM ou rejeite para descartar."
)

resumo_df = read_sheet("resumo_diario")
pendentes = (
    resumo_df[resumo_df["status"] == "pendente"].reset_index(drop=True)
    if not resumo_df.empty and "status" in resumo_df.columns
    else None
)

if pendentes is None or pendentes.empty:
    st.info("Nenhuma sugestão pendente. Faça upload de uma conversa abaixo.")
else:
    st.caption(f"{len(pendentes)} sugestão(ões) aguardando revisão.")
    for _, item in pendentes.iterrows():
        fonte      = item.get("fonte", "manual")
        icone      = FONTE_ICON.get(fonte, "💬")
        contato    = item.get("contato", "—")
        resumo_txt = item.get("mensagem_resumo", "")
        acao       = item.get("acao_sugerida", "ignorar")
        data       = item.get("data", "")
        try:
            dados = json.loads(item.get("dados_json", "{}"))
        except Exception:
            dados = {}

        with st.container(border=True):
            col_h, col_d = st.columns([5, 2])
            col_h.markdown(
                f"{icone} **{contato}** &nbsp;&nbsp; `{ACAO_LABEL.get(acao, acao)}`",
                unsafe_allow_html=True,
            )
            col_d.caption(data)
            st.markdown(f"*{resumo_txt}*")

            if dados:
                with st.expander("Ver detalhes"):
                    for k, v in dados.items():
                        if v:
                            st.markdown(f"**{k}:** {v}")

            col_ap, col_rej, _ = st.columns([2, 2, 5])
            if col_ap.button("✅ Aprovar", key=f"ap_{item['id']}",
                             use_container_width=True, type="primary"):
                executar_aprovacao(dict(item))
                st.toast(f"{contato} salvo no CRM!", icon="✅")
                st.rerun()
            if col_rej.button("❌ Rejeitar", key=f"rej_{item['id']}",
                              use_container_width=True):
                update_row("resumo_diario", item["id"], {"status": "rejeitado"})
                st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 2 — Upload de conversa WhatsApp (.txt / .zip)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📱 Importar conversa do WhatsApp")
st.caption(
    "No celular: abra a conversa → **⋮ → Mais → Exportar conversa → Sem mídia**. "
    "O arquivo .txt (ou .zip) chegará nos seus arquivos — envie para aqui."
)

arquivo = st.file_uploader(
    "Arraste o arquivo exportado (.txt ou .zip)",
    type=["txt", "zip"],
)

if arquivo:
    dados_arquivo = arquivo.read()
    conv = parse_whatsapp_zip(dados_arquivo) if arquivo.name.endswith(".zip") \
           else parse_whatsapp_txt(dados_arquivo)

    st.success(f"Conversa com **{conv['contato']}** carregada — {len(conv['mensagens'])} mensagens.")

    with st.expander("Prévia das últimas mensagens"):
        for msg in conv["mensagens"][-20:]:
            st.text(msg)

    if tem_ia:
        if st.button("🤖 Analisar e enviar para Caixa de Entrada", type="primary"):
            with st.spinner("Analisando com Claude..."):
                try:
                    texto = "\n".join(conv["mensagens"][-40:])
                    resultado = analisar_com_claude(texto, "whatsapp")
                    salvar_na_caixa(resultado, "whatsapp", conv["contato"])
                    st.toast("Análise salva! Veja a Caixa de Entrada acima.", icon="📥")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("A IA retornou formato inesperado. Tente novamente.")
                except Exception as e:
                    st.error(f"Erro: {e}")
    else:
        st.warning("Configure `anthropic_api_key` para analisar automaticamente.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 3 — Colar conversa (Instagram / outro canal)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📸 Colar conversa (Instagram ou outro canal)")
st.caption("Cole o texto da conversa do Instagram Direct ou qualquer outra fonte.")

if tem_ia:
    col_txt, col_opt = st.columns([4, 1])
    conversa = col_txt.text_area(
        "Cole a conversa aqui",
        height=200,
        placeholder="Cliente: Oi! Vi seu bordado no insta, quanto custa um 20x20?\nVocê: Olá! O valor é R$ 90...",
    )
    fonte_sel = col_opt.selectbox(
        "Canal",
        ["instagram", "whatsapp", "outro"],
        format_func=lambda x: {"instagram": "📸 Instagram", "whatsapp": "📱 WhatsApp", "outro": "✏️ Outro"}[x],
    )

    if st.button("🤖 Analisar com IA", type="primary", disabled=not conversa.strip()):
        with st.spinner("Analisando..."):
            try:
                resultado = analisar_com_claude(conversa, fonte_sel)
                st.session_state["analise"] = resultado
                st.session_state["fonte_analise"] = fonte_sel
            except json.JSONDecodeError:
                st.error("A IA retornou formato inesperado. Tente novamente.")
            except Exception as e:
                st.error(f"Erro: {e}")

    if "analise" in st.session_state:
        res    = st.session_state["analise"]
        fonte_a = st.session_state.get("fonte_analise", "manual")
        nome_c  = res.get("contato", "")
        if isinstance(nome_c, dict):
            nome_c = nome_c.get("nome", "")
        dados_r = res.get("dados", {})

        st.success(f"**Resumo:** {res.get('resumo', '')}")
        col_c, col_p = st.columns(2)

        with col_c:
            st.markdown("#### Contato detectado")
            st.markdown(f"**Nome:** {nome_c or '—'}")
            st.markdown(f"**Ação:** {ACAO_LABEL.get(res.get('acao_sugerida', ''), '—')}")
            if dados_r.get("notas"):
                st.markdown(f"**Notas:** {dados_r['notas']}")
            if st.button("Salvar na Caixa de Entrada", type="primary", key="salvar_caixa"):
                salvar_na_caixa(res, fonte_a, nome_c)
                st.toast("Salvo na Caixa de Entrada!", icon="📥")
                del st.session_state["analise"]
                st.rerun()

        with col_p:
            if res.get("acao_sugerida") == "novo_pedido" and dados_r:
                st.markdown("#### Pedido detectado")
                st.markdown(f"**Descrição:** {dados_r.get('descricao', '—')}")
                st.markdown(f"**Total:** R$ {dados_r.get('valor_total', 0)}")
                st.markdown(f"**Pago:** R$ {dados_r.get('valor_pago', 0)}")
                st.markdown(f"**Status:** {dados_r.get('status_pagamento', '—')}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 4 — Entrada manual rápida
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("✏️ Entrada manual rápida")
st.caption("Cadastro direto sem IA.")

with st.form("manual_sync", clear_on_submit=True):
    c1, c2   = st.columns(2)
    nome_m   = c1.text_input("Nome do cliente *")
    status_m = c2.selectbox(
        "Status no CRM", ["lead", "lead_qualificado", "cliente"],
        format_func=lambda x: {"lead": "Lead", "lead_qualificado": "Lead Qualificado", "cliente": "Cliente"}[x],
    )
    nota_m     = st.text_area("O que foi conversado?", height=80,
                               placeholder="Ex: Interessada em bordado de casamento 20x20.")
    tem_pedido = st.checkbox("Tem pedido/orçamento?")
    if tem_pedido:
        c3, c4  = st.columns(2)
        desc_m  = c3.text_input("Descrição do pedido")
        total_m = c4.number_input("Valor total (R$)", min_value=0.0, step=10.0)
        pago_m  = c3.number_input("Valor pago (R$)", min_value=0.0, step=10.0)
    else:
        desc_m, total_m, pago_m = "", 0.0, 0.0

    if st.form_submit_button("Salvar no CRM", type="primary"):
        if not nome_m.strip():
            st.error("Nome é obrigatório.")
        else:
            append_row("contatos", {
                "nome": nome_m.strip(), "status": status_m,
                "origem": "Manual", "notas": nota_m.strip(),
                "telefone": "", "instagram": "",
            })
            if tem_pedido and desc_m.strip():
                status_pag = "pago" if pago_m >= total_m > 0 else ("parcial" if pago_m > 0 else "pendente")
                append_row("pedidos", {
                    "contato_nome":     nome_m.strip(),
                    "mes_ref":          datetime.now().strftime("%Y-%m"),
                    "descricao":        desc_m.strip(),
                    "valor_total":      total_m,
                    "valor_pago":       pago_m,
                    "status_pagamento": status_pag,
                    "data_entrega":     "",
                })
            msg = f"**{nome_m}** salvo!" + (" + pedido registrado!" if tem_pedido and desc_m else "")
            st.success(msg)
            st.rerun()
