(function () {
  const STORAGE_KEY = 'jt-insumos-language';
  const root = document.documentElement;
  const originalText = new WeakMap();
  let isApplying = false;
  const zh = {
  "Login • Portal de Insumos J&T": "登录 • J&T 耗材门户网站",
  "Cadastro • Portal de Insumos J&T": "注册 • J&T 耗材门户网站",
  "Acesso ao Portal": "登录门户网站",
  "Entre com seu nome de usuário e senha. Se sua conta exigir confirmação, informe o código para concluir o login.": "请输入用户名和密码。如果您的账号需要确认，请输入代码完成登录。",
  "Entre com seu nome de usuário e senha.": "请输入用户名和密码。",
  "Se sua conta exigir confirmação, informe o código para concluir o login.": "如果您的账号需要确认，请输入代码完成登录。",
  "Ainda não tem cadastro? Solicitar acesso": "还没有账号？申请权限",
  "Ex.: admin": "例如：admin",
  "O cadastro só será liberado após aprovação de um administrador.": "注册申请需经管理员批准后才会开通。",
  "Nome do responsável": "负责人姓名",
  "Tipo de unidade": "单位类型",
  "Nome da base": "基地名称",
  "Nome da franquia": "加盟店名称",
  "Selecione a base": "请选择基地",
  "Selecione a franquia": "请选择加盟店",
  "Ex.: Eduardo Rodrigues": "例如：Eduardo Rodrigues",
  "Ex.: mg_bhz": "例如：mg_bhz",
  "Voltar ao login": "返回登录",
  "Cargo": "职位",
  "Digite o cargo da pessoa": "请输入此人的职位",
  "Portal de Insumos J&T": "J&T 耗材门户网站",
  "Portal de Insumos": "耗材门户网站",
  "J&T Express Brazil": "J&T Express 巴西",
  "J&T Express • Gestão de insumos": "J&T Express • 耗材管理",
  "Solicitação e controle interno de materiais.": "内部物料申请与管控。",
  "Solicitar insumos": "申请耗材",
  "Minhas solicitações": "我的申请",
  "Painel admin": "管理面板",
  "Produtos": "产品",
  "Gestão de estoque": "库存管理",
  "Usuários": "用户",
  "Solicitações": "申请单",
  "Pendentes": "待处理",
  "Atendidas": "已处理",
  "Sair": "登出",
  "Entrar": "登入",
  "Solicitar cadastro": "申请注册",
  "Tema": "主题",
  "Idioma": "语言",
  "Mudar para tema escuro": "切换至深色主题",
  "Mudar para tema claro": "切换至浅色主题",
  "Alternar tema claro ou escuro": "切换浅色或深色主题",
  "Alternar idioma entre português e chinês simplificado": "切换语言：葡萄牙语 / 简体中文",
  "Informações de segurança e desenvolvimento": "安全与开发资讯",
  "Developed by: Eduardo Rodrigues & Aleffi Silva": "开发者：Eduardo Rodrigues 与 Aleffi Silva",
  "J&T Express Brazil • CNPJ: 42.584.754/0092-13": "J&T Express 巴西 • CNPJ：42.584.754/0092-13",
  "Login": "登入",
  "Acesse o portal com seu nome de usuário e senha.": "使用您的用户名与密码进入门户网站。",
  "Nome de usuário": "用户名",
  "Senha": "密码",
  "Sua senha": "您的密码",
  "Ainda não tem cadastro?": "尚未注册？",
  "Solicitar acesso": "申请存取权限",
  "Cadastro": "注册",
  "Solicite seu acesso ao portal. Um administrador fará a aprovação.": "申请门户网站存取权限，管理员将审核。",
  "Responsável": "负责人",
  "Unidade / Franquia": "单位 / 加盟店",
  "Tipo de acesso": "存取类型",
  "Base": "基地",
  "Franquia": "加盟店",
  "Crie uma senha": "建立密码",
  "Crie uma senha segura": "建立安全密码",
  "Enviar cadastro": "送出注册",
  "Voltar ao login": "返回登入",
  "Confirmação de login": "登入确认",
  "Digite o código para confirmar seu login.": "输入代码以确认您的登入。",
  "Código de confirmação": "确认代码",
  "Confirmar login": "确认登入",
  "Voltar": "返回",
  "Solicitar insumos • Portal de Insumos J&T": "申请耗材 • J&T 耗材门户网站",
  "Pesquise o insumo, informe a quantidade e envie para aprovação administrativa.": "搜寻耗材、输入数量，并送交管理审核。",
  "Pesquisar por insumo, categoria ou descrição...": "依耗材、类别或描述搜寻...",
  "Atualizar": "更新",
  "Perfil base: valores e estoque não são exibidos.": "基地账号：不显示价格与库存。",
  "Perfil franquia: valores aparecem; estoque permanece oculto.": "加盟店账号：显示价格，但库存维持隐藏。",
  "Perfil admin: você visualiza preço, estoque e limites.": "管理员账号：可查看价格、库存与限制。",
  "Nenhum insumo encontrado.": "找不到任何耗材。",
  "Lista de solicitação": "申请清单",
  "0 itens": "0 项",
  "Limpar": "清除",
  "Observações": "备注",
  "Ex.: urgência, rota, responsável pela retirada...": "例如：急件、路线、取货负责人...",
  "Enviar solicitação": "送出申请",
  "Baixar PDF da solicitação": "下载申请 PDF",
  "Sua lista está vazia.": "您的清单是空的。",
  "Carregando insumos...": "正在载入耗材...",
  "Adicionar": "新增",
  "Quantidade": "数量",
  "Estoque": "库存",
  "Limite": "限制",
  "Sem limite definido": "未设定限制",
  "Sem descrição cadastrada.": "尚未填写描述。",
  "Informe uma quantidade válida.": "请输入有效数量。",
  "Valor oculto": "价格隐藏",
  "Item removido.": "项目已移除。",
  "Adicione pelo menos um insumo antes de enviar.": "送出前请至少新增一项耗材。",
  "Enviando solicitação...": "正在送出申请...",
  "Não foi possível enviar a solicitação.": "无法送出申请。",
  "Erro de conexão ao enviar solicitação.": "送出申请时发生连线错误。",
  "Lista limpa.": "清单已清除。",
  "item": "项",
  "itens": "项",
  "Minhas solicitações • Portal de Insumos J&T": "我的申请 • J&T 耗材门户网站",
  "Acompanhe o status das solicitações enviadas.": "追踪已送出申请的状态。",
  "Data": "日期",
  "Status": "状态",
  "Itens": "项目",
  "Total": "总计",
  "Observação admin": "管理员备注",
  "PDF": "PDF",
  "Baixar PDF": "下载 PDF",
  "Nenhuma solicitação enviada.": "尚未送出任何申请。",
  "Dashboard • Portal de Insumos J&T": "仪表板 • J&T 耗材门户网站",
  "Painel administrativo": "管理面板",
  "Resumo geral de cadastros, solicitações e estoque.": "注册、申请与库存总览。",
  "Cadastros pendentes": "待审核注册",
  "Solicitações pendentes": "待处理申请",
  "Produtos cadastrados": "已注册产品",
  "Estoque total": "库存总量",
  "Últimas solicitações": "最近申请",
  "Ver todas": "查看全部",
  "Unidade": "单位",
  "Nenhuma solicitação.": "没有申请。",
  "Estoque baixo": "低库存",
  "Gerenciar": "管理",
  "Produto": "产品",
  "Sem alerta de estoque baixo.": "没有低库存警示。",
  "Produtos • Portal de Insumos J&T": "产品 • J&T 耗材门户网站",
  "Catálogo de insumos": "耗材目录",
  "Cadastre, edite, importe e exporte insumos disponíveis para solicitação.": "新增、编辑、导入与导出可申请的耗材。",
  "Gestão de Estoque": "库存管理",
  "Exportar planilha": "导出电子表格",
  "Novo produto": "新增产品",
  "Importar dados": "导入资料",
  "Colunas aceitas: ID, Nome do produto, Categoria, Descrição, Estoque disponível, Valor unitário, Limite para bases, Limite para franquias, Estoque mínimo, Estoque máximo e Ativo.": "接受字段：ID、产品名称、类别、描述、可用库存、单价、基地限制、加盟店限制、最低库存、最高库存与启用。",
  "Categoria": "类别",
  "Descrição": "描述",
  "Estoque disponível": "可用库存",
  "Valor unitário": "单价",
  "Unidade de medida": "计量单位",
  "Unidade": "单位",
  "Ex.: un, caixa, rolo, pacote": "例如：个、箱、卷、包",
  "Colunas aceitas: ID, Nome do produto, Categoria, Unidade de medida, Descrição, Estoque disponível, Valor unitário, Limite para bases, Limite para franquias, Estoque mínimo, Estoque máximo e Ativo.": "接受字段：ID、产品名称、类别、计量单位、描述、可用库存、单价、基地限制、加盟店限制、最低库存、最高库存与启用。",
  "Limite para bases": "基地限制",
  "Limite para franquias": "加盟店限制",
  "Estoque mínimo": "最低库存",
  "Estoque máximo": "最高库存",
  "Ativo": "启用",
  "Mín.": "最低",
  "Máx.": "最高",
  "Valor": "价格",
  "Limite base": "基地限制",
  "Limite franquia": "加盟店限制",
  "Situação": "状况",
  "Ações": "操作",
  "Editar": "编辑",
  "Desativar": "停用",
  "Desativar este produto?": "确定要停用此产品吗？",
  "Excluir definitivamente este produto? Essa ação remove o produto do site e do banco de dados.": "确定要永久删除此产品吗？此操作会从网站和数据库中移除该产品。",
  "Nenhum produto cadastrado.": "尚未注册产品。",
  "Novo produto • Portal de Insumos J&T": "新增产品 • J&T 耗材门户网站",
  "Editar produto • Portal de Insumos J&T": "编辑产品 • J&T 耗材门户网站",
  "Editar produto": "编辑产品",
  "Preencha as informações do insumo e regras de estoque.": "填写耗材资讯与库存规则。",
  "Nome do produto": "产品名称",
  "Ex.: Embalagens": "例如：包材",
  "Estoque inicial / atual": "初始 / 当前库存",
  "Valor unitário (R$)": "单价 (R$)",
  "Limite por pedido - Base": "每笔申请限制 - 基地",
  "Limite por pedido - Franquia": "每笔申请限制 - 加盟店",
  "Vazio = sem limite": "空白 = 无限制",
  "Ex.: 100": "例如：100",
  "Ex.: 500": "例如：500",
  "Produto ativo": "产品启用",
  "Salvar produto": "保存产品",
  "Cancelar": "取消",
  "Gestão de Estoque • Portal de Insumos J&T": "库存管理 • J&T 耗材门户网站",
  "Painel de controle com níveis mínimos e máximos, saúde do estoque e movimentações registradas.": "包含最低/最高水位、库存健康度与移动纪录的控制面板。",
  "Controle operacional": "运营管控",
  "Visão geral do estoque": "库存总览",
  "Acompanhe produtos críticos, estoque saudável, faixa mínima/máxima e todo o histórico de movimentações.": "追踪关键产品、健康库存、最低/最高范围与完整移动历史。",
  "Itens totais": "项目总数",
  "Críticos": "关键",
  "Saudáveis": "健康",
  "Estoque atual por produto": "各产品当前库存",
  "Sem pesquisa, o gráfico mostra o estoque agrupado por categoria. Pesquise um produto para visualizar somente ele.": "未搜寻时，图表按类别汇总库存。搜寻产品即可只查看该产品。",
  "Editar produtos": "编辑产品",
  "Pesquisar produto...": "搜寻产品...",
  "Pesquisar produto no estoque": "在库存中搜寻产品",
  "Produtos disponíveis": "可用产品",
  "Limpar pesquisa": "清除搜寻",
  "Visualização por categoria": "依类别检视",
  "Limpar filtro": "清除筛选",
  "Gráfico de estoque atual por produto": "各产品当前库存图表",
  "Atenção": "注意",
  "Dentro da faixa": "范围内",
  "Saudável": "健康",
  "Normal": "正常",
  "Prioridade de reposição": "补货优先顺序",
  "Produtos que exigem acompanhamento mais próximo.": "需要更密切追踪的产品。",
  "Nenhum item encontrado para este produto.": "此产品没有找到项目。",
  "Mapa de estoque": "库存地图",
  "Comparativo rápido entre estoque atual, mínimo e máximo definido.": "快速比较当前库存、最低与最高设定。",
  "Atual": "当前",
  "Nenhum card encontrado para este produto.": "此产品没有找到卡片。",
  "Movimentações de estoque": "库存变动",
  "Entradas, saídas por solicitação, ajustes manuais e importações.": "入库、申请出库、手动调整与导入。",
  "Tipo": "类型",
  "Mov.": "变动",
  "Antes": "之前",
  "Depois": "之后",
  "Solicitação": "申请",
  "Observação": "备注",
  "Nenhuma movimentação registrada ainda.": "尚未记录任何变动。",
  "Nenhuma movimentação encontrada para este produto.": "此产品没有找到变动。",
  "Saída por solicitação": "申请出库",
  "Ajuste manual": "手动调整",
  "Cadastro de produto": "产品建立",
  "Ajuste por importação": "导入调整",
  "Sem categoria": "无类别",
  "Nenhum produto encontrado.": "找不到任何产品。",
  "Clique para filtrar": "点击以筛选",
  "Nenhum produto encontrado para a pesquisa.": "搜寻找不到任何产品。",
  "Nenhuma categoria cadastrada.": "尚未注册类别。",
  "Solicitações • Portal de Insumos J&T": "申请单 • J&T 耗材门户网站",
  "Analise pedidos, aprove, recuse ou acompanhe histórico.": "分析申请、批准、拒绝或追踪历史。",
  "Todas": "全部",
  "Aprovadas": "已批准",
  "Recusadas": "已拒绝",
  "Excluídas": "已删除",
  "Abrir": "开启",
  "Nenhuma solicitação encontrada.": "找不到任何申请。",
  "Pedidos atendidos": "已处理申请",
  "Ver todas as solicitações": "查看所有申请",
  "Nenhuma solicitação atendida ainda.": "尚无已处理申请。",
  "Detalhe da solicitação": "申请详情",
  "Revise os itens solicitados e registre a decisão administrativa.": "检查申请项目并登录管理决定。",
  "Itens solicitados": "申请项目",
  "Qtd.": "数量",
  "Valor unit.": "单价",
  "Subtotal": "小计",
  "Estoque atual": "当前库存",
  "Salvar quantidades": "保存数量",
  "Edite as quantidades antes de aprovar. O estoque será validado na aprovação.": "批准前可编辑数量。批准时将检查库存。",
  "Dados": "资料",
  "Observação do solicitante:": "申请人备注：",
  "Enviado em:": "送出时间：",
  "Observação admin:": "管理员备注：",
  "Observação ao aprovar": "批准备注",
  "Aprovar e descontar estoque": "批准并扣减库存",
  "Motivo da recusa": "拒绝原因",
  "Recusar solicitação": "拒绝申请",
  "Excluir solicitação": "删除申请",
  "Usuários • Portal de Insumos J&T": "用户 • J&T 耗材门户网站",
  "Cadastro de usuários": "用户注册",
  "Adicione usuários, aprove cadastros, edite acessos ou exclua contas.": "新增用户、批准注册、编辑存取或删除账户。",
  "Todos": "全部",
  "Aprovados": "已批准",
  "Recusados": "已拒绝",
  "Adicionar usuário": "新增用户",
  "Usuário": "用户",
  "Editar acesso": "编辑存取",
  "Aprovar": "批准",
  "Recusar": "拒绝",
  "Excluir": "删除",
  "Excluir este usuário?": "确定要删除此用户吗？",
  "Usuário atual": "当前用户",
  "Nenhum usuário encontrado.": "找不到任何用户。",
  "Novo usuário • Portal de Insumos J&T": "新增用户 • J&T 耗材门户网站",
  "Editar usuário • Portal de Insumos J&T": "编辑用户 • J&T 耗材门户网站",
  "Novo usuário": "新增用户",
  "Editar usuário": "编辑用户",
  "Crie ou atualize o acesso ao portal.": "建立或更新门户网站存取权限。",
  "Unidade / Base": "单位 / 基地",
  "Senha inicial do usuário": "用户初始密码",
  "Nova senha opcional": "可选的新密码",
  "deixe vazio para manter a atual": "留空以保留当前密码",
  "Administrador": "管理员",
"ADMINISTRAÇÃO": "管理部门",
  "Pendente": "待处理",
  "Aprovado": "已批准",
  "Recusado": "已拒绝",
  "Excluído": "已删除",
  "Páginas liberadas": "已开放页面",
  "Defina exatamente quais telas esse usuário poderá acessar.": "精确设定此用户可存取哪些画面。",
  "Editar páginas": "编辑页面",
  "Controle de acesso": "存取控制",
  "Páginas do usuário": "用户页面",
  "Marque as páginas que ficarão disponíveis para este cadastro. As páginas administrativas só funcionam para usuários com tipo de acesso Administrador.": "勾选此账号可使用的页面。管理页面仅适用于存取类型为管理员的用户。",
  "Fechar": "关闭",
  "Permissões básicas": "基本权限",
  "Marcar tudo": "全选",
  "Concluir": "完成",
  "Salvar acesso": "保存存取权限",
  "Usuários e acessos": "用户与存取权限",
  "Permite acessar a tela inicial e enviar solicitações de insumos.": "允许进入首页并送出耗材申请。",
  "Permite visualizar as solicitações feitas pelo próprio usuário e baixar PDFs.": "允许查看自己送出的申请并下载 PDF。",
  "Permite acessar o resumo administrativo do portal.": "允许进入门户网站管理摘要。",
  "Permite cadastrar, editar, importar e exportar produtos.": "允许新增、编辑、导入与导出产品。",
  "Permite acompanhar estoque, gráficos e movimentações.": "允许查看库存、图表与变动。",
  "Permite aprovar, criar, editar permissões e excluir usuários.": "允许批准、建立、编辑权限与删除用户。",
  "Permite analisar, editar quantidades, aprovar ou recusar pedidos pendentes.": "允许分析、编辑数量、批准或拒绝待处理申请。",
  "Permite visualizar pedidos já aprovados ou recusados.": "允许查看已批准或已拒绝的申请。",
  "Faça login para continuar.": "请先登入以继续。",
  "Seu cadastro ainda não foi aprovado por um administrador.": "您的注册尚未由管理员批准。",
  "Nome de usuário ou senha inválidos.": "用户名或密码无效。",
  "Login realizado com sucesso.": "登入成功。",
  "Faça login novamente.": "请重新登入。",
  "Login confirmado com sucesso.": "登入确认成功。",
  "Código inválido ou expirado.": "代码无效或已过期。",
  "Preencha todos os campos obrigatórios.": "请填写所有必填字段。",
  "Use um nome de usuário com 3 a 40 caracteres: letras, números, ponto, hífen ou underline.": "用户名需为 3 到 40 个字元：字母、数字、句点、连字号或底线。",
  "Já existe cadastro com esse nome de usuário.": "此用户名已存在注册。",
  "Cadastro enviado. Aguarde aprovação de um administrador.": "注册已送出，请等待管理员批准。",
  "Você saiu do portal.": "您已登出门户网站。",
  "Seu usuário não possui acesso a esta página.": "您的用户没有此页面的存取权限。",
  "Preencha responsável, unidade, nome de usuário e senha.": "请填写负责人、单位、用户名与密码。",
  "Já existe usuário cadastrado com este nome de usuário.": "已有用户使用此用户名。",
  "Não foi possível adicionar o usuário.": "无法新增用户。",
  "Usuário adicionado com sucesso.": "用户新增成功。",
  "Preencha responsável, unidade e nome de usuário.": "请填写负责人、单位与用户名。",
  "Já existe outro usuário cadastrado com este nome de usuário.": "已有其他用户使用此用户名。",
  "Acesso do usuário atualizado.": "用户存取权限已更新。",
  "Você não pode bloquear seu próprio usuário admin.": "您不能封锁自己的管理员账号。",
  "Status do usuário atualizado.": "用户状态已更新。",
  "Você não pode excluir seu próprio usuário admin.": "您不能删除自己的管理员账号。",
  "Não é possível excluir o último administrador aprovado.": "不能删除最后一位已批准管理员。",
  "Usuário possui solicitações vinculadas; o cadastro foi recusado/desativado em vez de excluído.": "此用户有关联申请；账号已改为拒绝/停用，而非删除。",
  "Usuário excluído.": "用户已删除。",
  "Usuário excluído definitivamente do banco de dados.": "用户已从数据库中永久删除。",
  "Excluir definitivamente este usuário do banco de dados?": "确定要从数据库中永久删除此用户吗？",
  "Selecione uma planilha .xlsx para importar.": "请选择 .xlsx 电子表格导入。",
  "Importe apenas arquivos .xlsx.": "请仅导入 .xlsx 档案。",
  "Não foi possível ler a planilha. Verifique se o arquivo está em formato .xlsx válido.": "无法读取电子表格，请确认档案为有效的 .xlsx 格式。",
  "A planilha está vazia.": "电子表格是空的。",
  "Informe o nome do produto.": "请输入产品名称。",
  "Produto cadastrado.": "产品已建立。",
  "Produto atualizado.": "产品已更新。",
  "Produto desativado.": "产品已停用。",
  "Produto excluído definitivamente do banco de dados.": "产品已从数据库中永久删除。",
  "Apenas solicitações pendentes podem ter quantidades editadas.": "只有待处理申请可以编辑数量。",
  "Todas as quantidades precisam ser maiores que zero.": "所有数量都必须大于零。",
  "Quantidades atualizadas.": "数量已更新。",
  "Nenhuma quantidade foi alterada.": "没有数量被变更。",
  "Apenas solicitações pendentes podem ser aprovadas.": "只有待处理申请可以批准。",
  "Solicitação aprovada e estoque descontado.": "申请已批准并扣减库存。",
  "Apenas solicitações pendentes podem ser recusadas.": "只有待处理申请可以拒绝。",
  "Solicitação recusada.": "申请已拒绝。",
  "Solicitação marcada como excluída.": "申请已标记为删除。",
  "Solicitação excluída definitivamente do banco de dados.": "申请已从数据库中永久删除。",
  "Excluir definitivamente esta solicitação do banco de dados?": "确定要从数据库中永久删除此申请吗？",
  "Acesso negado": "拒绝存取",
  "Você não possui permissão para acessar esta página.": "您没有权限存取此页面。",
  "Página não encontrada": "找不到页面",
  "A página solicitada não existe.": "请求的页面不存在。",
  "Não consegui enviar o código de confirmação por e-mail. Confira as variáveis SMTP no Render e tente novamente.": "无法透过电子邮件发送确认代码。请检查 Render 的 SMTP 变数后重试。",
"Ação": "操作",
"Código de confirmação de login": "登入确认代码",
"Ex.: Eduardo Rodrigues": "例如：Eduardo Rodrigues",
"Ex.: MG BHZ / Administração": "例如：MG BHZ / 管理部",
"Ex.: MG BHZ / Franquia Centro": "例如：MG BHZ / 中心加盟店",
"Ex.: admin": "例如：admin",
"Ex.: mg_bhz": "例如：mg_bhz",
"Importar planilha de produtos (.xlsx)": "导入产品电子表格 (.xlsx)",
"Navegação principal": "主要导航",
"Nome da base/franquia": "基地/加盟店名称",
"Selecione a base/franquia": "请选择基地/加盟店",
"Nome da base/franquia/área": "基地/加盟店/部门名称",
"Nome da base": "基地名称",
"Nome da franquia": "加盟店名称",
"Selecione a base": "请选择基地",
"Selecione a franquia": "请选择加盟店",
"Cargo": "职位",
"Ex.: Supervisor de Qualidade": "例如：质量主管",
"Nome do responsável": "负责人姓名",
"Observação opcional": "选填备注",
"Produto ativo para solicitação": "产品可供申请",
"Portal de Insumos J&T Express": "J&T Express 耗材门户网站",
"Status do cadastro": "注册状态",
"Tipo de unidade": "单位类型",
"Tipo:": "类型：",
"Unidade:": "单位：",
"Usuário:": "用户：",
"Valor unit.": "单价",
"Valor unitário": "单价",
"Solicitações pendentes": "待处理申请",
"×": "×"
};

  Object.assign(zh, {
    "Produtos e estoque": "产品与库存",
    "Cadastre insumos, valores, limites e parâmetros de estoque mínimo/máximo.": "注册耗材、价格、限制以及最低/最高库存参数。",
    "Produtos cadastrados": "已注册产品",
    "Já cadastrados": "已注册",
    "Envelope de segurança M": "M 型安全信封",
    "Envelope de segurança P": "P 型安全信封",
    "Envelope médio para envios padrão.": "用于标准寄件的中型信封。",
    "Envelope pequeno para envios leves.": "用于轻量寄件的小型信封。",
    "Etiqueta térmica": "热敏标签",
    "Rolo de etiqueta para impressora térmica.": "热敏打印机用标签卷。",
    "Lacre plástico": "塑料封条",
    "Lacre numerado para controle interno.": "用于内部管控的编号封条。",
    "Embalagens": "包装用品",
    "Etiquetas": "标签",
    "Operacional": "运营用品",
    "Sem limite": "无限制",
    "un": "个",
    "rolo": "卷",
    "caixa": "箱",
    "pacote": "包",
    "metro": "米",
    "kg": "公斤",
    "Normal": "正常",
    "Baixo": "偏低",
    "Crítico": "危急",
    "Alto": "偏高",
    "Importar planilha de produtos (.xlsx)": "导入产品电子表格 (.xlsx)",
    "No file selected.": "尚未选择档案。",

    "Exportação": "导出",
    "Escolha o idioma da planilha": "选择电子表格语言",
    "Selecione se a planilha será exportada em português ou chinês simplificado.": "选择电子表格要以葡萄牙语或简体中文导出。",
    "Português": "葡萄牙语",
    "Cabeçalhos e dados em português.": "字段标题与资料为葡萄牙语。",
    "Chinês simplificado": "简体中文",
    "Cabeçalhos bilíngues e dados conhecidos traduzidos.": "双语字段标题与已知资料翻译。",
    "Browse...": "浏览..."
  });


  Object.assign(zh, {
    "Selecione se a planilha será exportada em português ou chinês simplificado.": "选择电子表格导出为葡萄牙语或简体中文。",
    "Chinês simplificado": "简体中文",
    "Cabeçalhos bilíngues e dados conhecidos traduzidos.": "双语字段标题和已知数据会被翻译。",
    "Mudar para chinês simplificado": "切换为简体中文",
    "Alternar idioma entre português e chinês simplificado": "切换语言：葡萄牙语 / 简体中文",
    "Envelope de segurança M": "M 型安全信封",
    "Envelope de segurança P": "P 型安全信封",
    "Envelope médio para envios padrão.": "用于标准寄件的中型信封。",
    "Envelope pequeno para envios leves.": "用于轻量寄件的小型信封。",
    "Etiqueta térmica": "热敏标签",
    "Rolo de etiqueta para impressora térmica.": "热敏打印机用标签卷。",
    "Lacre plástico": "塑料封条",
    "Lacre numerado para controle interno.": "用于内部管控的编号封条。",
    "Embalagens": "包装用品",
    "Etiquetas": "标签",
    "Operacional": "运营用品",
    "un": "个",
    "rolo": "卷",
    "caixa": "箱",
    "pacote": "包",
    "metro": "米",
    "kg": "公斤"
  });


  Object.assign(zh, {
    "Normal • Min 100 / Máx 500": "正常 • 最低 100 / 最高 500",
    "Normal • Min 120 / Máx 600": "正常 • 最低 120 / 最高 600",
    "Normal • Min 30 / Máx 180": "正常 • 最低 30 / 最高 180",
    "Normal • Min 250 / Máx 1200": "正常 • 最低 250 / 最高 1200",
    "M 型安全信封": "M 型安全信封",
    "P 型安全信封": "P 型安全信封",
    "热敏标签": "热敏标签",
    "塑料封条": "塑料封条"
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
    ['Acesso ao Portal', '登录门户网站'],
    ['Entre com seu nome de usuário e senha. Se sua conta exigir confirmação, informe o código para concluir o login.', '请输入用户名和密码。如果您的账号需要确认，请输入代码完成登录。'],
    ['Ainda não tem cadastro?', '还没有账号？'],
    ['Solicitar acesso', '申请权限'],
    ['Nome do responsável', '负责人姓名'],
    ['Tipo de unidade', '单位类型'],
    ['Nome da base', '基地名称'],
    ['Nome da franquia', '加盟店名称'],
    ['Selecione a base', '请选择基地'],
    ['Selecione a franquia', '请选择加盟店'],
    ['Voltar ao login', '返回登录'],
    ['Solicitações pendentes', '待处理申请'],
    ['Minhas solicitações', '我的申请'],
    ['Painel administrativo', '管理面板'],
    ['Painel admin', '管理面板'],
    ['Gestão de estoque', '库存管理'],
    ['Gestão de Estoque', '库存管理'],
    ['Portal de Insumos', '耗材门户网站'],
    ['Solicitar insumos', '申请耗材'],
    ['Solicitar cadastro', '申请注册'],
    ['Nome de usuário', '用户名'],
    ['Unidade de medida', '计量单位'],
    ['Valor unitário', '单价'],
    ['Estoque disponível', '可用库存'],
    ['Limite para franquias', '加盟店限制'],
    ['Limite para bases', '基地限制'],
    ['Estoque mínimo', '最低库存'],
    ['Estoque máximo', '最高库存'],
    ['Novo produto', '新增产品'],
    ['Editar produto', '编辑产品'],
    ['Baixar PDF', '下载 PDF'],
    ['Exportar planilha', '导出电子表格'],
    ['Importar dados', '导入资料'],
    ['Produto ativo', '产品启用'],
    ['Confirmação de login', '登入确认'],
    ['Código de confirmação', '确认代码'],
    ['Confirmar login', '确认登入'],
    ['Usuários', '用户'],
    ['Produtos', '产品'],
    ['Solicitações', '申请单'],
    ['Pendentes', '待处理'],
    ['Atendidas', '已处理'],
    ['Responsável', '负责人'],
    ['Categoria', '类别'],
    ['Descrição', '描述'],
    ['Quantidade', '数量'],
    ['Observações', '备注'],
    ['Observação', '备注'],
    ['Status', '状态'],
    ['Unidade', '单位'],
    ['Produto', '产品'],
    ['Estoque', '库存'],
    ['Limite', '限制'],
    ['Senha', '密码'],
    ['Entrar', '登入'],
    ['Sair', '登出'],
    ['Voltar', '返回'],
    ['Salvar', '保存'],
    ['Cancelar', '取消'],
    ['Editar', '编辑'],
    ['Excluir', '删除'],
    ['Aprovar', '批准'],
    ['Recusar', '拒绝'],
    ['Atualizar', '更新'],
    ['Adicionar', '新增'],
    ['Limpar', '清除'],
    ['Data', '日期'],
    ['Itens', '项目'],
    ['Total', '总计'],
    ['Valor', '价格'],
    ['Ações', '操作'],
    ['Ação', '操作'],
    ['Tipo', '类型'],
    ['Base', '基地'],
    ['Franquia', '加盟店'],
    ['Admin', '管理员'],
    ['Ativo', '启用'],
    ['Inativo', '停用'],
    ['Envelope de segurança', '安全信封'],
    ['Envelope médio', '中型信封'],
    ['Envelope pequeno', '小型信封'],
    ['Etiqueta térmica', '热敏标签'],
    ['Lacre plástico', '塑料封条'],
    ['Envelope', '信封'],
    ['etiqueta', '标签'],
    ['impressora térmica', '热敏打印机'],
    ['envios padrão', '标准寄件'],
    ['envios leves', '轻量寄件'],
    ['controle interno', '内部管控'],
    ['Normal • Min', '正常 • 最低'],
    ['Normal • Mín', '正常 • 最低'],
    ['Baixo • Min', '偏低 • 最低'],
    ['Crítico • Min', '危急 • 最低'],
    ['Alto • Min', '偏高 • 最低'],
    [' / Máx', ' / 最高'],
    ['Min ', '最低 '],
    ['Mín ', '最低 '],
    ['Máx ', '最高 '],
    ['estoque mínimo/máximo', '最低/最高库存'],
    ['estoque mínimo', '最低库存'],
    ['estoque máximo', '最高库存'],
    ['estoque', '库存'],
    ['produtos', '产品'],
    ['produto', '产品'],
    ['insumos', '耗材'],
    ['insumo', '耗材'],
    ['valores', '价格'],
    ['limites', '限制'],
    ['parâmetros', '参数'],
    ['cadastrados', '已注册'],
    ['Cadastre', '注册'],
    ['mínimo', '最低'],
    ['máximo', '最高'],
  ].sort(function (a, b) { return b[0].length - a[0].length; });

  function currentLanguage() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored === 'zh-CN' || stored === 'zh-Hans' || stored === 'zh-Hant') ? 'zh-CN' : 'pt-BR';
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

  function translatePiece(value) {
    const raw = String(value == null ? '' : value).trim();
    if (!raw) return raw;
    return zh[raw] || translateFallback(raw);
  }

  function translateCore(core) {
    if (!core) return core;
    if (core === 'Entre com seu nome de usuário e senha. Se sua conta exigir confirmação, informe o código 用于 concluir o login.') return '请输入用户名和密码。如果您的账号需要确认，请输入代码完成登录。';
    if (zh[core]) return zh[core];
    let match;
    if ((match = core.match(/^(.+?)\s*•\s*Min\s+(.+?)\s*\/\s*Máx\s+(.+)$/))) return `${translatePiece(match[1])} • 最低 ${translatePiece(match[2])} / 最高 ${translatePiece(match[3])}`;
    if ((match = core.match(/^(.+?)\s*•\s*Mín\.?\s+(.+?)\s*\/\s*Máx\.?\s+(.+)$/))) return `${translatePiece(match[1])} • 最低 ${translatePiece(match[2])} / 最高 ${translatePiece(match[3])}`;
    if ((match = core.match(/^(.+?)\s*•\s*Mín\.?:\s*(.+?)\s*•\s*Máx\.?:\s*(.+)$/))) return `${translatePiece(match[1])} • 最低：${translatePiece(match[2])} • 最高：${translatePiece(match[3])}`;
    if ((match = core.match(/^(.+?)\s*•\s*Min\.?:\s*(.+?)\s*•\s*Máx\.?:\s*(.+)$/))) return `${translatePiece(match[1])} • 最低：${translatePiece(match[2])} • 最高：${translatePiece(match[3])}`;
    if ((match = core.match(/^Insira o código para confirmar o seu login:\s*(\d{6})$/))) return `请输入代码以确认您的登入：${match[1]}`;
    if ((match = core.match(/^Solicitação #(\d+) enviada para aprovação\. PDF disponível para download\.$/))) return `申请 #${match[1]} 已送交批准。PDF 可供下载。`;
    if ((match = core.match(/^Limite de insumos excedido para (.+)\. Limite permitido: (.+)\.$/))) return `${match[1]} 超出耗材限制。允许限制：${match[2]}。`;
    if ((match = core.match(/^(.+) adicionado à solicitação\.$/))) return `${match[1]} 已加入申请。`;
    if ((match = core.match(/^Estoque:\s*(.+)$/))) return `库存：${match[1]}`;
    if ((match = core.match(/^Limite:\s*(.+)$/))) return `限制：${match[1]}`;
    if ((match = core.match(/^Unidade:\s*(.+)$/))) return `单位：${match[1]}`;
    if ((match = core.match(/^Min\s+(.+)\s+\/\s+Máx\s+(.+)$/))) return `最低 ${match[1]} / 最高 ${match[2]}`;
    if ((match = core.match(/^Mín\.\s*(.+)$/))) return `最低 ${match[1]}`;
    if ((match = core.match(/^Máx\.\s*(.+)$/))) return `最高 ${match[1]}`;
    if ((match = core.match(/^Atual\s*(.+)$/))) return `当前 ${match[1]}`;
    if ((match = core.match(/^(\d+)\s+item$/))) return `${match[1]} 项`;
    if ((match = core.match(/^(\d+)\s+itens$/))) return `${match[1]} 项`;
    if ((match = core.match(/^(\d+)\s+un$/))) return `${match[1]} 个`;
    if ((match = core.match(/^(\d+)\s+rolo$/))) return `${match[1]} 卷`;
    if ((match = core.match(/^(\d+)\s+rolos$/))) return `${match[1]} 卷`;
    if ((match = core.match(/^(\d+)\s+caixa$/))) return `${match[1]} 箱`;
    if ((match = core.match(/^(\d+)\s+caixas$/))) return `${match[1]} 箱`;
    if ((match = core.match(/^(\d+)\s+pacote$/))) return `${match[1]} 包`;
    if ((match = core.match(/^(\d+)\s+pacotes$/))) return `${match[1]} 包`;
    if ((match = core.match(/^Admin\s*•\s*(.+)$/))) return `管理员 • ${match[1]}`;
    if ((match = core.match(/^Base\s*•\s*(.+)$/))) return `基地 • ${match[1]}`;
    if ((match = core.match(/^Franquia\s*•\s*(.+)$/))) return `加盟店 • ${match[1]}`;
    if ((match = core.match(/^Categoria\s*•\s*(.+)$/))) return `类别 • ${match[1]}`;
    if ((match = core.match(/^Produto\s*•\s*(.+)$/))) return `产品 • ${match[1]}`;
    if ((match = core.match(/^Estoque atual:\s*(.+)$/))) return `当前库存：${match[1]}`;
    if ((match = core.match(/^Mín\.?:\s*(.+)\s*•\s*Máx\.?:\s*(.+)$/))) return `最低：${match[1]} • 最高：${match[2]}`;
    if ((match = core.match(/^Importação concluída:\s*(.+)$/))) return `导入完成：${match[1]}`;
    if ((match = core.match(/^Estoque insuficiente para aprovar:\s*(.+)$/))) return `库存不足，无法批准：${match[1]}`;
    return translateFallback(core);
  }

  function t(value) {
    const text = String(value == null ? '' : value);
    return currentLanguage() === 'zh-CN' ? withWhitespace(text, translateCore(text.trim())) : text;
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
    const next = currentLanguage() === 'zh-CN' ? t(original) : original;
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
      const next = currentLanguage() === 'zh-CN' ? t(original) : original;
      if (el.getAttribute(attr) !== next) el.setAttribute(attr, next);
    });
    const tag = elementTag(el);
    const type = String(el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['button', 'submit', 'reset'].indexOf(type) !== -1 && el.hasAttribute('value')) {
      const key = STORAGE_ATTR_PREFIX + 'value';
      if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute('value') || '');
      const original = el.getAttribute(key) || '';
      const next = currentLanguage() === 'zh-CN' ? t(original) : original;
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
    document.title = currentLanguage() === 'zh-CN' ? t(originalTitle) : originalTitle;
  }

  function updateButton() {
    const lang = currentLanguage();
    const btn = document.getElementById('languageToggle');
    if (!btn) return;
    btn.setAttribute('aria-pressed', String(lang === 'zh-CN'));
    btn.classList.toggle('is-zh', lang === 'zh-CN');
    btn.title = lang === 'zh-CN' ? '切换为葡萄牙语' : 'Mudar para chinês simplificado';
  }

  function setRootLanguage() {
    root.setAttribute('lang', currentLanguage() === 'zh-CN' ? 'zh-CN' : 'pt-BR');
    root.setAttribute('data-language', currentLanguage());
  }

  function dispatchLanguageChange() {
    window.dispatchEvent(new CustomEvent('jt-language-change', { detail: { language: currentLanguage() } }));
  }

  function forceTranslateStockAndCards() {
    if (currentLanguage() !== 'zh-CN') return;
    const selectors = [
      '.stock-priority-item strong',
      '.stock-priority-item small',
      '.stock-product-card strong',
      '.stock-product-card small',
      '.stock-product-card span',
      '.product-card h3',
      '.product-card p',
      '.product-card .product-category',
      '.badge',
      '.stock-pill',
      '.stock-chart-tooltip *',
      '.stock-suggestion-item strong',
      '.stock-suggestion-item span',
      '.hero-card h2',
      '.hero-card p',
      '.hero-card .eyebrow',
      '.auth-card label',
      '.auth-card button',
      '.auth-card a',
      '.auth-card p',
      '.auth-card span',
      '.public-actions a',
      '.dev-credit strong',
      '.dev-credit small',
      '.language-toggle-text',
      '.theme-toggle-text'
    ];
    document.querySelectorAll(selectors.join(',')).forEach(function (el) {
      if (!el || shouldSkipElement(el)) return;
      Array.prototype.slice.call(el.childNodes || []).forEach(function (node) {
        if (node.nodeType !== Node.TEXT_NODE) return;
        const raw = String(node.nodeValue || '');
        if (!raw.trim()) return;
        if (!originalText.has(node)) originalText.set(node, raw);
        const source = originalText.get(node) || raw;
        const next = t(source);
        if (node.nodeValue !== next) node.nodeValue = next;
      });
      ATTRS.forEach(function (attr) {
        if (!el.hasAttribute || !el.hasAttribute(attr)) return;
        const key = STORAGE_ATTR_PREFIX + attr;
        if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute(attr) || '');
        const original = el.getAttribute(key) || '';
        const next = t(original);
        if (el.getAttribute(attr) !== next) el.setAttribute(attr, next);
      });
    });
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
        forceTranslateStockAndCards();
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
    localStorage.setItem(STORAGE_KEY, lang === 'zh-CN' ? 'zh-CN' : 'pt-BR');
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
        if (currentLanguage() === 'zh-CN') scheduleVisibleTranslation(document.body || document.documentElement, 80);
      }, { passive: true });
    });

    ['click', 'input', 'change', 'keyup'].forEach(function (eventName) {
      document.addEventListener(eventName, function () {
        if (currentLanguage() === 'zh-CN') scheduleVisibleTranslation(document.body || document.documentElement, 90);
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
        applyLanguage(currentLanguage() === 'zh-CN' ? 'pt-BR' : 'zh-CN');
      });
    }

    scheduleVisibleTranslation(document.body || document.documentElement, 20);
    window.setTimeout(function () { if (currentLanguage() === 'zh-CN') refresh(document.body || document.documentElement); }, 260);
  });
})();
