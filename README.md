

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


## v33
- Removido o aviso duplicado de envio de código por e-mail na confirmação de login.
- Mensagem de modo dev alterada para: “Insira o código para confirmar o seu login”.


## v47 - Lista oficial de bases/franquias

- Cadastro de usuário passou a selecionar a base/franquia em lista oficial.
- Administração de usuários também usa a mesma lista para criação/edição.
- Bases e franquias só podem ser salvas com unidades válidas da lista.


## v50.1 - Inativar produtos

- Produtos voltaram a ter a ação **Inativar/Ativar** na listagem administrativa.
- Inativar remove o produto das solicitações, mas mantém o registro salvo no banco de dados.
- A ação **Excluir** continua disponível apenas para remoção definitiva.


## v50.2 - Cards responsivos sem rolagem interna

- Listas dentro dos cards agora crescem junto com o conteúdo em vez de criar rolagem interna.
- Tabelas administrativas viram cartões responsivos em telas menores.
- Carrinho, cards de estoque, permissões e movimentações foram ajustados para quebrar linha sem esconder conteúdo.


## v50.3 - Linhas contidas nos cards

- Tabelas compactas do painel administrativo agora respeitam a largura do card.
- Linhas e divisórias não vazam para fora da borda arredondada.


## v51 - Gestão de Ativos

- Gestão de Estoque ganhou submenu com **Gestão de Ativos** e **Gestão de Insumos**.
- Gestão de Insumos mantém a tela atual de estoque, gráficos e movimentações.
- Gestão de Ativos permite adicionar ativos em modal com Nome, Base, Regional, Setor, Gestor e múltiplos itens.
- Relatórios de ativos aparecem na própria tela e podem ser filtrados por base ou regional.


## v51.1 - Ajustes da Gestão de Ativos

- Corrigido o card de Itens cadastrados.
- Lista de bases agora acompanha o filtro regional: MG mostra bases `-MG`, SPN mostra bases `-SP`.
- Quando a regional não possui bases correspondentes, a lista exibe **Sem Dados**.

## v68 - Cadastro em massa de usuários

- Administradores podem baixar um modelo XLSX e importar vários usuários pela página de Usuários.
- Cadastros de franquia possuem nome, número e CNPJ opcional; o CNPJ só aparece para esse tipo de acesso.
- Bases e franquias usam as páginas Solicitar insumos e Minhas solicitações por padrão; administradores recebem todas as páginas.
- Produtos com estoque zerado ficam ocultos para bases e franquias até uma nova entrada de estoque.

## v69 - Favicon oficial J&T

- O favicon usa diretamente o SVG oficial branco da J&T enviado pelo usuário.
- Foram removidas do HTML as referências aos favicons PNG e ICO gerados anteriormente.

## v70 - PDF e pessoas na base

- O PDF de solicitação usa Helvetica nos textos em português e fonte CJK apenas nos trechos chineses, sem espaçamento artificial entre letras.
- O cabeçalho, dados da solicitação e tabela de itens receberam um layout mais limpo.
- O número de pessoas na base é solicitado e exibido somente para usuários do tipo Base.

## v71 - Responsável pelas movimentações

- O histórico de estoque mostra quem adicionou, retirou ou ajustou cada produto.
- São exibidos nome e usuário do responsável.
- Retiradas antigas por solicitação recuperam o administrador que aprovou o pedido quando possível.
- Registros iniciais automáticos são identificados como Sistema.

## v72 - Categorias e pesquisa dinâmica

- O cadastro e a edição de produtos permitem pesquisar categorias já existentes.
- Uma nova categoria pode ser criada pelo botão Nova categoria.
- A listagem de produtos é filtrada imediatamente enquanto o administrador digita.


## v51.2 - Ativos integrados ao estoque

- Itens de ativos agora são selecionados a partir dos produtos cadastrados.
- Cadastro de ativos ganhou quantidade por item e baixa automaticamente o estoque do produto.
- A baixa entra no histórico de movimentações como **Saída para ativo**.
- Regional **Matriz** adicionada; ao selecionar Matriz, o campo Base fica inativo.


## v52 - Alertas Feishu

- Ao enviar uma solicitacao de insumos, o portal envia um card para o grupo Feishu com solicitante, base/franquia, itens, quantidades e botao para abrir o detalhe.
- Ao cadastrar um novo ativo, o portal envia um card para o grupo Feishu com regional, base, setor, gestor, itens, quantidades e botao para abrir o ativo na Gestao de Ativos.
- Configure `PUBLIC_BASE_URL` no Render para os botoes abrirem o dominio correto do portal.
- O webhook pode ser trocado pela variavel `FEISHU_STOCK_WEBHOOK_URL`.

## v59 - Horário de Brasília no Feishu

- Mensagens enviadas para o Feishu agora usam o fuso `America/Sao_Paulo`.
- Datas exibidas nos cards do Feishu aparecem com indicação `(Brasília)`.



## v60 - Correção de caracteres chineses em PDFs

- PDFs de solicitações e ativos agora usam fonte CJK compatível com chinês simplificado.
- Corrigido problema de caracteres chineses aparecendo como quadradinhos/caixas pretas no PDF.
# Atualização v76

- A importação de produtos permite escolher entre manter os dados atuais ou substituir todo o catálogo.
- No modo de manutenção, os produtos são comparados pelo nome normalizado e têm estoque e demais dados atualizados sem duplicação.
- No modo de substituição, somente os produtos da nova planilha permanecem nas telas, sem apagar o histórico de solicitações e movimentações anteriores.

# Atualização v75

- A página **Solicitar insumos** ganhou filtros por categoria, ordenação por nome, estoque ou preço e visualização em cards ou lista.
- Os cards foram realinhados para manter ícone, categoria, descrição, indicadores e quantidade bem distribuídos.
- Categorias agora aceitam um emoji próprio; o ícone escolhido é aplicado a todos os produtos da mesma categoria.
- Produtos podem ter uma quantidade mínima opcional por pedido, validada tanto na tela quanto no servidor.
- Exportação e importação de produtos incluem o ícone da categoria e a quantidade mínima por pedido.
