import streamlit as st
import json
from datetime import datetime
from utils.sheets import append_row, read_sheet, is_configured

st.set_page_config(page_title="Sincronizar — Afeto em Ponto", page_icon="💬", layout="wide")
st.title("💬 Sincronizar Conversas")
st.caption("Cole uma conversa do WhatsApp ou Instagram. A IA vai identificar o que precisa ser atualizado no CRM.")

if not is_configured():
    st.warning("Configure o sistema primeiro. Veja SETUP.md.")
    st.stop()

# Verifica chave Anthropic
ANTHROPIC_KEY = st.secrets.get("anthropic_api_key", "")
tem_ia = bool(ANTHROPIC_KEY and not ANTHROPIC_KEY.startswith("sk-ant-..."))

if not tem_ia:
    st.info(
        "Para usar a análise automática de conversas, adicione sua `anthropic_api_key` "
        "no `.streamlit/secrets.toml`. Por enquanto use o modo manual abaixo."
    )

# ── Análise com IA ─────────────────────────────────────────────────────────────
if tem_ia:
    st.subheader("Analisar conversa")
    conversa = st.text_area(
        "Cole a conversa aqui",
        height=250,
        placeholder="[WhatsApp - 08/04/2026]\nCliente: Oi! Quero encomendar um bordado de casamento 20x20...\nVocê: Olá! O valor é R$ 90...",
    )

    if st.button("Analisar com IA", type="primary", disabled=not conversa.strip()):
        with st.spinner("Analisando conversa..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

                prompt = f"""Você é um assistente de CRM para um ateliê de bordados chamado Afeto em Ponto.
Analise a conversa abaixo e extraia informações relevantes para o CRM.

Retorne APENAS um JSON válido com esta estrutura (sem markdown):
{{
  "contato": {{
    "nome": "Nome completo ou apelido",
    "telefone": "telefone se mencionado, senão vazio",
    "instagram": "@ se mencionado, senão vazio",
    "status": "lead | lead_qualificado | cliente",
    "notas": "resumo do interesse/situação em 1-2 frases"
  }},
  "pedido": {{
    "existe": true ou false,
    "descricao": "descrição da peça pedida",
    "valor_total": número ou 0,
    "valor_pago": número ou 0,
    "status_pagamento": "pendente | parcial | pago"
  }},
  "resumo": "resumo em 1 frase do que aconteceu na conversa"
}}

Conversa:
{conversa}"""

                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                resultado = json.loads(response.content[0].text)
                st.session_state["analise"] = resultado
                st.session_state["conversa_analisada"] = conversa

            except json.JSONDecodeError:
                st.error("A IA retornou um formato inesperado. Tente novamente.")
            except Exception as e:
                st.error(f"Erro ao chamar a API: {e}")

    # Mostra resultado e botões de confirmação
    if "analise" in st.session_state:
        res = st.session_state["analise"]
        st.success(f"**Resumo:** {res.get('resumo', '')}")

        col_c, col_p = st.columns(2)

        with col_c:
            st.markdown("#### Contato detectado")
            c = res.get("contato", {})
            st.markdown(f"**Nome:** {c.get('nome', '—')}")
            st.markdown(f"**Status:** {c.get('status', '—')}")
            st.markdown(f"**Notas:** {c.get('notas', '—')}")
            if st.button("Salvar contato no CRM", type="primary"):
                append_row("contatos", {
                    "nome": c.get("nome", ""),
                    "telefone": c.get("telefone", ""),
                    "instagram": c.get("instagram", ""),
                    "status": c.get("status", "lead"),
                    "origem": "WhatsApp/Instagram",
                    "notas": c.get("notas", ""),
                })
                st.success("Contato salvo!")

        with col_p:
            pedido = res.get("pedido", {})
            if pedido.get("existe"):
                st.markdown("#### Pedido detectado")
                st.markdown(f"**Descrição:** {pedido.get('descricao', '—')}")
                st.markdown(f"**Total:** R$ {pedido.get('valor_total', 0)}")
                st.markdown(f"**Pago:** R$ {pedido.get('valor_pago', 0)}")
                st.markdown(f"**Status:** {pedido.get('status_pagamento', '—')}")
                if st.button("Salvar pedido no Financeiro", type="primary"):
                    mes_ref = datetime.now().strftime("%Y-%m")
                    append_row("pedidos", {
                        "contato_nome": c.get("nome", ""),
                        "mes_ref": mes_ref,
                        "descricao": pedido.get("descricao", ""),
                        "valor_total": pedido.get("valor_total", 0),
                        "valor_pago": pedido.get("valor_pago", 0),
                        "status_pagamento": pedido.get("status_pagamento", "pendente"),
                        "data_entrega": "",
                    })
                    st.success("Pedido salvo!")
            else:
                st.markdown("#### Pedido")
                st.caption("Nenhum pedido identificado nesta conversa.")

st.divider()

# ── Entrada manual ─────────────────────────────────────────────────────────────
st.subheader("Entrada manual rápida")
st.caption("Cadastro rápido sem IA — preencha direto o que sabe da conversa.")

with st.form("manual_sync", clear_on_submit=True):
    c1, c2 = st.columns(2)
    nome_m   = c1.text_input("Nome do cliente *")
    status_m = c2.selectbox("Status no CRM", ["lead", "lead_qualificado", "cliente"],
                             format_func=lambda x: {"lead": "Lead", "lead_qualificado": "Lead Qualificado", "cliente": "Cliente"}[x])
    nota_m   = st.text_area("O que foi conversado?", height=80,
                             placeholder="Ex: Interessada em bordado de casamento 20x20. Pediu orçamento.")
    tem_pedido = st.checkbox("Tem pedido/orçamento?")
    if tem_pedido:
        c3, c4 = st.columns(2)
        desc_m   = c3.text_input("Descrição do pedido")
        total_m  = c4.number_input("Valor total (R$)", min_value=0.0, step=10.0)
        pago_m   = c3.number_input("Valor pago (R$)", min_value=0.0, step=10.0)
    else:
        desc_m, total_m, pago_m = "", 0.0, 0.0

    if st.form_submit_button("Salvar no CRM", type="primary"):
        if not nome_m.strip():
            st.error("Nome é obrigatório.")
        else:
            append_row("contatos", {
                "nome": nome_m.strip(), "status": status_m,
                "origem": "WhatsApp/Instagram", "notas": nota_m.strip(),
                "telefone": "", "instagram": "",
            })
            if tem_pedido and desc_m.strip():
                status_pag = "pago" if pago_m >= total_m > 0 else ("parcial" if pago_m > 0 else "pendente")
                append_row("pedidos", {
                    "contato_nome": nome_m.strip(),
                    "mes_ref": datetime.now().strftime("%Y-%m"),
                    "descricao": desc_m.strip(),
                    "valor_total": total_m,
                    "valor_pago": pago_m,
                    "status_pagamento": status_pag,
                    "data_entrega": "",
                })
            st.success(f"**{nome_m}** salvo no CRM!" + (" + pedido registrado!" if tem_pedido and desc_m else ""))
            st.rerun()
