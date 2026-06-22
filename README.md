

## Rodar local no Windows

1. Extraia o ZIP.
2. Abra a pasta `jt_insumos_portal` no VS Code.
3. Dê dois cliques em `instalar_dependencias.bat`.
4. No VS Code, selecione o interpretador Python da pasta:

```text
.venv\Scripts\python.exe
```

5. Para abrir o site local, dê dois cliques em `rodar_local.bat` ou rode:

```bash
.venv\Scripts\activate
python app.py
```

Acesse no navegador:

```text
http://localhost:5000
```

Se aparecer `ModuleNotFoundError: No module named 'flask_mail'`, `flask_sqlalchemy` ou `sqlalchemy`, significa que o VS Code/terminal ainda não está usando o ambiente `.venv` ou que o `requirements.txt` não foi instalado.


## Corrigir erros do Pylance no VS Code

Se o VS Code mostrar erros como:

- `Import "flask_mail" could not be resolved`
- `Import "flask_sqlalchemy" could not be resolved`
- `Import "sqlalchemy" could not be resolved`

rode o arquivo:

```text
corrigir_ambiente_vscode.bat
```

Ele cria o ambiente `.venv`, instala todas as dependências e configura o VS Code para usar:

```text
.venv\Scripts\python.exe
```

Depois disso, feche e abra o VS Code novamente na pasta do projeto. Se ainda aparecer alerta, use `Ctrl+Shift+P` → `Python: Select Interpreter` → selecione `.venv\Scripts\python.exe`.

## Atualização visual v4

- Design reformulado com layout glassmorphism, tema J&T vermelho/preto e versão clara.
- Logo oficial adicionada em `static/img/logo-jt.svg`.
- Switch fixo no canto inferior direito para alternar tema claro/escuro.
- Créditos fixos no canto inferior esquerdo: `Developed by: Eduardo Rodrigues & Aleffi Silva`.
- Preferência de tema salva no navegador via `localStorage`.



## Update visual v6

- Logo branca no tema escuro e vermelha no tema claro.
- Rodapé de desenvolvimento redesenhado, com ícone de segurança, J&T Express Brazil e CNPJ.
- Mantido layout sem sidebar, com navegação superior.


## Atualização v8

- Animações adicionadas aos cards, tabelas, botões, logo, fundo, carrinho e navegação.
- Correção reforçada do tema claro para manter textos neutros em preto/cinza escuro.


## v9 - Ajustes visuais

- Botões da barra superior: selecionado em vermelho com texto branco; não selecionado em branco com texto vermelho.
- Bloco Developed by convertido para card quadrado lateral esquerdo.
- Ajuste para evitar sobreposição do crédito lateral com os elementos principais em telas médias.


## v10
- Crédito `Developed by` reposicionado para o canto inferior esquerdo em formato quadrado.
- Barra superior reforçada: botão ativo vermelho/branco e botões inativos branco/vermelho.


## Atualização v14
- Adicionada criação manual de usuários pelo painel de usuários.
- Tipo de acesso agora permite Base, Franquia e Administrador.
- Edição de acesso permite trocar usuário para administrador.
- Admin logado não pode remover o próprio acesso administrativo.


## Atualização v15

- Exportação de PDF da solicitação com logo J&T, solicitante, base/franquia, status atual, itens solicitados, observações e total quando permitido pelo perfil.
- Botão de PDF aparece após enviar uma solicitação na tela Solicitar Insumos.
- Também há download de PDF em Minhas Solicitações e no detalhe admin da solicitação.
- Página Produtos ganhou exportação de planilha `.xlsx`.
- Página Produtos ganhou importação de planilha `.xlsx` para criar ou atualizar produtos.

### Colunas aceitas na importação de produtos

`ID`, `Nome do produto`, `Categoria`, `Descrição`, `Estoque disponível`, `Valor unitário`, `Limite para bases`, `Limite para franquias`, `Ativo`.

Se o `ID` existir, o produto é atualizado. Se não houver ID, mas o nome já existir, o produto também é atualizado. Caso contrário, um novo produto é criado.


## Versão v17
- Corrigida duplicidade da logo no tema escuro.
- Barra superior redesenhada com layout mais profissional, responsivo e organizado.


## Abrir sem VS Code

Para abrir fora do VS Code, use `ABRIR_PORTAL.bat`. Ele cria o ambiente local, instala as dependências e abre o navegador automaticamente. Também é possível executar `app.py` diretamente; se faltar alguma dependência, ele tentará instalar automaticamente.


## Atualização v23

- Gestão de Estoque: gráfico padrão agrupado por categoria.
- Pesquisa de produto/categoria acima do gráfico.
- Filtro das listas e movimentações somente por clique ou pesquisa, sem ativar ao passar o mouse.
- Correção visual dos artefatos escuros nos cards de estoque.


## Atualização v25

- Barra superior de bases/franquias ajustada para adaptar largura conforme quantidade de botões.
- Administradores podem definir permissões por página ao criar ou editar usuários.
- Card de permissões abre em modal com blur no fundo.
- Permissões são aplicadas também na exibição do menu e no bloqueio das rotas.


## v26
- Correção visual: animação de brilho dos botões da barra superior agora fica presa dentro dos botões, sem vazar por trás ou para fora.


## v27

- Corrigido brilho dos botões da barra superior para ficar dentro dos botões.
- Corrigido brilho dos itens do submenu para não vazar.
- Adicionadas animações faltantes nos cards da Gestão de Estoque.


## Deploy Cloudflare + Render

Esta versão possui integração com Cloudflare D1 e R2. Veja o arquivo `DEPLOY_CLOUDFLARE_RENDER.md` para o passo a passo resumido.


## v31 - Correção SMTP Feishu

- Adicionado suporte a `MAIL_USE_SSL=true` para SMTP na porta 465.
- Corrigido erro 500 quando o envio do código admin por e-mail falha.
- Agora o erro SMTP aparece nos Logs do Render com servidor, porta, TLS/SSL e mensagem da exceção.

Configuração recomendada para Feishu/Lark com SSL:

```env
MAIL_SERVER=smtp.feishu.cn
MAIL_PORT=465
MAIL_USE_TLS=false
MAIL_USE_SSL=true
MAIL_USERNAME=portal.insumos@seudominio.com
MAIL_PASSWORD=sua_senha_ou_codigo_de_autorizacao
MAIL_DEFAULT_SENDER=portal.insumos@seudominio.com
```


## Atualização v32

- Mensagens do código alteradas para confirmação de login.
- Logo do topo substituída pelo SVG enviado.
