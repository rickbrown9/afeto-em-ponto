# Setup — Afeto em Ponto

Guia completo para colocar o sistema no ar **gratuitamente**.

---

## 1. Criar a planilha no Google Sheets

1. Acesse [sheets.google.com](https://sheets.google.com)
2. Crie uma planilha chamada **Afeto em Ponto**
3. Anote o nome exato (com acentos) — é o que vai no `secrets.toml`

---

## 2. Criar Service Account no Google Cloud

> Isso permite que o app leia e escreva na planilha automaticamente.

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um projeto novo (ex: `afeto-em-ponto`)
3. No menu lateral: **APIs e Serviços → Biblioteca**
4. Ative as APIs:
   - **Google Sheets API**
   - **Google Drive API**
5. Vá em **APIs e Serviços → Credenciais**
6. Clique **Criar credenciais → Conta de serviço**
   - Nome: `afeto-app`
   - Função: Editor
7. Após criar, clique na conta → aba **Chaves** → **Adicionar chave → JSON**
8. Baixe o arquivo `.json` (guarde com segurança!)

---

## 3. Compartilhar a planilha com a Service Account

1. Abra o arquivo JSON baixado e copie o valor de `client_email`
   (parece: `afeto-app@afeto-em-ponto.iam.gserviceaccount.com`)
2. Abra a planilha **Afeto em Ponto** no Google Sheets
3. Clique em **Compartilhar** → cole o e-mail da service account
4. Permissão: **Editor** → Enviar

---

## 4. Preencher o secrets.toml

Abra o arquivo `.streamlit/secrets.toml` e preencha com os dados do JSON:

```toml
spreadsheet_name = "Afeto em Ponto"
anthropic_api_key = "sk-ant-..."  # opcional, para análise de conversas

[gcp_service_account]
type = "service_account"
project_id = "afeto-em-ponto"
private_key_id = "abc123..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "afeto-app@afeto-em-ponto.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

> ⚠️ O `private_key` deve ter `\n` no lugar das quebras de linha. Abra o JSON,
> copie o campo `private_key` e cole diretamente.

---

## 5. Instalar dependências e popular os dados iniciais

```bash
# Instalar Python (se não tiver) e as libs
pip install -r requirements.txt
pip install toml  # para o script de seed

# Popular dados de março e abril
python seed_data.py
```

---

## 6. Testar localmente

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` no navegador.

---

## 7. Deploy no Streamlit Community Cloud (gratuito)

1. Suba o projeto para o GitHub:
   ```bash
   git init
   git add .
   git commit -m "first commit"
   git remote add origin https://github.com/SEU_USUARIO/afeto-em-ponto.git
   git push -u origin main
   ```
   > O `.gitignore` já protege o `secrets.toml` — ele NÃO vai pro GitHub.

2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Clique **New app** → conecte o repositório
4. Em **Advanced settings → Secrets**, cole o conteúdo do `secrets.toml`
5. Clique **Deploy** — pronto!

Você receberá uma URL pública (ex: `https://afeto-em-ponto.streamlit.app`)
que funciona em qualquer PC ou celular.

---

## Acesso para sua mãe

Compartilhe a URL com ela. Pode usar de qualquer PC (inclusive coworking) ou celular,
sem instalar nada.

Para o sistema funcionar em dois dispositivos ao mesmo tempo:
- Os dados ficam no Google Sheets (nuvem)
- Qualquer atualização feita por uma aparece para a outra em até 30 segundos

---

## Chave Claude (opcional — página Sincronizar)

Para usar a análise automática de conversas com IA:
1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma API key
3. Cole em `anthropic_api_key` no `secrets.toml` (e no painel do Streamlit Cloud)

Custo estimado: menos de R$0,10 por análise (usa o modelo Haiku).

---

## Resumo de custos

| Serviço | Custo |
|---|---|
| Streamlit Community Cloud | **Grátis** |
| Google Sheets / Drive API | **Grátis** |
| GitHub | **Grátis** |
| Claude API (análise de conversas) | ~R$0,05–0,10 por análise |
