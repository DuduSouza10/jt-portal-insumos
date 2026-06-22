# Deploy Render + Cloudflare D1/R2

Esta versão usa:

- GitHub para versionar o código.
- Render para rodar o Flask.
- Cloudflare D1 como banco de dados principal.
- Cloudflare R2 para PDFs, planilhas importadas e exportações.
- Cloudflare DNS para domínio.

## Variáveis obrigatórias no Render

```env
DATABASE_DRIVER=cloudflare_d1
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_D1_DATABASE_ID=...
CLOUDFLARE_API_TOKEN=...
SECRET_KEY=...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123
```

## Variáveis R2

```env
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=jt-insumos-storage
R2_PUBLIC_URL=https://arquivos.seudominio.com.br
```

Se o R2 não estiver configurado, o app continua funcionando e apenas baixa os arquivos direto pelo navegador.

## Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

## Local

Localmente o app continua usando SQLite por padrão. Para abrir:

```bat
ABRIR_PORTAL.bat
```

Para testar local com D1, crie um `.env` ou defina as variáveis de ambiente e use:

```env
DATABASE_DRIVER=cloudflare_d1
```
