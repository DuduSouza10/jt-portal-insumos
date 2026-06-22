(function () {
  const STORAGE_KEY = 'jt-insumos-language';
  const root = document.documentElement;
  const originalText = new WeakMap();
  let isApplying = false;
  const zh = {
  "Portal de Insumos J&T": "J&T 耗材入口網站",
  "Portal de Insumos": "耗材入口網站",
  "J&T Express Brazil": "J&T Express 巴西",
  "J&T Express • Gestão de insumos": "J&T Express • 耗材管理",
  "Solicitação e controle interno de materiais.": "內部物料申請與管控。",
  "Solicitar insumos": "申請耗材",
  "Minhas solicitações": "我的申請",
  "Painel admin": "管理面板",
  "Produtos": "產品",
  "Gestão de estoque": "庫存管理",
  "Usuários": "使用者",
  "Solicitações": "申請單",
  "Pendentes": "待處理",
  "Atendidas": "已處理",
  "Sair": "登出",
  "Entrar": "登入",
  "Solicitar cadastro": "申請註冊",
  "Tema": "主題",
  "Idioma": "語言",
  "Mudar para tema escuro": "切換至深色主題",
  "Mudar para tema claro": "切換至淺色主題",
  "Alternar tema claro ou escuro": "切換淺色或深色主題",
  "Alternar idioma entre português e chinês tradicional": "切換語言：葡萄牙文 / 繁體中文",
  "Informações de segurança e desenvolvimento": "安全與開發資訊",
  "Developed by: Eduardo Rodrigues & Aleffi Silva": "開發者：Eduardo Rodrigues 與 Aleffi Silva",
  "J&T Express Brazil • CNPJ: 42.584.754/0092-13": "J&T Express 巴西 • CNPJ：42.584.754/0092-13",
  "Login": "登入",
  "Acesse o portal com seu nome de usuário e senha.": "使用您的使用者名稱與密碼進入入口網站。",
  "Nome de usuário": "使用者名稱",
  "Senha": "密碼",
  "Sua senha": "您的密碼",
  "Ainda não tem cadastro?": "尚未註冊？",
  "Solicitar acesso": "申請存取權限",
  "Cadastro": "註冊",
  "Solicite seu acesso ao portal. Um administrador fará a aprovação.": "申請入口網站存取權限，管理員將審核。",
  "Responsável": "負責人",
  "Unidade / Franquia": "單位 / 加盟店",
  "Tipo de acesso": "存取類型",
  "Base": "基地",
  "Franquia": "加盟店",
  "Crie uma senha": "建立密碼",
  "Crie uma senha segura": "建立安全密碼",
  "Enviar cadastro": "送出註冊",
  "Voltar ao login": "返回登入",
  "Confirmação de login": "登入確認",
  "Digite o código para confirmar seu login.": "輸入代碼以確認您的登入。",
  "Código de confirmação": "確認代碼",
  "Confirmar login": "確認登入",
  "Voltar": "返回",
  "Solicitar insumos • Portal de Insumos J&T": "申請耗材 • J&T 耗材入口網站",
  "Pesquise o insumo, informe a quantidade e envie para aprovação administrativa.": "搜尋耗材、輸入數量，並送交管理審核。",
  "Pesquisar por insumo, categoria ou descrição...": "依耗材、類別或描述搜尋...",
  "Atualizar": "更新",
  "Perfil base: valores e estoque não são exibidos.": "基地帳號：不顯示價格與庫存。",
  "Perfil franquia: valores aparecem; estoque permanece oculto.": "加盟店帳號：顯示價格，但庫存維持隱藏。",
  "Perfil admin: você visualiza preço, estoque e limites.": "管理員帳號：可查看價格、庫存與限制。",
  "Nenhum insumo encontrado.": "找不到任何耗材。",
  "Lista de solicitação": "申請清單",
  "0 itens": "0 項",
  "Limpar": "清除",
  "Observações": "備註",
  "Ex.: urgência, rota, responsável pela retirada...": "例如：急件、路線、取貨負責人...",
  "Enviar solicitação": "送出申請",
  "Baixar PDF da solicitação": "下載申請 PDF",
  "Sua lista está vazia.": "您的清單是空的。",
  "Carregando insumos...": "正在載入耗材...",
  "Adicionar": "新增",
  "Quantidade": "數量",
  "Estoque": "庫存",
  "Limite": "限制",
  "Sem limite definido": "未設定限制",
  "Sem descrição cadastrada.": "尚未填寫描述。",
  "Informe uma quantidade válida.": "請輸入有效數量。",
  "Valor oculto": "價格隱藏",
  "Item removido.": "項目已移除。",
  "Adicione pelo menos um insumo antes de enviar.": "送出前請至少新增一項耗材。",
  "Enviando solicitação...": "正在送出申請...",
  "Não foi possível enviar a solicitação.": "無法送出申請。",
  "Erro de conexão ao enviar solicitação.": "送出申請時發生連線錯誤。",
  "Lista limpa.": "清單已清除。",
  "item": "項",
  "itens": "項",
  "Minhas solicitações • Portal de Insumos J&T": "我的申請 • J&T 耗材入口網站",
  "Acompanhe o status das solicitações enviadas.": "追蹤已送出申請的狀態。",
  "Data": "日期",
  "Status": "狀態",
  "Itens": "項目",
  "Total": "總計",
  "Observação admin": "管理員備註",
  "PDF": "PDF",
  "Baixar PDF": "下載 PDF",
  "Nenhuma solicitação enviada.": "尚未送出任何申請。",
  "Dashboard • Portal de Insumos J&T": "儀表板 • J&T 耗材入口網站",
  "Painel administrativo": "管理面板",
  "Resumo geral de cadastros, solicitações e estoque.": "註冊、申請與庫存總覽。",
  "Cadastros pendentes": "待審核註冊",
  "Solicitações pendentes": "待處理申請",
  "Produtos cadastrados": "已註冊產品",
  "Estoque total": "庫存總量",
  "Últimas solicitações": "最近申請",
  "Ver todas": "查看全部",
  "Unidade": "單位",
  "Nenhuma solicitação.": "沒有申請。",
  "Estoque baixo": "低庫存",
  "Gerenciar": "管理",
  "Produto": "產品",
  "Sem alerta de estoque baixo.": "沒有低庫存警示。",
  "Produtos • Portal de Insumos J&T": "產品 • J&T 耗材入口網站",
  "Catálogo de insumos": "耗材目錄",
  "Cadastre, edite, importe e exporte insumos disponíveis para solicitação.": "新增、編輯、匯入與匯出可申請的耗材。",
  "Gestão de Estoque": "庫存管理",
  "Exportar planilha": "匯出試算表",
  "Novo produto": "新增產品",
  "Importar dados": "匯入資料",
  "Colunas aceitas: ID, Nome do produto, Categoria, Descrição, Estoque disponível, Valor unitário, Limite para bases, Limite para franquias, Estoque mínimo, Estoque máximo e Ativo.": "接受欄位：ID、產品名稱、類別、描述、可用庫存、單價、基地限制、加盟店限制、最低庫存、最高庫存與啟用。",
  "Categoria": "類別",
  "Descrição": "描述",
  "Estoque disponível": "可用庫存",
  "Valor unitário": "單價",
  "Unidade de medida": "計量單位",
  "Unidade": "單位",
  "Ex.: un, caixa, rolo, pacote": "例如：個、箱、卷、包",
  "Colunas aceitas: ID, Nome do produto, Categoria, Unidade de medida, Descrição, Estoque disponível, Valor unitário, Limite para bases, Limite para franquias, Estoque mínimo, Estoque máximo e Ativo.": "接受欄位：ID、產品名稱、類別、計量單位、描述、可用庫存、單價、基地限制、加盟店限制、最低庫存、最高庫存與啟用。",
  "Limite para bases": "基地限制",
  "Limite para franquias": "加盟店限制",
  "Estoque mínimo": "最低庫存",
  "Estoque máximo": "最高庫存",
  "Ativo": "啟用",
  "Mín.": "最低",
  "Máx.": "最高",
  "Valor": "價格",
  "Limite base": "基地限制",
  "Limite franquia": "加盟店限制",
  "Situação": "狀況",
  "Ações": "操作",
  "Editar": "編輯",
  "Desativar": "停用",
  "Desativar este produto?": "確定要停用此產品嗎？",
  "Nenhum produto cadastrado.": "尚未註冊產品。",
  "Novo produto • Portal de Insumos J&T": "新增產品 • J&T 耗材入口網站",
  "Editar produto • Portal de Insumos J&T": "編輯產品 • J&T 耗材入口網站",
  "Editar produto": "編輯產品",
  "Preencha as informações do insumo e regras de estoque.": "填寫耗材資訊與庫存規則。",
  "Nome do produto": "產品名稱",
  "Ex.: Embalagens": "例如：包材",
  "Estoque inicial / atual": "初始 / 目前庫存",
  "Valor unitário (R$)": "單價 (R$)",
  "Limite por pedido - Base": "每筆申請限制 - 基地",
  "Limite por pedido - Franquia": "每筆申請限制 - 加盟店",
  "Vazio = sem limite": "空白 = 無限制",
  "Ex.: 100": "例如：100",
  "Ex.: 500": "例如：500",
  "Produto ativo": "產品啟用",
  "Salvar produto": "儲存產品",
  "Cancelar": "取消",
  "Gestão de Estoque • Portal de Insumos J&T": "庫存管理 • J&T 耗材入口網站",
  "Painel de controle com níveis mínimos e máximos, saúde do estoque e movimentações registradas.": "包含最低/最高水位、庫存健康度與移動紀錄的控制面板。",
  "Controle operacional": "營運管控",
  "Visão geral do estoque": "庫存總覽",
  "Acompanhe produtos críticos, estoque saudável, faixa mínima/máxima e todo o histórico de movimentações.": "追蹤關鍵產品、健康庫存、最低/最高範圍與完整移動歷史。",
  "Itens totais": "項目總數",
  "Críticos": "關鍵",
  "Saudáveis": "健康",
  "Estoque atual por produto": "各產品目前庫存",
  "Sem pesquisa, o gráfico mostra o estoque agrupado por categoria. Pesquise um produto para visualizar somente ele.": "未搜尋時，圖表按類別彙總庫存。搜尋產品即可只查看該產品。",
  "Editar produtos": "編輯產品",
  "Pesquisar produto...": "搜尋產品...",
  "Pesquisar produto no estoque": "在庫存中搜尋產品",
  "Produtos disponíveis": "可用產品",
  "Limpar pesquisa": "清除搜尋",
  "Visualização por categoria": "依類別檢視",
  "Limpar filtro": "清除篩選",
  "Gráfico de estoque atual por produto": "各產品目前庫存圖表",
  "Atenção": "注意",
  "Dentro da faixa": "範圍內",
  "Saudável": "健康",
  "Normal": "正常",
  "Prioridade de reposição": "補貨優先順序",
  "Produtos que exigem acompanhamento mais próximo.": "需要更密切追蹤的產品。",
  "Nenhum item encontrado para este produto.": "此產品沒有找到項目。",
  "Mapa de estoque": "庫存地圖",
  "Comparativo rápido entre estoque atual, mínimo e máximo definido.": "快速比較目前庫存、最低與最高設定。",
  "Atual": "目前",
  "Nenhum card encontrado para este produto.": "此產品沒有找到卡片。",
  "Movimentações de estoque": "庫存異動",
  "Entradas, saídas por solicitação, ajustes manuais e importações.": "入庫、申請出庫、手動調整與匯入。",
  "Tipo": "類型",
  "Mov.": "異動",
  "Antes": "之前",
  "Depois": "之後",
  "Solicitação": "申請",
  "Observação": "備註",
  "Nenhuma movimentação registrada ainda.": "尚未記錄任何異動。",
  "Nenhuma movimentação encontrada para este produto.": "此產品沒有找到異動。",
  "Saída por solicitação": "申請出庫",
  "Ajuste manual": "手動調整",
  "Cadastro de produto": "產品建立",
  "Ajuste por importação": "匯入調整",
  "Sem categoria": "無類別",
  "Nenhum produto encontrado.": "找不到任何產品。",
  "Clique para filtrar": "點擊以篩選",
  "Nenhum produto encontrado para a pesquisa.": "搜尋找不到任何產品。",
  "Nenhuma categoria cadastrada.": "尚未註冊類別。",
  "Solicitações • Portal de Insumos J&T": "申請單 • J&T 耗材入口網站",
  "Analise pedidos, aprove, recuse ou acompanhe histórico.": "分析申請、核准、拒絕或追蹤歷史。",
  "Todas": "全部",
  "Aprovadas": "已核准",
  "Recusadas": "已拒絕",
  "Excluídas": "已刪除",
  "Abrir": "開啟",
  "Nenhuma solicitação encontrada.": "找不到任何申請。",
  "Pedidos atendidos": "已處理申請",
  "Ver todas as solicitações": "查看所有申請",
  "Nenhuma solicitação atendida ainda.": "尚無已處理申請。",
  "Detalhe da solicitação": "申請詳情",
  "Revise os itens solicitados e registre a decisão administrativa.": "檢查申請項目並登錄管理決定。",
  "Itens solicitados": "申請項目",
  "Qtd.": "數量",
  "Valor unit.": "單價",
  "Subtotal": "小計",
  "Estoque atual": "目前庫存",
  "Salvar quantidades": "儲存數量",
  "Edite as quantidades antes de aprovar. O estoque será validado na aprovação.": "核准前可編輯數量。核准時將檢查庫存。",
  "Dados": "資料",
  "Observação do solicitante:": "申請人備註：",
  "Enviado em:": "送出時間：",
  "Observação admin:": "管理員備註：",
  "Observação ao aprovar": "核准備註",
  "Aprovar e descontar estoque": "核准並扣減庫存",
  "Motivo da recusa": "拒絕原因",
  "Recusar solicitação": "拒絕申請",
  "Excluir solicitação": "刪除申請",
  "Usuários • Portal de Insumos J&T": "使用者 • J&T 耗材入口網站",
  "Cadastro de usuários": "使用者註冊",
  "Adicione usuários, aprove cadastros, edite acessos ou exclua contas.": "新增使用者、核准註冊、編輯存取或刪除帳戶。",
  "Todos": "全部",
  "Aprovados": "已核准",
  "Recusados": "已拒絕",
  "Adicionar usuário": "新增使用者",
  "Usuário": "使用者",
  "Editar acesso": "編輯存取",
  "Aprovar": "核准",
  "Recusar": "拒絕",
  "Excluir": "刪除",
  "Excluir este usuário?": "確定要刪除此使用者嗎？",
  "Usuário atual": "目前使用者",
  "Nenhum usuário encontrado.": "找不到任何使用者。",
  "Novo usuário • Portal de Insumos J&T": "新增使用者 • J&T 耗材入口網站",
  "Editar usuário • Portal de Insumos J&T": "編輯使用者 • J&T 耗材入口網站",
  "Novo usuário": "新增使用者",
  "Editar usuário": "編輯使用者",
  "Crie ou atualize o acesso ao portal.": "建立或更新入口網站存取權限。",
  "Unidade / Base": "單位 / 基地",
  "Senha inicial do usuário": "使用者初始密碼",
  "Nova senha opcional": "可選的新密碼",
  "deixe vazio para manter a atual": "留空以保留目前密碼",
  "Administrador": "管理員",
  "Pendente": "待處理",
  "Aprovado": "已核准",
  "Recusado": "已拒絕",
  "Excluído": "已刪除",
  "Páginas liberadas": "已開放頁面",
  "Defina exatamente quais telas esse usuário poderá acessar.": "精確設定此使用者可存取哪些畫面。",
  "Editar páginas": "編輯頁面",
  "Controle de acesso": "存取控制",
  "Páginas do usuário": "使用者頁面",
  "Marque as páginas que ficarão disponíveis para este cadastro. As páginas administrativas só funcionam para usuários com tipo de acesso Administrador.": "勾選此帳號可使用的頁面。管理頁面僅適用於存取類型為管理員的使用者。",
  "Fechar": "關閉",
  "Permissões básicas": "基本權限",
  "Marcar tudo": "全選",
  "Concluir": "完成",
  "Salvar acesso": "儲存存取權限",
  "Usuários e acessos": "使用者與存取權限",
  "Permite acessar a tela inicial e enviar solicitações de insumos.": "允許進入首頁並送出耗材申請。",
  "Permite visualizar as solicitações feitas pelo próprio usuário e baixar PDFs.": "允許查看自己送出的申請並下載 PDF。",
  "Permite acessar o resumo administrativo do portal.": "允許進入入口網站管理摘要。",
  "Permite cadastrar, editar, importar e exportar produtos.": "允許新增、編輯、匯入與匯出產品。",
  "Permite acompanhar estoque, gráficos e movimentações.": "允許查看庫存、圖表與異動。",
  "Permite aprovar, criar, editar permissões e excluir usuários.": "允許核准、建立、編輯權限與刪除使用者。",
  "Permite analisar, editar quantidades, aprovar ou recusar pedidos pendentes.": "允許分析、編輯數量、核准或拒絕待處理申請。",
  "Permite visualizar pedidos já aprovados ou recusados.": "允許查看已核准或已拒絕的申請。",
  "Faça login para continuar.": "請先登入以繼續。",
  "Seu cadastro ainda não foi aprovado por um administrador.": "您的註冊尚未由管理員核准。",
  "Nome de usuário ou senha inválidos.": "使用者名稱或密碼無效。",
  "Login realizado com sucesso.": "登入成功。",
  "Faça login novamente.": "請重新登入。",
  "Login confirmado com sucesso.": "登入確認成功。",
  "Código inválido ou expirado.": "代碼無效或已過期。",
  "Preencha todos os campos obrigatórios.": "請填寫所有必填欄位。",
  "Use um nome de usuário com 3 a 40 caracteres: letras, números, ponto, hífen ou underline.": "使用者名稱需為 3 到 40 個字元：字母、數字、句點、連字號或底線。",
  "Já existe cadastro com esse nome de usuário.": "此使用者名稱已存在註冊。",
  "Cadastro enviado. Aguarde aprovação de um administrador.": "註冊已送出，請等待管理員核准。",
  "Você saiu do portal.": "您已登出入口網站。",
  "Seu usuário não possui acesso a esta página.": "您的使用者沒有此頁面的存取權限。",
  "Preencha responsável, unidade, nome de usuário e senha.": "請填寫負責人、單位、使用者名稱與密碼。",
  "Já existe usuário cadastrado com este nome de usuário.": "已有使用者使用此使用者名稱。",
  "Não foi possível adicionar o usuário.": "無法新增使用者。",
  "Usuário adicionado com sucesso.": "使用者新增成功。",
  "Preencha responsável, unidade e nome de usuário.": "請填寫負責人、單位與使用者名稱。",
  "Já existe outro usuário cadastrado com este nome de usuário.": "已有其他使用者使用此使用者名稱。",
  "Acesso do usuário atualizado.": "使用者存取權限已更新。",
  "Você não pode bloquear seu próprio usuário admin.": "您不能封鎖自己的管理員帳號。",
  "Status do usuário atualizado.": "使用者狀態已更新。",
  "Você não pode excluir seu próprio usuário admin.": "您不能刪除自己的管理員帳號。",
  "Não é possível excluir o último administrador aprovado.": "不能刪除最後一位已核准管理員。",
  "Usuário possui solicitações vinculadas; o cadastro foi recusado/desativado em vez de excluído.": "此使用者有關聯申請；帳號已改為拒絕/停用，而非刪除。",
  "Usuário excluído.": "使用者已刪除。",
  "Selecione uma planilha .xlsx para importar.": "請選擇 .xlsx 試算表匯入。",
  "Importe apenas arquivos .xlsx.": "請僅匯入 .xlsx 檔案。",
  "Não foi possível ler a planilha. Verifique se o arquivo está em formato .xlsx válido.": "無法讀取試算表，請確認檔案為有效的 .xlsx 格式。",
  "A planilha está vazia.": "試算表是空的。",
  "Informe o nome do produto.": "請輸入產品名稱。",
  "Produto cadastrado.": "產品已建立。",
  "Produto atualizado.": "產品已更新。",
  "Produto desativado.": "產品已停用。",
  "Apenas solicitações pendentes podem ter quantidades editadas.": "只有待處理申請可以編輯數量。",
  "Todas as quantidades precisam ser maiores que zero.": "所有數量都必須大於零。",
  "Quantidades atualizadas.": "數量已更新。",
  "Nenhuma quantidade foi alterada.": "沒有數量被變更。",
  "Apenas solicitações pendentes podem ser aprovadas.": "只有待處理申請可以核准。",
  "Solicitação aprovada e estoque descontado.": "申請已核准並扣減庫存。",
  "Apenas solicitações pendentes podem ser recusadas.": "只有待處理申請可以拒絕。",
  "Solicitação recusada.": "申請已拒絕。",
  "Solicitação marcada como excluída.": "申請已標記為刪除。",
  "Acesso negado": "拒絕存取",
  "Você não possui permissão para acessar esta página.": "您沒有權限存取此頁面。",
  "Página não encontrada": "找不到頁面",
  "A página solicitada não existe.": "請求的頁面不存在。",
  "Não consegui enviar o código de confirmação por e-mail. Confira as variáveis SMTP no Render e tente novamente.": "無法透過電子郵件發送確認代碼。請檢查 Render 的 SMTP 變數後重試。",
"Ação": "操作",
"Código de confirmação de login": "登入確認代碼",
"Ex.: Eduardo Rodrigues": "例如：Eduardo Rodrigues",
"Ex.: MG BHZ / Administração": "例如：MG BHZ / 管理部",
"Ex.: MG BHZ / Franquia Centro": "例如：MG BHZ / 中心加盟店",
"Ex.: admin": "例如：admin",
"Ex.: mg_bhz": "例如：mg_bhz",
"Importar planilha de produtos (.xlsx)": "匯入產品試算表 (.xlsx)",
"Navegação principal": "主要導覽",
"Nome da base/franquia": "基地/加盟店名稱",
"Nome da base/franquia/área": "基地/加盟店/部門名稱",
"Nome do responsável": "負責人姓名",
"Observação opcional": "選填備註",
"Produto ativo para solicitação": "產品可供申請",
"Portal de Insumos J&T Express": "J&T Express 耗材入口網站",
"Status do cadastro": "註冊狀態",
"Tipo de unidade": "單位類型",
"Tipo:": "類型：",
"Unidade:": "單位：",
"Usuário:": "使用者：",
"Valor unit.": "單價",
"Valor unitário": "單價",
"Solicitações pendentes": "待處理申請",
"×": "×"
};

  Object.assign(zh, {
    "Produtos e estoque": "產品與庫存",
    "Cadastre insumos, valores, limites e parâmetros de estoque mínimo/máximo.": "註冊耗材、價格、限制以及最低/最高庫存參數。",
    "Produtos cadastrados": "已註冊產品",
    "Já cadastrados": "已註冊",
    "Envelope de segurança M": "M 型安全信封",
    "Envelope de segurança P": "P 型安全信封",
    "Envelope médio para envios padrão.": "用於標準寄件的中型信封。",
    "Envelope pequeno para envios leves.": "用於輕量寄件的小型信封。",
    "Etiqueta térmica": "熱敏標籤",
    "Rolo de etiqueta para impressora térmica.": "熱敏印表機用標籤卷。",
    "Lacre plástico": "塑膠封條",
    "Lacre numerado para controle interno.": "用於內部管控的編號封條。",
    "Embalagens": "包裝用品",
    "Etiquetas": "標籤",
    "Operacional": "營運用品",
    "Sem limite": "無限制",
    "un": "個",
    "rolo": "卷",
    "caixa": "箱",
    "pacote": "包",
    "metro": "公尺",
    "kg": "公斤",
    "Normal": "正常",
    "Baixo": "偏低",
    "Crítico": "危急",
    "Alto": "偏高",
    "Importar planilha de produtos (.xlsx)": "匯入產品試算表 (.xlsx)",
    "No file selected.": "尚未選擇檔案。",
    "Browse...": "瀏覽..."
  });

  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];
  const STORAGE_ATTR_PREFIX = 'data-i18n-original-';
  const SKIP_TAGS = new Set(['script', 'style', 'textarea', 'noscript', 'canvas', 'svg', 'path', 'code', 'pre']);
  const VIEWPORT_PADDING = 2200;
  const MAX_TEXT_NODES_PER_RUN = 12000;
  const MAX_ATTR_NODES_PER_RUN = 9000;
  const originalTitle = document.title;
  let scheduled = false;

  const fallbackTerms = [
    ['Solicitações pendentes', '待處理申請'],
    ['Minhas solicitações', '我的申請'],
    ['Painel administrativo', '管理面板'],
    ['Painel admin', '管理面板'],
    ['Gestão de estoque', '庫存管理'],
    ['Gestão de Estoque', '庫存管理'],
    ['Portal de Insumos', '耗材入口網站'],
    ['Solicitar insumos', '申請耗材'],
    ['Solicitar cadastro', '申請註冊'],
    ['Nome de usuário', '使用者名稱'],
    ['Unidade de medida', '計量單位'],
    ['Valor unitário', '單價'],
    ['Estoque disponível', '可用庫存'],
    ['Limite para franquias', '加盟店限制'],
    ['Limite para bases', '基地限制'],
    ['Estoque mínimo', '最低庫存'],
    ['Estoque máximo', '最高庫存'],
    ['Novo produto', '新增產品'],
    ['Editar produto', '編輯產品'],
    ['Baixar PDF', '下載 PDF'],
    ['Exportar planilha', '匯出試算表'],
    ['Importar dados', '匯入資料'],
    ['Produto ativo', '產品啟用'],
    ['Confirmação de login', '登入確認'],
    ['Código de confirmação', '確認代碼'],
    ['Confirmar login', '確認登入'],
    ['Usuários', '使用者'],
    ['Produtos', '產品'],
    ['Solicitações', '申請單'],
    ['Pendentes', '待處理'],
    ['Atendidas', '已處理'],
    ['Responsável', '負責人'],
    ['Categoria', '類別'],
    ['Descrição', '描述'],
    ['Quantidade', '數量'],
    ['Observações', '備註'],
    ['Observação', '備註'],
    ['Status', '狀態'],
    ['Unidade', '單位'],
    ['Produto', '產品'],
    ['Estoque', '庫存'],
    ['Limite', '限制'],
    ['Senha', '密碼'],
    ['Entrar', '登入'],
    ['Sair', '登出'],
    ['Voltar', '返回'],
    ['Salvar', '儲存'],
    ['Cancelar', '取消'],
    ['Editar', '編輯'],
    ['Excluir', '刪除'],
    ['Aprovar', '核准'],
    ['Recusar', '拒絕'],
    ['Atualizar', '更新'],
    ['Adicionar', '新增'],
    ['Limpar', '清除'],
    ['Data', '日期'],
    ['Itens', '項目'],
    ['Total', '總計'],
    ['Valor', '價格'],
    ['Ações', '操作'],
    ['Ação', '操作'],
    ['Tipo', '類型'],
    ['Base', '基地'],
    ['Franquia', '加盟店'],
    ['Admin', '管理員'],
    ['Ativo', '啟用'],
    ['Inativo', '停用'],
    ['Envelope de segurança', '安全信封'],
    ['Envelope médio', '中型信封'],
    ['Envelope pequeno', '小型信封'],
    ['Etiqueta térmica', '熱敏標籤'],
    ['Lacre plástico', '塑膠封條'],
    ['Envelope', '信封'],
    ['etiqueta', '標籤'],
    ['impressora térmica', '熱敏印表機'],
    ['envios padrão', '標準寄件'],
    ['envios leves', '輕量寄件'],
    ['controle interno', '內部管控'],
    ['estoque mínimo/máximo', '最低/最高庫存'],
    ['estoque mínimo', '最低庫存'],
    ['estoque máximo', '最高庫存'],
    ['estoque', '庫存'],
    ['produtos', '產品'],
    ['produto', '產品'],
    ['insumos', '耗材'],
    ['insumo', '耗材'],
    ['valores', '價格'],
    ['limites', '限制'],
    ['parâmetros', '參數'],
    ['cadastrados', '已註冊'],
    ['Cadastre', '註冊'],
    ['mínimo', '最低'],
    ['máximo', '最高'],
    ['para', '用於']
  ].sort(function (a, b) { return b[0].length - a[0].length; });

  function currentLanguage() {
    return localStorage.getItem(STORAGE_KEY) === 'zh-Hant' ? 'zh-Hant' : 'pt-BR';
  }

  function withWhitespace(original, translated) {
    const text = String(original || '');
    return (text.match(/^\s*/) || [''])[0] + translated + (text.match(/\s*$/) || [''])[0];
  }

  function translateFallback(core) {
    let out = core;
    let changed = false;
    fallbackTerms.forEach(function (pair) {
      if (out.indexOf(pair[0]) === -1) return;
      out = out.split(pair[0]).join(pair[1]);
      changed = true;
    });
    return changed ? out : core;
  }

  function translateCore(core) {
    if (!core) return core;
    if (zh[core]) return zh[core];
    let match;
    if ((match = core.match(/^Insira o código para confirmar o seu login:\s*(\d{6})$/))) return `請輸入代碼以確認您的登入：${match[1]}`;
    if ((match = core.match(/^Solicitação #(\d+) enviada para aprovação\. PDF disponível para download\.$/))) return `申請 #${match[1]} 已送交核准。PDF 可供下載。`;
    if ((match = core.match(/^Limite de insumos excedido para (.+)\. Limite permitido: (.+)\.$/))) return `${match[1]} 超出耗材限制。允許限制：${match[2]}。`;
    if ((match = core.match(/^(.+) adicionado à solicitação\.$/))) return `${match[1]} 已加入申請。`;
    if ((match = core.match(/^Estoque:\s*(.+)$/))) return `庫存：${match[1]}`;
    if ((match = core.match(/^Limite:\s*(.+)$/))) return `限制：${match[1]}`;
    if ((match = core.match(/^Unidade:\s*(.+)$/))) return `單位：${match[1]}`;
    if ((match = core.match(/^Min\s+(.+)\s+\/\s+Máx\s+(.+)$/))) return `最低 ${match[1]} / 最高 ${match[2]}`;
    if ((match = core.match(/^Mín\.\s*(.+)$/))) return `最低 ${match[1]}`;
    if ((match = core.match(/^Máx\.\s*(.+)$/))) return `最高 ${match[1]}`;
    if ((match = core.match(/^Atual\s*(.+)$/))) return `目前 ${match[1]}`;
    if ((match = core.match(/^(\d+)\s+item$/))) return `${match[1]} 項`;
    if ((match = core.match(/^(\d+)\s+itens$/))) return `${match[1]} 項`;
    if ((match = core.match(/^(\d+)\s+un$/))) return `${match[1]} 個`;
    if ((match = core.match(/^(\d+)\s+rolo$/))) return `${match[1]} 卷`;
    if ((match = core.match(/^(\d+)\s+rolos$/))) return `${match[1]} 卷`;
    if ((match = core.match(/^(\d+)\s+caixa$/))) return `${match[1]} 箱`;
    if ((match = core.match(/^(\d+)\s+caixas$/))) return `${match[1]} 箱`;
    if ((match = core.match(/^(\d+)\s+pacote$/))) return `${match[1]} 包`;
    if ((match = core.match(/^(\d+)\s+pacotes$/))) return `${match[1]} 包`;
    if ((match = core.match(/^Admin\s*•\s*(.+)$/))) return `管理員 • ${match[1]}`;
    if ((match = core.match(/^Base\s*•\s*(.+)$/))) return `基地 • ${match[1]}`;
    if ((match = core.match(/^Franquia\s*•\s*(.+)$/))) return `加盟店 • ${match[1]}`;
    if ((match = core.match(/^Categoria\s*•\s*(.+)$/))) return `類別 • ${match[1]}`;
    if ((match = core.match(/^Produto\s*•\s*(.+)$/))) return `產品 • ${match[1]}`;
    if ((match = core.match(/^Estoque atual:\s*(.+)$/))) return `目前庫存：${match[1]}`;
    if ((match = core.match(/^Mín\.?:\s*(.+)\s*•\s*Máx\.?:\s*(.+)$/))) return `最低：${match[1]} • 最高：${match[2]}`;
    if ((match = core.match(/^Importação concluída:\s*(.+)$/))) return `匯入完成：${match[1]}`;
    if ((match = core.match(/^Estoque insuficiente para aprovar:\s*(.+)$/))) return `庫存不足，無法核准：${match[1]}`;
    return translateFallback(core);
  }

  function t(value) {
    const text = String(value == null ? '' : value);
    return currentLanguage() === 'zh-Hant' ? withWhitespace(text, translateCore(text.trim())) : text;
  }

  function elementTag(el) {
    return el && el.tagName ? el.tagName.toLowerCase() : '';
  }

  function shouldSkipElement(el) {
    if (!el || !el.closest) return false;
    if (el.closest('[data-no-i18n]')) return true;
    const tag = elementTag(el);
    if (SKIP_TAGS.has(tag)) return true;
    if (el.isContentEditable) return true;
    return !!el.closest('script,style,textarea,noscript,canvas,svg,code,pre,[data-no-i18n]');
  }

  function isVisibleOrNear(el) {
    if (!el || el === document.documentElement || el === document.body) return true;
    if (shouldSkipElement(el)) return false;
    const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    if (style && (style.display === 'none' || style.visibility === 'hidden')) return false;
    const rects = el.getClientRects ? el.getClientRects() : [];
    if (!rects || !rects.length) return false;
    const height = window.innerHeight || document.documentElement.clientHeight || 800;
    const width = window.innerWidth || document.documentElement.clientWidth || 1200;
    for (let i = 0; i < rects.length; i += 1) {
      const r = rects[i];
      if (r.bottom >= -VIEWPORT_PADDING && r.top <= height + VIEWPORT_PADDING && r.right >= -VIEWPORT_PADDING && r.left <= width + VIEWPORT_PADDING) {
        return true;
      }
    }
    return false;
  }

  function shouldSkipTextNode(node) {
    const parent = node && node.parentElement;
    if (!parent) return true;
    if (shouldSkipElement(parent)) return true;
    return !String(node.nodeValue || '').trim();
  }

  function getOriginalText(node) {
    if (!originalText.has(node)) originalText.set(node, node.nodeValue);
    return originalText.get(node) || '';
  }

  function processTextNode(node) {
    if (shouldSkipTextNode(node)) return;
    const parent = node.parentElement;
    if (!isVisibleOrNear(parent)) return;
    const original = getOriginalText(node);
    const next = currentLanguage() === 'zh-Hant' ? t(original) : original;
    if (node.nodeValue !== next) node.nodeValue = next;
  }

  function processAttributes(el) {
    if (!el || !el.getAttribute || shouldSkipElement(el)) return;
    if (!isVisibleOrNear(el)) return;
    ATTRS.forEach(function (attr) {
      if (!el.hasAttribute(attr)) return;
      const key = STORAGE_ATTR_PREFIX + attr;
      if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute(attr) || '');
      const original = el.getAttribute(key) || '';
      const next = currentLanguage() === 'zh-Hant' ? t(original) : original;
      if (el.getAttribute(attr) !== next) el.setAttribute(attr, next);
    });
    const tag = elementTag(el);
    const type = String(el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['button', 'submit', 'reset'].indexOf(type) !== -1 && el.hasAttribute('value')) {
      const key = STORAGE_ATTR_PREFIX + 'value';
      if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute('value') || '');
      const original = el.getAttribute(key) || '';
      const next = currentLanguage() === 'zh-Hant' ? t(original) : original;
      if (el.getAttribute('value') !== next) el.setAttribute('value', next);
    }
  }

  function processVisible(rootNode) {
    const target = rootNode && rootNode.nodeType ? rootNode : (document.body || document.documentElement);
    if (!target) return;

    let textCount = 0;
    let attrCount = 0;

    if (target.nodeType === Node.TEXT_NODE) {
      processTextNode(target);
      return;
    }

    if (target.nodeType === Node.ELEMENT_NODE) processAttributes(target);

    const walker = document.createTreeWalker(
      target,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
      {
        acceptNode: function (candidate) {
          if (candidate.nodeType === Node.ELEMENT_NODE) {
            return shouldSkipElement(candidate) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
          }
          return shouldSkipTextNode(candidate) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    let current = walker.currentNode;
    while (current) {
      if (current.nodeType === Node.ELEMENT_NODE) {
        if (attrCount < MAX_ATTR_NODES_PER_RUN) processAttributes(current);
        attrCount += 1;
      } else if (current.nodeType === Node.TEXT_NODE) {
        if (textCount < MAX_TEXT_NODES_PER_RUN) processTextNode(current);
        textCount += 1;
      }
      current = walker.nextNode();
    }
  }

  function updateDocumentTitle() {
    document.title = currentLanguage() === 'zh-Hant' ? t(originalTitle) : originalTitle;
  }

  function updateButton() {
    const lang = currentLanguage();
    const btn = document.getElementById('languageToggle');
    if (!btn) return;
    btn.setAttribute('aria-pressed', String(lang === 'zh-Hant'));
    btn.classList.toggle('is-zh', lang === 'zh-Hant');
    btn.title = lang === 'zh-Hant' ? '切換為葡萄牙文' : 'Mudar para chinês tradicional';
  }

  function setRootLanguage() {
    root.setAttribute('lang', currentLanguage() === 'zh-Hant' ? 'zh-Hant' : 'pt-BR');
    root.setAttribute('data-language', currentLanguage());
  }

  function dispatchLanguageChange() {
    window.dispatchEvent(new CustomEvent('jt-language-change', { detail: { language: currentLanguage() } }));
  }

  function runVisibleTranslation(rootNode) {
    if (isApplying) return;
    isApplying = true;
    const btn = document.getElementById('languageToggle');
    if (btn) btn.disabled = true;

    const runner = function () {
      try {
        updateDocumentTitle();
        processVisible(rootNode || document.body || document.documentElement);
      } finally {
        if (btn) btn.disabled = false;
        isApplying = false;
        dispatchLanguageChange();
      }
    };

    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(runner, { timeout: 450 });
    } else {
      window.requestAnimationFrame(runner);
    }
  }

  function scheduleVisibleTranslation(rootNode, delay) {
    if (scheduled) return;
    scheduled = true;
    window.setTimeout(function () {
      scheduled = false;
      runVisibleTranslation(rootNode);
    }, typeof delay === 'number' ? delay : 60);
  }

  function applyLanguage(lang) {
    localStorage.setItem(STORAGE_KEY, lang === 'zh-Hant' ? 'zh-Hant' : 'pt-BR');
    setRootLanguage();
    updateButton();
    runVisibleTranslation(document.body || document.documentElement);
  }

  function refresh(rootNode) {
    setRootLanguage();
    updateButton();
    scheduleVisibleTranslation(rootNode || document.body || document.documentElement, 20);
  }

  function installLazyVisibleTranslator() {
    ['scroll', 'resize'].forEach(function (eventName) {
      window.addEventListener(eventName, function () {
        if (currentLanguage() === 'zh-Hant') scheduleVisibleTranslation(document.body || document.documentElement, 80);
      }, { passive: true });
    });

    ['click', 'input', 'change', 'keyup'].forEach(function (eventName) {
      document.addEventListener(eventName, function () {
        if (currentLanguage() === 'zh-Hant') scheduleVisibleTranslation(document.body || document.documentElement, 90);
      }, true);
    });
  }

  window.JT_I18N = { t: t, applyLanguage: applyLanguage, refresh: refresh, getLanguage: currentLanguage };

  document.addEventListener('DOMContentLoaded', function () {
    if (!localStorage.getItem(STORAGE_KEY)) localStorage.setItem(STORAGE_KEY, 'pt-BR');
    setRootLanguage();
    updateButton();
    updateDocumentTitle();
    installLazyVisibleTranslator();

    const btn = document.getElementById('languageToggle');
    if (btn) {
      btn.addEventListener('click', function () {
        applyLanguage(currentLanguage() === 'zh-Hant' ? 'pt-BR' : 'zh-Hant');
      });
    }

    scheduleVisibleTranslation(document.body || document.documentElement, 20);
    window.setTimeout(function () { if (currentLanguage() === 'zh-Hant') refresh(document.body || document.documentElement); }, 260);
  });
})();
