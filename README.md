# Portal de Insumos — J&T Express Brazil

Sistema web interno para **bases e franquias solicitarem insumos** e para a **equipe administrativa aprovar, enviar e controlar estoque, ativos e relatórios**. Funciona em português, com tradução para chinês na interface, e tem tema claro e escuro.

> O histórico de versões fica em [`CHANGELOG.md`](CHANGELOG.md). Notas sobre o visual e como reconstruir o CSS ficam em [`NOVO_VISUAL.md`](NOVO_VISUAL.md).

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Perfis de acesso e permissões](#2-perfis-de-acesso-e-permissões)
3. [Para bases e franquias](#3-para-bases-e-franquias)
4. [Para a administração](#4-para-a-administração)
5. [Produtos e catálogo](#5-produtos-e-catálogo)
6. [Estoque, entrada de materiais e ativos](#6-estoque-entrada-de-materiais-e-ativos)
7. [Usuários e tipos de acesso](#7-usuários-e-tipos-de-acesso)
8. [PDFs e planilhas](#8-pdfs-e-planilhas)
9. [Notificações](#9-notificações)
10. [Interface](#10-interface)
11. [Tecnologia e estrutura de arquivos](#11-tecnologia-e-estrutura-de-arquivos)
12. [Rodar no computador](#12-rodar-no-computador)
13. [Deploy e variáveis de ambiente](#13-deploy-e-variáveis-de-ambiente)
14. [Segurança e boas práticas](#14-segurança-e-boas-práticas)

---

## 1. Visão geral

O portal cobre o ciclo completo de um pedido de insumos:

```text
Base/Franquia solicita ──► Admin analisa ──► Aprova (baixa o estoque) ──► Confirma envio (rastreio) ──► Solicitante acompanha
                                   └──► Recusa (com observação)
```

Em paralelo, o portal controla o **estoque por regional**, as **entradas de materiais com nota fiscal**, o **cadastro de ativos patrimoniais** e gera **relatórios em PDF e planilhas**.

Principais áreas:

| Área | Quem usa | Para quê |
|---|---|---|
| Solicitar insumos | Base, Franquia | Montar o carrinho e enviar o pedido |
| Minhas solicitações | Base, Franquia | Acompanhar status, rastreio e baixar PDF |
| Troca de Insumos – 3 meses | Base | Ver o ciclo de 3 meses e a próxima data disponível |
| Painel admin | Administração | Resumo geral do portal |
| Dashboard Geral de Pedidos | Administração | Todos os pedidos, filtros e totais |
| Troca de Insumos – Bases | Administração | Gerir o ciclo de 3 meses das bases |
| Solicitações pendentes / atendidas | Administração | Analisar, aprovar, recusar e enviar |
| Produtos | Administração | Catálogo, preços, limites e importação |
| Gestão de estoque | Administração | Saldos, gráficos, movimentações, entradas e ativos |
| Usuários e acessos | Administração / Dev | Contas, tipos de acesso e permissões |

---

## 2. Perfis de acesso e permissões

### Tipos padrão

| Tipo | Descrição |
|---|---|
| **Base** | Solicita insumos. Informa o número de pessoas da base a cada pedido. Sujeita ao ciclo de 3 meses. |
| **Franquia** | Solicita insumos. Pode ver valores nos PDFs. Não tem ciclo de 3 meses. |
| **Administrador** | Acesso às áreas administrativas liberadas para ele. |
| **Dev** | Controle total do portal, dos tipos de acesso e das permissões. |

Também é possível criar **tipos de acesso personalizados** (veja a [seção 7](#7-usuários-e-tipos-de-acesso)), por exemplo "Gestão de Franquias".

### Permissões em dois níveis

**Por página** — define quais telas o usuário enxerga no menu e quais rotas consegue abrir:

- Solicitar insumos · Minhas solicitações · Troca de Insumos – 3 meses
- Painel admin · Dashboard Geral de Pedidos · Troca de Insumos – Bases
- Produtos · Gestão de estoque · Usuários e acessos
- Solicitações pendentes · Solicitações atendidas

**Por ação** — controle fino dentro de cada página:

| Página | Ações controladas |
|---|---|
| Produtos | criar, editar dados principais, categorias, unidade/kit, preço, estoque, limites, visibilidade/status, importar, exportar, excluir |
| Gestão de estoque | entrada de materiais, criar ativos e baixar estoque, gerar relatórios |
| Solicitações | editar itens, aprovar/recusar, confirmar envio, excluir |
| Usuários | criar/editar, importar/exportar, status e exclusão |

Além disso, o tipo de acesso pode limitar **quais campos do cadastro de usuário** o administrador pode alterar (nome, login, senha, tipo de acesso, status, base/setor, franquia, telefone, CNPJ e permissões).

As permissões são aplicadas **no menu e também no bloqueio das rotas** — esconder o botão não é a única proteção.

---

## 3. Para bases e franquias

### 3.1 Solicitar insumos (tela inicial)
- Catálogo com **busca**, **filtro por categoria** (com ícone/emoji) e **imagem ampliável** do produto.
- **Carrinho** com quantidades; o pedido é enviado para aprovação.
- **Observação** opcional para a administração.
- **Bases** informam o **número de pessoas** na base (obrigatório).
- Depois de enviar, aparece o botão para **baixar o PDF** da solicitação.

### 3.2 Regras aplicadas automaticamente ao enviar
O portal valida o pedido no servidor antes de gravar:

- O produto precisa estar **ativo**, ser do estoque de **insumos** e **visível** para o tipo do usuário (base ou franquia). Itens marcados como **internos** não podem ser solicitados.
- O usuário precisa ter **regional** cadastrada (MG ou SPN) e o produto precisa ter **saldo na regional**.
- **Limite por produto** (separado para bases e para franquias): se o pedido ultrapassa o limite, ou o limite do período já foi atingido, o envio é recusado informando quanto ainda resta.
- **Bloqueio automático**: ao atingir o limite, o produto fica bloqueado para aquele usuário por um número configurável de dias (padrão 60).
- **Quantidade mínima por pedido** configurável por produto.
- **Kits**: o limite é contado em kits e a quantidade efetiva considera a quantidade por kit.
- **Estoque insuficiente** na regional impede o pedido de franquias.
- **Bases**: só podem fazer nova solicitação quando o ciclo de 3 meses terminar.

Administradores podem criar solicitações sem passar pelos limites de bloqueio.

### 3.3 Minhas solicitações
- Lista paginada das solicitações do próprio usuário, com status colorido e filtros.
- Botão **Consultar nº de rastreio** quando o pedido já foi enviado.
- Download do **PDF** de cada solicitação.

### 3.4 Troca de Insumos – 3 meses (somente bases)
- Mostra o **ciclo de três meses** da base, o **último pedido** e a **próxima data disponível**.
- O ciclo começa automaticamente quando a base envia uma solicitação.
- Enquanto o ciclo estiver ativo, a tela de solicitação informa a data em que será liberada.

### Status de uma solicitação

| Status | Significado |
|---|---|
| Pendente | Enviada, aguardando análise |
| Aguardando envio | Aprovada e já descontada do estoque; falta enviar |
| Enviado | Envio confirmado, com número de rastreio |
| Recusado | Rejeitada pela administração (com observação) |
| Excluído | Removida por quem tem permissão |

---

## 4. Para a administração

### 4.1 Painel admin
Resumo administrativo do portal, ponto de entrada de quem tem acesso administrativo.

### 4.2 Solicitações pendentes
- Lista com **filtros** (tipo, regional, produto, datas, ordenação por mais recentes/antigas, unidade A–Z, quantidade) e **paginação**.
- **Detalhe da solicitação** com resumo, fluxo, itens, observações e **histórico completo de ações** (quem criou, aprovou, enviou etc.).
- **Editar quantidades** dos itens de um pedido pendente.
- **Aprovar**: confere o estoque do responsável na regional, **baixa o saldo**, registra a movimentação e muda o status para *Aguardando envio*. A observação do administrador é opcional.
- **Recusar**: registra a observação no histórico e envia aviso ao Feishu; o status passa para *Recusado*.
  Bloqueios por limite já criados continuam valendo e podem ser revogados na edição do usuário.
- **Confirmar envio**: abre um modal do portal exigindo o **número de rastreio** (observação opcional). O código fica na solicitação e no histórico, e o solicitante consulta em *Minhas solicitações*.
- **Excluir** solicitação (permissão própria).
- **Designação por regional**: a administração define quais usuários aprovam as solicitações de cada regional, e é possível direcionar uma base a administradores específicos. Quem não foi designado não consegue aprovar.

### 4.3 Solicitações atendidas
Pedidos já aprovados, enviados ou recusados, com os mesmos filtros e a possibilidade de confirmar o envio pendente.

### 4.4 Dashboard Geral de Pedidos
- Todos os pedidos de bases e franquias, com filtros e **totais**.
- **Indicadores** e **totais de pedidos confirmados** por produto.
- Respeita a visibilidade por designação de regional.

### 4.5 Troca de Insumos – Bases
- Acompanha o **ciclo automático de 3 meses** de cada base.
- Permite ajustar o ciclo de uma base específica.

---

## 5. Produtos e catálogo

Cadastro completo de cada produto:

- **Dados**: nome, descrição, imagem, categoria e ícone da categoria.
- **Unidade de medida** e **kit** (com quantidade por kit).
- **Preço unitário**.
- **Estoque** disponível, mínimo e máximo.
- **Limites**: limite para bases, limite para franquias, dias de bloqueio após o limite e quantidade mínima por pedido.
- **Visibilidade**: ativo/inativo, item interno, visível para bases, visível para franquias.
- **Tag de estoque**: separa o estoque de *Insumos* (solicitações) do de *Ativos* (patrimônio). Novas tags podem ser criadas.

Recursos da tela de produtos:

- Busca e filtros, ativar/inativar e excluir.
- **Gerenciar categorias** (nome e ícone) e **tags de estoque**.
- **Exportar** o catálogo em planilha `.xlsx` (PT ou ZH).
- **Importar** planilha `.xlsx`: se o `ID` existir o produto é atualizado; sem ID, mas com nome já existente, também atualiza; caso contrário cria um novo.

Colunas da planilha: ID, Nome do produto, Categoria, Ícone da categoria, Unidade de medida, Kit, Quantidade por kit, Descrição, Estoque disponível, Valor unitário, Limite para bases, Limite para franquias, Dias de bloqueio após limite, Quantidade mínima por pedido, Estoque mínimo, Estoque máximo, Tag de estoque, Ativo.

---

## 6. Estoque, entrada de materiais e ativos

### 6.1 Gestão de estoque
- Saldos **por regional (MG e SPN)** e **por responsável pelo estoque** — cada administrador tem o seu estoque individual.
- **Gráfico por categoria** (padrão), busca por produto/categoria e filtro por tipo de solicitante.
- **Lista de produtos** e **histórico de movimentações** (aprovações de pedidos, entradas, baixas de ativos), filtrados por clique ou pesquisa.
- **Pedidos confirmados**: visão de totais por produto, com filtros de tipo, regional, produto e datas.
- Estoque legado ainda não atribuído a um responsável continua sendo consumido pelas aprovações.

### 6.2 Entrada de materiais
- Cadastro manual: produto existente (ou item novo), quantidade, unidade, valor unitário e observações.
- **Nota fiscal opcional**: número, data, valor e arquivo anexado (guardado no Cloudflare R2 quando configurado).
- A entrada **soma ao estoque** da regional escolhida.
- **Importação por planilha** `.xlsx` (modelo para download).
- **Relatório PDF** de entradas por período.
- Cada administrador só sobe estoque nas regionais liberadas para ele.

### 6.3 Ativos patrimoniais
- Cadastro de ativo: nome, **base/franquia**, **regional** (MG, SPN, Matriz, SC CGE, SC RAO), setor, gestor responsável e **itens vinculados** com patrimônio/série.
- Os itens podem ser ligados a produtos do estoque de *Ativos* e **dar baixa no estoque**.
- **Importação por planilha** `.xlsx` (modelo para download).
- **Ficha do ativo em PDF** com linhas de assinatura.
- **Relatório de ativos por período** em PDF, filtrável por unidade.

### 6.4 Relatórios de estoque
- **Relatório de solicitações por período** (PDF): indicadores por status, resumo dos produtos mais pedidos e lista detalhada.
- **Relatório de ativos por período** (PDF).
- **Relatório de entrada de materiais por período** (PDF).

---

## 7. Usuários e tipos de acesso

### Usuários
- **Criação manual** de usuários dentro da plataforma (o cadastro público está desativado).
- Edição de dados, senha individual, regional, base/setor, franquia, telefone e CNPJ.
- **Status**: ativo ou inativo (usuário inativo não consegue entrar).
- **Regional**: MG, SPN ou ambas (MG/SPN); opção, só para Dev, de permitir a uma base ser **atendida por outra regional**.
- **Bloqueios por produto**: a administração vê e pode revogar bloqueios automáticos de limite de cada usuário.
- **Ações em lote**: definir regional e designar administradores de base para vários usuários de uma vez.
- **Exportar** a tabela de usuários, baixar o **modelo** e **importar** usuários por planilha.
- O administrador logado não pode remover o próprio acesso administrativo.

### Tipos de acesso personalizados
- Crie tipos além de Base/Franquia/Administrador (por exemplo, "Gestão de Franquias").
- Para cada tipo, defina **páginas**, **ações** e **campos de usuário** liberados.
- **Troca de senha em lote** para todos os usuários de um tipo.
- Permissões também podem ser ajustadas **individualmente** por usuário, num modal com fundo desfocado.

---

## 8. PDFs e planilhas

### PDFs

| Documento | Onde gerar |
|---|---|
| Solicitação de insumos | Após enviar o pedido, em *Minhas solicitações* e no detalhe admin |
| Relatório de solicitações por período | Gestão de estoque → relatórios |
| Relatório de entrada de materiais | Entrada de materiais |
| Relatório de ativos por período | Ativos |
| Ficha de ativo | Ativos |

Todos usam o mesmo tema (`pdf_theme.py`): fonte Barlow embutida, logo J&T, faixa vermelha, cartões de indicadores, tabelas limpas, rodapé com "Página X de Y" e cabeçalho corrido nas páginas seguintes. Ideogramas chineses são suportados.

Os **valores** aparecem no PDF da solicitação apenas para administradores e franquias.

### Planilhas `.xlsx`
Produtos, usuários, entradas de materiais e ativos têm **modelo para download**, **importação** e (quando aplicável) **exportação**.

---

## 9. Notificações

- **Feishu** (webhook): avisos de solicitação criada, aprovada/recusada/enviada, nova solicitação de acesso, ativo criado e movimentações de estoque.
- **E-mail (SMTP)**: usado para o código de verificação administrativo (suporta TLS na porta 587 e SSL na 465).
- Se uma notificação falhar, a operação principal **não é interrompida**.

---

## 10. Interface

- **Visual J&T**: vermelho `#e60012`, tipografia Barlow, cartões e tabelas limpos.
- **Menu lateral** nas telas logadas e **painel de marca** na tela de login.
- **Tema claro e escuro**, salvo no navegador.
- **Idioma**: português com tradução da interface para chinês (`static/js/i18n.js`).
- Botão flutuante de configurações (tema e idioma) e créditos de desenvolvimento.
- Responsivo para celular e tablet.

---

## 11. Tecnologia e estrutura de arquivos

**Stack**: Python 3 · Flask · SQLite (local) ou Cloudflare D1 (produção) · Cloudflare R2 (arquivos) · ReportLab + svglib (PDFs) · openpyxl (planilhas) · Gunicorn.

```text
app.py                      Aplicação Flask (rotas, regras de negócio, banco, PDFs, planilhas)
pdf_theme.py                Tema visual compartilhado dos PDFs
cloudflare_d1.py            Adaptador do banco Cloudflare D1
cloudflare_r2.py            Envio/leitura de arquivos no Cloudflare R2
cloudflare_d1_schema.sql    Esquema do banco para o D1
requirements.txt            Dependências Python
render.yaml                 Configuração de deploy no Render
templates/                  Páginas HTML (Jinja)
  admin/                    Telas administrativas
static/css/                 jt-ui.css (gerado) e styles.css (legado)
static/css/src/             jt-ui.src.css (fonte do CSS novo)
static/js/                  main.js, theme.js, i18n.js, file-inputs.js
static/fonts/               Fontes do site (woff2) e dos PDFs (fonts/pdf/*.ttf)
static/img/                 Logos e ícones
tools/build_css.py          Gera jt-ui.css a partir do jt-ui.src.css
instance/jt_insumos.db      Banco SQLite local
*.bat                       Atalhos para Windows (veja a seção 12)
```

---

## 12. Rodar no computador

Requisito: **Python 3.10 ou superior** instalado e no PATH.

| Arquivo | Para quê |
|---|---|
| `ABRIR_PORTAL.bat` | Cria o ambiente `.venv`, instala as dependências, inicia o portal e abre o navegador |
| `TESTAR_NOVO_VISUAL.bat` | Testa localmente com SQLite, sem instalação automática e sem tocar no ambiente de produção |
| `instalar_dependencias.bat` | Só instala as dependências |
| `rodar_local.bat` | Só inicia o portal (dependências já instaladas) |
| `corrigir_ambiente_vscode.bat` | Recria o `.venv` e configura o VS Code para usá-lo |

Ou manualmente:

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse **http://localhost:5000**.

- Localmente o banco é o SQLite em `instance/jt_insumos.db`.
- Se o VS Code mostrar `Import "flask_mail" could not be resolved` (ou similar), selecione o interpretador `.venv\Scripts\python.exe` em *Python: Select Interpreter*.
- Se o `.bat` apresentar erro de Python após formatar o PC ou trocar a versão, apague a pasta `.venv` e rode `ABRIR_PORTAL.bat` de novo — ele recria o ambiente sozinho.
- **Para alterar o CSS**, edite `static/css/src/jt-ui.src.css` e rode `python tools/build_css.py`.

---

## 13. Deploy e variáveis de ambiente

Arquitetura de produção: **GitHub** (código) → **Render** (Flask via `gunicorn app:app`) → **Cloudflare D1** (banco) + **Cloudflare R2** (arquivos) + Cloudflare DNS. Passo a passo em [`DEPLOY_CLOUDFLARE_RENDER.md`](DEPLOY_CLOUDFLARE_RENDER.md) e `render.yaml`.

| Variável | Para que serve |
|---|---|
| `SECRET_KEY` | Chave de sessão do Flask (obrigatória em produção) |
| `DATABASE_DRIVER` | `sqlite` (padrão) ou `cloudflare_d1` |
| `DATABASE_PATH` | Caminho do SQLite local |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_D1_DATABASE_ID`, `CLOUDFLARE_API_TOKEN` | Acesso ao D1 |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_URL` | Cloudflare R2 (sem ele, os arquivos são baixados direto pelo navegador) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Administrador criado na primeira execução |
| `DEV_ACCESS_PASSWORD` | Senha de acesso Dev |
| `PUBLIC_BASE_URL` | URL pública, usada nos links das notificações |
| `FEISHU_STOCK_WEBHOOK_URL` | Webhook do Feishu |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`, `MAIL_USE_TLS`, `MAIL_USE_SSL` | Envio de e-mail |
| `ADMIN_CODE_MINUTES` | Validade do código de verificação administrativo |
| `DISABLE_AUTO_INSTALL` | `1` impede a instalação automática de dependências ao iniciar |
| `PORT`, `FLASK_DEBUG`, `AUTO_OPEN_BROWSER` | Execução local |
| `USER_IMPORT_MAX_ROWS`, `ASSET_IMPORT_MAX_BYTES`, `IMPORT_BACKUP_MAX_BYTES` | Limites de importação |
| `D1_*` | Ajustes de desempenho das consultas no D1 |

---

## 14. Segurança e boas práticas

- **Troque as senhas padrão** do administrador e do acesso Dev antes de publicar (`ADMIN_PASSWORD`, `DEV_ACCESS_PASSWORD`) e use uma `SECRET_KEY` longa e aleatória.
- Senhas são guardadas como **hash**; nunca em texto puro.
- O cadastro público de usuários está **desativado** — contas são criadas dentro da plataforma por quem tem permissão.
- Permissões de página e de ação são **validadas no servidor**, não só escondidas no menu.
- Cada aprovação, recusa, envio e exclusão fica registrada no **histórico da solicitação**, e cada alteração de estoque no **histórico de movimentações**.
- Não publique o arquivo `instance/jt_insumos.db` nem tokens do Cloudflare no GitHub.
