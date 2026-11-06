# Novo visual (v300)

- Teste local no Windows: dê dois cliques em `TESTAR_NOVO_VISUAL.bat` (cria o ambiente na 1a vez e abre o navegador).
- Se o visual parecer o antigo, aperte Ctrl+F5.

## Como funciona
- `templates/base.html`: nova estrutura (sidebar, cabeçalho de página, tela de login em duas colunas). Mesmos textos, rotas e permissões de antes.
- `static/css/jt-ui.css`: camada visual nova (GERADA). O `styles.css` antigo é carregado por ela, numa camada de menor prioridade.
- Para mexer no visual, edite `static/css/src/jt-ui.src.css` e rode `python tools/build_css.py`.
- Fontes Barlow / Barlow Condensed (licença OFL) ficam em `static/fonts/`, então funciona sem internet.
- Telas novas que usem classes antigas continuam funcionando; ajustes finos entram no arquivo `src`.
