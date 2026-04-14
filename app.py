from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import hashlib
import secrets
import os
import random
import json
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_mude_para_algo_seguro_123456')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# ==================== CONFIGURAÇÕES DE UPLOAD ====================
UPLOAD_FOLDER = 'static/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists('comprovantes'):
    os.makedirs('comprovantes')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== ARQUIVO JSON (PERSISTENTE) ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DADOS_JSON = os.path.join(DATA_DIR, 'dados.json')

def carregar_dados():
    """Carrega os dados do arquivo JSON. Se não existir, cria com valores padrão."""
    if not os.path.exists(DADOS_JSON):
        print("⚠️ dados.json não encontrado. Criando novo arquivo com valores padrão...")
        dados_padrao = {
            "usuarios": [
                {
                    "id": 1,
                    "nome": "Administrador",
                    "email": "admin@admin.com",
                    "telefone": "",
                    "senha": hashlib.sha256("admin123".encode()).hexdigest(),
                    "codigo_convite": "ADMIN001",
                    "convidado_por": None,
                    "nivel": 0,
                    "nivel_nome": "Admin",
                    "saldo_principal": 0,
                    "saldo_comissao": 0,
                    "roleta_usada": 0,
                    "is_admin": 1,
                    "data_registro": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            ],
            "niveis": [
                {"id": 0, "nome": "Estagiário", "investimento": 0, "tarefas_por_dia": 2, "recompensa_por_anuncio": 0, "duracao_dias": 180},
                {"id": 1, "nome": "VIP 1", "investimento": 600, "tarefas_por_dia": 5, "recompensa_por_anuncio": 4, "duracao_dias": 180},
                {"id": 2, "nome": "VIP 2", "investimento": 3000, "tarefas_por_dia": 10, "recompensa_por_anuncio": 10, "duracao_dias": 180},
                {"id": 3, "nome": "VIP 3", "investimento": 12000, "tarefas_por_dia": 10, "recompensa_por_anuncio": 40, "duracao_dias": 180},
                {"id": 4, "nome": "VIP 4", "investimento": 30000, "tarefas_por_dia": 10, "recompensa_por_anuncio": 100, "duracao_dias": 180},
                {"id": 5, "nome": "VIP 5", "investimento": 90000, "tarefas_por_dia": 20, "recompensa_por_anuncio": 100, "duracao_dias": 180},
                {"id": 6, "nome": "VIP 6", "investimento": 300000, "tarefas_por_dia": 20, "recompensa_por_anuncio": 500, "duracao_dias": 180},
                {"id": 7, "nome": "VIP 7", "investimento": 900000, "tarefas_por_dia": 20, "recompensa_por_anuncio": 1500, "duracao_dias": 180}
            ],
            "pedidos_deposito": [],
            "pedidos_saque": [],
            "tarefas_multimidia": [
                {"id": 1, "titulo": "Anúncio Diário", "descricao": "Clique para assistir e ganhar", "tipo": "link", "url": "https://omg10.com/4/10861968", "recompensa": 10, "duracao_segundos": 30, "nivel_requerido": 1, "ativo": 1}
            ],
            "tarefas_assistidas": [],
            "produtos": [
                {"id": 1, "nome": "Smartphone XYZ", "descricao": "Smartphone de última geração", "preco": 5000, "imagem": "https://placehold.co/400x400/667eea/white?text=Smartphone", "categoria": "eletronicos", "ativo": 1},
                {"id": 2, "nome": "Fones Bluetooth", "descricao": "Fones de ouvido sem fio", "preco": 800, "imagem": "https://placehold.co/400x400/667eea/white?text=Fones", "categoria": "eletronicos", "ativo": 1},
                {"id": 3, "nome": "Camiseta Premium", "descricao": "Camiseta 100% algodão", "preco": 300, "imagem": "https://placehold.co/400x400/667eea/white?text=Camiseta", "categoria": "moda", "ativo": 1},
                {"id": 4, "nome": "Tênis Esportivo", "descricao": "Tênis confortável", "preco": 1200, "imagem": "https://placehold.co/400x400/667eea/white?text=Tênis", "categoria": "moda", "ativo": 1},
                {"id": 5, "nome": "Voucher Amazon", "descricao": "Voucher de 100 MZN", "preco": 100, "imagem": "https://placehold.co/400x400/667eea/white?text=Voucher", "categoria": "vouchers", "ativo": 1}
            ],
            "compras": [],
            "config": {
                "links_tarefas": [
                    "https://omg10.com/4/10861968",
                    "https://exemplo.com/anuncio2",
                    "https://outro-link.com/anuncio3"
                ],
                "modo_rotacao": "aleatorio",
                "whatsapp": "879267774",
                "grupo": "https://chat.whatsapp.com/DwPuPeBzKAfEXz6efHtIVP",
                "site_nome": "MOZ ADS",
                "taxa_saque": 15,
                "min_saque": 100
            }
        }
        salvar_dados(dados_padrao)
        return dados_padrao

    with open(DADOS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def atualizar_ganhos_usuario(usuario_id, valor):
    """Atualiza os campos ganhos_hoje, ganhos_semana, ganhos_mes, ganhos_total de um usuário"""
    dados = carregar_dados()
    for i, u in enumerate(dados['usuarios']):
        if u['id'] == usuario_id:
            dados['usuarios'][i]['ganhos_hoje'] += valor
            dados['usuarios'][i]['ganhos_semana'] += valor
            dados['usuarios'][i]['ganhos_mes'] += valor
            dados['usuarios'][i]['ganhos_total'] += valor
            break
    salvar_dados(dados)

def salvar_dados(dados):
    with open(DADOS_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def get_next_id(lista):
    if not lista:
        return 1
    return max(item['id'] for item in lista) + 1

def get_usuario_por_email(email):
    dados = carregar_dados()
    for usuario in dados['usuarios']:
        if usuario['email'] == email:
            return usuario
    return None

def get_usuario_por_id(usuario_id):
    dados = carregar_dados()
    for usuario in dados['usuarios']:
        if usuario['id'] == usuario_id:
            return usuario
    return None

def get_usuario_por_codigo(codigo):
    dados = carregar_dados()
    for usuario in dados['usuarios']:
        if usuario['codigo_convite'] == codigo:
            return usuario
    return None

def atualizar_usuario(usuario_id, campos):
    dados = carregar_dados()
    for i, usuario in enumerate(dados['usuarios']):
        if usuario['id'] == usuario_id:
            for key, value in campos.items():
                dados['usuarios'][i][key] = value
            salvar_dados(dados)
            return True
    return False

def get_nivel_por_id(nivel_id):
    dados = carregar_dados()
    for nivel in dados['niveis']:
        if nivel['id'] == nivel_id:
            return nivel
    return None

# ==================== FUNÇÕES AUXILIARES ====================

def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login primeiro', 'erro')
            return redirect(url_for('login'))
        # Verificar se o usuário ainda existe
        usuario = get_usuario_por_id(session['usuario_id'])
        if not usuario:
            session.clear()
            flash('Sessão expirada. Faça login novamente.', 'erro')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login primeiro', 'erro')
            return redirect(url_for('login'))
        usuario = get_usuario_por_id(session['usuario_id'])
        if not usuario or usuario['is_admin'] != 1:
            flash('Acesso negado. Área administrativa.', 'erro')
            return redirect(url_for('painel'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    codigo_ref = request.args.get('ref', '')
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form.get('telefone', '')
        senha = request.form['senha']
        codigo_convite = request.form.get('codigo_convite', '') or codigo_ref

        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        codigo_proprio = secrets.token_hex(4).upper()

        dados = carregar_dados()

        if get_usuario_por_email(email):
            flash('Email já cadastrado!', 'erro')
            return redirect(url_for('cadastro'))

        convidado_por = None
        nome_convidante = None
        if codigo_convite:
            convidante = get_usuario_por_codigo(codigo_convite)
            if convidante:
                convidado_por = codigo_convite
                nome_convidante = convidante['nome']

        novo_usuario = {
            "id": get_next_id(dados['usuarios']),
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "senha": senha_hash,
            "codigo_convite": codigo_proprio,
            "convidado_por": convidado_por,
            "nivel": 0,
            "nivel_nome": "Estagiário",
            "saldo_principal": 0,
            "saldo_comissao": 0,
            "is_admin": 0,
            "data_registro": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        dados['usuarios'].append(novo_usuario)
        salvar_dados(dados)

        if nome_convidante:
            flash(f'✅ Cadastro realizado! Você foi convidado por {nome_convidante}', 'sucesso')
        else:
            flash('Cadastro realizado com sucesso! Faça login.', 'sucesso')
        return redirect(url_for('login'))

    return render_template('cadastro.html', codigo_ref=codigo_ref)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        usuario = get_usuario_por_email(email)
        if usuario and usuario['senha'] == senha_hash:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['is_admin'] = usuario['is_admin']
            session.permanent = True
            flash(f'Bem-vindo, {usuario["nome"]}!', 'sucesso')
            if usuario['is_admin'] == 1:
                return redirect(url_for('admin_painel'))
            else:
                return redirect(url_for('painel'))
        else:
            flash('Email ou senha incorretos', 'erro')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado', 'sucesso')
    return redirect(url_for('login'))

@app.route('/painel')
@login_obrigatorio
def painel():
    usuario = get_usuario_por_id(session['usuario_id'])
    dados = carregar_dados()
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    semana_passada = hoje - timedelta(days=7)
    mes_passado = hoje - timedelta(days=30)

    # Calcular ganhos a partir do histórico de tarefas_assistidas
    ganhos_hoje = 0
    ganhos_ontem = 0
    ganhos_semana = 0
    ganhos_mes = 0
    ganhos_total = 0

    for t in dados['tarefas_assistidas']:
        if t['usuario_id'] == session['usuario_id']:
            data_t = datetime.strptime(t['data_assistida'], '%Y-%m-%d %H:%M:%S').date()
            if data_t == hoje:
                ganhos_hoje += t['ganho']
            if data_t == ontem:
                ganhos_ontem += t['ganho']
            if data_t >= semana_passada:
                ganhos_semana += t['ganho']
            if data_t >= mes_passado:
                ganhos_mes += t['ganho']
            ganhos_total += t['ganho']

    total_convidados = sum(1 for u in dados['usuarios'] if u['convidado_por'] == usuario['codigo_convite'])

    comissao_indicacao = 0
    for pedido in dados['pedidos_deposito']:
        if pedido['status'] == 'confirmado':
            for u in dados['usuarios']:
                if u['id'] == pedido['usuario_id'] and u['convidado_por'] == usuario['codigo_convite']:
                    comissao_indicacao += pedido['valor'] * 0.15

    # Adicionar também as comissões vindas de upgrades VIP (já estão no saldo, mas podem ser contabilizadas à parte se quiser)
    # Por simplicidade, usamos os valores calculados acima.

    return render_template('painel.html',
                           usuario=usuario,
                           total_convidados=total_convidados,
                           comissao_indicacao=comissao_indicacao,
                           ganhos_hoje=ganhos_hoje,
                           ganhos_ontem=ganhos_ontem,
                           ganhos_semana=ganhos_semana,
                           ganhos_mes=ganhos_mes,
                           ganhos_total=ganhos_total)

@app.route('/api/saldo')
@login_obrigatorio
def api_saldo():
    usuario = get_usuario_por_id(session['usuario_id'])
    return jsonify({
        'saldo_principal': usuario['saldo_principal'],
        'saldo_comissao': usuario['saldo_comissao'],
        'total': usuario['saldo_principal'] + usuario['saldo_comissao']
    })

@app.route('/tarefas')
@login_obrigatorio
def tarefas():
    try:
        usuario = get_usuario_por_id(session['usuario_id'])
        dados = carregar_dados()

        hoje = date.today()
        is_domingo = hoje.weekday() == 6

        nivel_usuario = get_nivel_por_id(usuario['nivel'])
        if nivel_usuario:
            limite_diario = nivel_usuario['tarefas_por_dia']
            recompensa_anuncio = nivel_usuario['recompensa_por_anuncio']
        else:
            limite_diario = 2
            recompensa_anuncio = 0

        if is_domingo:
            limite_diario = 0

        tarefas_feitas_hoje = sum(1 for t in dados['tarefas_assistidas']
                                  if t['usuario_id'] == session['usuario_id']
                                  and t['data_assistida'].startswith(hoje.strftime('%Y-%m-%d')))

        niveis = dados['niveis']
        progresso = {}
        for nivel in niveis:
            nivel_id = nivel['id']
            total_tarefas_nivel = sum(1 for t in dados['tarefas_multimidia'] if t['nivel_requerido'] == nivel_id and t['ativo'] == 1)
            feitas_nivel = sum(1 for t in dados['tarefas_assistidas']
                               if t['usuario_id'] == session['usuario_id']
                               and any(tm['id'] == t['tarefa_id'] and tm['nivel_requerido'] == nivel_id for tm in dados['tarefas_multimidia']))
            progresso[nivel_id] = {'total': total_tarefas_nivel, 'feitas': feitas_nivel}

        return render_template('tarefas.html',
                             usuario=usuario,
                             niveis=niveis,
                             progresso=progresso,
                             tarefas_feitas_hoje=tarefas_feitas_hoje,
                             limite_diario=limite_diario,
                             recompensa_anuncio=recompensa_anuncio,
                             is_domingo=is_domingo)
    except Exception as e:
        print(f"❌ ERRO em /tarefas: {str(e)}")
        flash(f'Erro ao carregar tarefas: {str(e)}', 'erro')
        return redirect(url_for('painel'))

@app.route('/clicar_tarefa', methods=['POST'])
@login_obrigatorio
def clicar_tarefa():
    try:
        dados = carregar_dados()
        usuario = get_usuario_por_id(session['usuario_id'])

        # Buscar links (com fallback)
        links = dados.get('config', {}).get('links_tarefas', ['https://omg10.com/4/10861968'])
        modo = dados.get('config', {}).get('modo_rotacao', 'aleatorio')
        if modo == 'aleatorio':
            url = random.choice(links)
        else:
            if 'link_index' not in session:
                session['link_index'] = 0
            url = links[session['link_index'] % len(links)]
            session['link_index'] += 1

        # Dados do nível
        nivel = get_nivel_por_id(usuario['nivel'])
        if nivel:
            limite = nivel['tarefas_por_dia']
            recompensa = nivel['recompensa_por_anuncio']
        else:
            limite = 2
            recompensa = 0

        # Domingo
        if date.today().weekday() == 6:
            return jsonify({'sucesso': False, 'erro': 'Domingo sem tarefas!'})

        # Contar tarefas de hoje
        hoje = date.today().strftime('%Y-%m-%d')
        feitas = sum(1 for t in dados['tarefas_assistidas']
                     if t['usuario_id'] == session['usuario_id'] and t['data_assistida'].startswith(hoje))

        if feitas >= limite:
            return jsonify({'sucesso': False, 'erro': f'Limite de {limite} tarefas hoje!'})

        # Registrar
        nova = {
            "id": get_next_id(dados['tarefas_assistidas']),
            "usuario_id": session['usuario_id'],
            "tarefa_id": 0,
            "data_assistida": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "ganho": recompensa
        }
        dados['tarefas_assistidas'].append(nova)

        # Adicionar saldo
        for i, u in enumerate(dados['usuarios']):
            if u['id'] == session['usuario_id']:
                dados['usuarios'][i]['saldo_comissao'] += recompensa
                break

        salvar_dados(dados)
        atualizar_ganhos_usuario(session['usuario_id'], recompensa)

        return jsonify({'sucesso': True, 'recompensa': recompensa, 'url': url})

    except Exception as e:
        print(f"❌ /clicar_tarefa: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)})
        
@app.route('/tabela_rendimentos')
@login_obrigatorio
def tabela_rendimentos():
    """Exibe a tabela de rendimentos por nível (PEPSI)"""
    dados = carregar_dados()
    niveis = dados.get('niveis', [])
    # Filtra apenas níveis com id >= 0 (todos)
    return render_template('tabela_rendimentos.html', niveis=niveis)

@app.route('/depositar', methods=['GET', 'POST'])
@login_obrigatorio
def depositar():
    if request.method == 'POST':
        valor = float(request.form['valor'])
        numero_pagamento = request.form['numero_pagamento']
        nome_titular = request.form['nome_titular']

        comprovante_path = None
        if 'comprovativo' in request.files:
            file = request.files['comprovativo']
            if file and file.filename:
                filename = secure_filename(f"{session['usuario_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join('comprovantes', filename)
                file.save(filepath)
                comprovante_path = filepath

        dados = carregar_dados()
        novo_pedido = {
            "id": get_next_id(dados['pedidos_deposito']),
            "usuario_id": session['usuario_id'],
            "valor": valor,
            "nivel_desejado": 0,
            "comprovante": comprovante_path,
            "metodo_pagamento": "mpesa",
            "numero_pagamento": numero_pagamento,
            "nome_titular": nome_titular,
            "status": "pendente",
            "data_pedido": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        dados['pedidos_deposito'].append(novo_pedido)
        salvar_dados(dados)

        flash(f'✅ Pedido de depósito de {valor} MZN enviado! Aguarde confirmação.', 'sucesso')
        return redirect(url_for('painel'))

    return render_template('depositos.html')

@app.route('/roleta')
@login_obrigatorio
def roleta():
    usuario = get_usuario_por_id(session['usuario_id'])
    ja_usou = usuario.get('roleta_usada', 0)
    return render_template('roleta.html', ja_usou=ja_usou)

@app.route('/spin_wheel', methods=['POST'])
@login_obrigatorio
def spin_wheel():
    dados = carregar_dados()
    usuario = get_usuario_por_id(session['usuario_id'])
    
    if usuario.get('roleta_usada', 0) == 1:
        return jsonify({'sucesso': False, 'erro': 'Você já usou sua roleta!'})
    
    # Sorteio dos prêmios (mesmas probabilidades)
    rand = random.random()
    if rand < 0.80:
        premio = 30
    elif rand < 0.95:
        premio = 50
    elif rand < 0.99:
        premio = 100
    else:
        premio = 150
    
    # Atualizar saldo e marcar como usada
    for i, u in enumerate(dados['usuarios']):
        if u['id'] == session['usuario_id']:
            dados['usuarios'][i]['saldo_comissao'] += premio
            dados['usuarios'][i]['roleta_usada'] = 1
            break
    
    salvar_dados(dados)
    atualizar_ganhos_usuario(session['usuario_id'], premio)
    
    return jsonify({'sucesso': True, 'premio': premio})

@app.route('/saque', methods=['GET', 'POST'])
@login_obrigatorio
def saque():
    usuario = get_usuario_por_id(session['usuario_id'])
    saldo_total = usuario['saldo_principal'] + usuario['saldo_comissao']
    pode_sacar = usuario['nivel'] >= 1

    if request.method == 'POST':
        if not pode_sacar:
            flash('Apenas usuários VIP podem solicitar saque!', 'erro')
            return redirect(url_for('saque'))

        valor = float(request.form['valor'])
        metodo = request.form.get('metodo', 'mpesa')
        numero_conta = request.form['numero_conta']
        nome_titular = request.form['nome_titular']
        email_paypal = request.form.get('email_paypal', '')

        if valor < 100:
            flash('Valor mínimo para saque é 100 MZN!', 'erro')
            return redirect(url_for('saque'))

        if valor > saldo_total:
            flash('Saldo insuficiente!', 'erro')
            return redirect(url_for('saque'))

        taxa = max(valor * 0.15, 10)   # 15% taxa, mínimo 10 MZN
        valor_liquido = valor - taxa

        dados = carregar_dados()
        novo_saque = {
            "id": get_next_id(dados['pedidos_saque']),
            "usuario_id": session['usuario_id'],
            "valor": valor,
            "valor_liquido": valor_liquido,
            "taxa": taxa,
            "metodo": metodo,
            "numero_conta": numero_conta,
            "nome_titular": nome_titular,
            "email_paypal": email_paypal,
            "status": "pendente",
            "data_pedido": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        dados['pedidos_saque'].append(novo_saque)
        salvar_dados(dados)

        flash(f'✅ Saque de {valor} MZN solicitado! Taxa: {taxa:.2f} MZN', 'sucesso')
        return redirect(url_for('painel'))

    return render_template('saque.html', saldo_total=saldo_total, saldo_principal=usuario['saldo_principal'],
                         saldo_comissao=usuario['saldo_comissao'], pode_sacar=pode_sacar)

@app.route('/convidar')
@login_obrigatorio
def convidar():
    usuario = get_usuario_por_id(session['usuario_id'])
    dados = carregar_dados()
    convidados = [u for u in dados['usuarios'] if u['convidado_por'] == usuario['codigo_convite']]
    return render_template('convidar.html', usuario=usuario, convidados=convidados, total_convidados=len(convidados))

@app.route('/vip', methods=['GET', 'POST'])
@login_obrigatorio
def vip():
    usuario = get_usuario_por_id(session['usuario_id'])
    dados = carregar_dados()
    niveis = [n for n in dados['niveis'] if n['id'] > 0]

    if request.method == 'POST':
        novo_nivel_id = int(request.form['nivel_id'])
        novo_nivel = get_nivel_por_id(novo_nivel_id)

        if novo_nivel:
            valor_novo_vip = novo_nivel['investimento']
            saldo_total = usuario['saldo_principal'] + usuario['saldo_comissao']
            nivel_atual = usuario['nivel']

            if novo_nivel_id > nivel_atual:
                if saldo_total >= valor_novo_vip:
                    # Cobrar o valor
                    novo_saldo_principal = usuario['saldo_principal'] - min(usuario['saldo_principal'], valor_novo_vip)
                    restante = valor_novo_vip - min(usuario['saldo_principal'], valor_novo_vip)
                    novo_saldo_comissao = usuario['saldo_comissao'] - restante


                    # Comissão de 15% para quem convidou
                    if usuario['convidado_por']:
                       comissao = valor_novo_vip * 0.15
                       convidante = get_usuario_por_codigo(usuario['convidado_por'])
                       if convidante:
                           for i, u in enumerate(dados['usuarios']):
                               if u['id'] == convidante['id']:
                                   dados['usuarios'][i]['saldo_comissao'] += comissao
                                   atualizar_ganhos_usuario(convidante['id'], comissao)
                                   break  


                    # Atualizar usuário
                    for i, u in enumerate(dados['usuarios']):
                        if u['id'] == session['usuario_id']:
                            dados['usuarios'][i]['saldo_principal'] = novo_saldo_principal
                            dados['usuarios'][i]['saldo_comissao'] = novo_saldo_comissao
                            dados['usuarios'][i]['nivel'] = novo_nivel_id
                            dados['usuarios'][i]['nivel_nome'] = novo_nivel['nome']
                            break

                    salvar_dados(dados)
                    flash(f'✅ Parabéns! Você fez upgrade para {novo_nivel["nome"]}!', 'sucesso')
                else:
                    falta = valor_novo_vip - saldo_total
                    flash(f'❌ Saldo insuficiente! Você precisa de {falta:.2f} MZN para fazer upgrade.', 'erro')
            else:
                flash(f'❌ Você já possui um nível igual ou superior!', 'erro')

        return redirect(url_for('vip'))

    return render_template('vip.html', usuario=usuario, niveis=niveis)

# ==================== SHOP ====================

@app.route('/shop')
@login_obrigatorio
def shop():
    try:
        usuario = get_usuario_por_id(session['usuario_id'])
        dados = carregar_dados()

        produtos = [p for p in dados['produtos'] if p['ativo'] == 1]

        compras = []
        for c in dados['compras']:
            if c['usuario_id'] == session['usuario_id']:
                for p in dados['produtos']:
                    if p['id'] == c['produto_id']:
                        compras.append({
                            "id": c['id'],
                            "produto_nome": p['nome'],
                            "imagem": p['imagem'],
                            "valor": c['valor'],
                            "data_compra": c['data_compra']
                        })
                        break

        return render_template('shop.html', usuario=usuario, produtos=produtos, compras=compras)

    except Exception as e:
        print(f"❌ Erro em /shop: {str(e)}")
        flash('Erro ao carregar a loja', 'erro')
        return redirect(url_for('painel'))

@app.route('/comprar_produto', methods=['POST'])
@login_obrigatorio
def comprar_produto():
    try:
        data = json.loads(request.data)
        produto_id = data.get('produto_id')
        preco = data.get('preco')

        dados = carregar_dados()
        usuario = get_usuario_por_id(session['usuario_id'])

        produto = None
        for p in dados['produtos']:
            if p['id'] == produto_id and p['ativo'] == 1:
                produto = p
                break

        if not produto:
            return jsonify({'sucesso': False, 'erro': 'Produto não encontrado!'})

        saldo_total = usuario['saldo_principal'] + usuario['saldo_comissao']
        if saldo_total < preco:
            return jsonify({'sucesso': False, 'erro': 'Saldo insuficiente!'})

        # Debita do saldo
        novo_saldo_principal = usuario['saldo_principal'] - min(usuario['saldo_principal'], preco)
        restante = preco - min(usuario['saldo_principal'], preco)
        novo_saldo_comissao = usuario['saldo_comissao'] - restante

        for i, u in enumerate(dados['usuarios']):
            if u['id'] == session['usuario_id']:
                dados['usuarios'][i]['saldo_principal'] = novo_saldo_principal
                dados['usuarios'][i]['saldo_comissao'] = novo_saldo_comissao
                break

        nova_compra = {
            "id": get_next_id(dados['compras']),
            "usuario_id": session['usuario_id'],
            "produto_id": produto_id,
            "valor": preco,
            "data_compra": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        dados['compras'].append(nova_compra)
        salvar_dados(dados)

        return jsonify({'sucesso': True})

    except Exception as e:
        print(f"❌ Erro em /comprar_produto: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)})

# ==================== ADMIN ====================

@app.route('/admin_painel')
@admin_obrigatorio
def admin_painel():
    dados = carregar_dados()

    total_usuarios = len(dados['usuarios'])
    pendentes_deposito = sum(1 for p in dados['pedidos_deposito'] if p['status'] == 'pendente')
    pendentes_saque = sum(1 for p in dados['pedidos_saque'] if p['status'] == 'pendente')
    total_saldo_sistema = sum(u['saldo_principal'] + u['saldo_comissao'] for u in dados['usuarios'])

    ultimos_pedidos = sorted(dados['pedidos_deposito'], key=lambda x: x['data_pedido'], reverse=True)[:10]
    for pedido in ultimos_pedidos:
        for u in dados['usuarios']:
            if u['id'] == pedido['usuario_id']:
                pedido['nome'] = u['nome']
                break

    stats = {
        'total_usuarios': total_usuarios,
        'pendentes_deposito': pendentes_deposito,
        'pendentes_saque': pendentes_saque,
        'total_saldo_sistema': total_saldo_sistema
    }

    return render_template('admin_painel.html', stats=stats, ultimos_pedidos=ultimos_pedidos)

@app.route('/admin_depositos')
@admin_obrigatorio
def admin_depositos():
    dados = carregar_dados()

    pedidos = []
    historico = []

    for p in dados['pedidos_deposito']:
        for u in dados['usuarios']:
            if u['id'] == p['usuario_id']:
                p['nome'] = u['nome']
                p['email'] = u['email']
                p['telefone'] = u['telefone']
                break

        if p['status'] == 'pendente':
            pedidos.append(p)
        else:
            historico.append(p)

    return render_template('admin_depositos.html', pedidos=pedidos, historico=historico)

@app.route('/admin_saques')
@admin_obrigatorio
def admin_saques():
    dados = carregar_dados()

    pendentes = []
    historico = []

    for p in dados['pedidos_saque']:
        for u in dados['usuarios']:
            if u['id'] == p['usuario_id']:
                p['usuario_nome'] = u['nome']
                p['usuario_email'] = u['email']
                break

        if p['status'] == 'pendente':
            pendentes.append(p)
        else:
            historico.append(p)

    return render_template('admin_saques.html', pendentes=pendentes, historico=historico)

@app.route('/admin_usuarios')
@admin_obrigatorio
def admin_usuarios():
    dados = carregar_dados()
    usuarios = dados['usuarios']
    niveis = dados['niveis']

    return render_template('admin_usuarios.html', usuarios=usuarios, niveis=niveis)

@app.route('/admin_tarefas')
@admin_obrigatorio
def admin_tarefas():
    dados = carregar_dados()
    tarefas = dados['tarefas_multimidia']

    return render_template('admin_tarefas.html', tarefas=tarefas)

@app.route('/admin_configuracoes', methods=['GET', 'POST'])
@admin_obrigatorio
def admin_configuracoes():
    dados = carregar_dados()
    niveis = dados['niveis']

    if request.method == 'POST':
        # Salvar configurações gerais
        whatsapp = request.form.get('whatsapp', '')
        grupo = request.form.get('grupo', '')
        site_nome = request.form.get('site_nome', 'MOZ ADS')
        taxa_saque = float(request.form.get('taxa_saque', 15))
        min_saque = float(request.form.get('min_saque', 100))

        dados['config'] = {
            'whatsapp': whatsapp,
            'grupo': grupo,
            'site_nome': site_nome,
            'taxa_saque': taxa_saque,
            'min_saque': min_saque,
            'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Atualizar níveis se vierem do formulário
        for nivel in niveis:
            nivel_id = nivel['id']
            if nivel_id > 0:
                investimento_key = f'investimento_{nivel_id}'
                tarefas_key = f'tarefas_{nivel_id}'
                recompensa_key = f'recompensa_{nivel_id}'

                if investimento_key in request.form:
                    novo_investimento = float(request.form[investimento_key])
                    for n in dados['niveis']:
                        if n['id'] == nivel_id:
                            n['investimento'] = novo_investimento
                            break

                if tarefas_key in request.form:
                    novas_tarefas = int(request.form[tarefas_key])
                    for n in dados['niveis']:
                        if n['id'] == nivel_id:
                            n['tarefas_por_dia'] = novas_tarefas
                            break

                if recompensa_key in request.form:
                    nova_recompensa = float(request.form[recompensa_key])
                    for n in dados['niveis']:
                        if n['id'] == nivel_id:
                            n['recompensa_por_anuncio'] = nova_recompensa
                            break

        salvar_dados(dados)
        flash('✅ Configurações salvas com sucesso!', 'sucesso')
        return redirect(url_for('admin_configuracoes'))

    config = dados.get('config', {
        'whatsapp': '879267774',
        'grupo': 'https://chat.whatsapp.com/DwPuPeBzKAfEXz6efHtIVP',
        'site_nome': 'MOZ ADS',
        'taxa_saque': 15,
        'min_saque': 100
    })

    return render_template('admin_configuracoes.html', niveis=niveis, config=config)

@app.route('/admin_editar_shop')
@admin_obrigatorio
def admin_editar_shop():
    dados = carregar_dados()
    produtos = dados['produtos']

    return render_template('admin_editar_shop.html', produtos=produtos)

@app.route('/admin_relatorios')
@admin_obrigatorio
def admin_relatorios():
    dados = carregar_dados()

    depositos = []
    for p in dados['pedidos_deposito']:
        for u in dados['usuarios']:
            if u['id'] == p['usuario_id']:
                p['usuario_nome'] = u['nome']
                p['usuario_email'] = u['email']
                break
        depositos.append(p)

    saques = []
    for p in dados['pedidos_saque']:
        for u in dados['usuarios']:
            if u['id'] == p['usuario_id']:
                p['usuario_nome'] = u['nome']
                p['usuario_email'] = u['email']
                break
        saques.append(p)

    compras = []
    for c in dados['compras']:
        for u in dados['usuarios']:
            if u['id'] == c['usuario_id']:
                c['usuario_nome'] = u['nome']
                c['usuario_email'] = u['email']
                break
        for p in dados['produtos']:
            if p['id'] == c['produto_id']:
                c['produto_nome'] = p['nome']
                break
        compras.append(c)

    stats = {
        'total_usuarios': len(dados['usuarios']),
        'total_depositos': sum(1 for p in dados['pedidos_deposito'] if p['status'] == 'confirmado'),
        'total_valor_depositos': sum(p['valor'] for p in dados['pedidos_deposito'] if p['status'] == 'confirmado'),
        'total_saques': sum(1 for p in dados['pedidos_saque'] if p['status'] == 'pago'),
        'total_valor_saques': sum(p['valor'] for p in dados['pedidos_saque'] if p['status'] == 'pago'),
        'total_compras': len(dados['compras']),
        'total_valor_compras': sum(c['valor'] for c in dados['compras']),
        'saldo_total_sistema': sum(u['saldo_principal'] + u['saldo_comissao'] for u in dados['usuarios'])
    }

    return render_template('admin_relatorios.html', depositos=depositos, saques=saques, compras=compras, stats=stats)

@app.route('/admin_links')
@admin_obrigatorio
def admin_links():
    dados = carregar_dados()
    links = dados.get('config', {}).get('links_tarefas', [])
    return render_template('admin_links.html', links=links)

@app.route('/adicionar_link', methods=['POST'])
@admin_obrigatorio
def adicionar_link():
    novo_link = request.form['link']
    dados = carregar_dados()
    if 'links_tarefas' not in dados.get('config', {}):
        dados['config']['links_tarefas'] = []
    dados['config']['links_tarefas'].append(novo_link)
    salvar_dados(dados)
    flash('Link adicionado!', 'sucesso')
    return redirect(url_for('admin_links'))

@app.route('/remover_link/<int:index>')
@admin_obrigatorio
def remover_link(index):
    dados = carregar_dados()
    if 'links_tarefas' in dados.get('config', {}):
        if 0 <= index < len(dados['config']['links_tarefas']):
            dados['config']['links_tarefas'].pop(index)
            salvar_dados(dados)
            flash('Link removido!', 'sucesso')
    return redirect(url_for('admin_links'))

@app.route('/confirmar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def confirmar_deposito(pedido_id):
    dados = carregar_dados()
    pedido = None
    for p in dados['pedidos_deposito']:
        if p['id'] == pedido_id:
            pedido = p
            break

    if request.method == 'POST':
        for i, p in enumerate(dados['pedidos_deposito']):
            if p['id'] == pedido_id:
                dados['pedidos_deposito'][i]['status'] = 'confirmado'
                dados['pedidos_deposito'][i]['data_confirmacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break

        for i, u in enumerate(dados['usuarios']):
            if u['id'] == pedido['usuario_id']:
                dados['usuarios'][i]['saldo_principal'] += pedido['valor']
                break

        salvar_dados(dados)
        flash(f'✅ Depósito de {pedido["valor"]} MZN confirmado!', 'sucesso')
        return redirect(url_for('admin_depositos'))

    for u in dados['usuarios']:
        if u['id'] == pedido['usuario_id']:
            pedido['nome'] = u['nome']
            pedido['email'] = u['email']
            pedido['telefone'] = u['telefone']
            break

    return render_template('confirmar_deposito.html', pedido=pedido)

@app.route('/rejeitar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def rejeitar_deposito(pedido_id):
    dados = carregar_dados()
    pedido = None
    for p in dados['pedidos_deposito']:
        if p['id'] == pedido_id:
            pedido = p
            break

    if request.method == 'POST':
        for i, p in enumerate(dados['pedidos_deposito']):
            if p['id'] == pedido_id:
                dados['pedidos_deposito'][i]['status'] = 'rejeitado'
                break
        salvar_dados(dados)
        flash(f'❌ Depósito de {pedido["valor"]} MZN rejeitado!', 'erro')
        return redirect(url_for('admin_depositos'))

    return render_template('rejeitar_deposito.html', pedido=pedido)

@app.route('/confirmar_saque/<int:saque_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def confirmar_saque(saque_id):
    dados = carregar_dados()
    saque = None
    for p in dados['pedidos_saque']:
        if p['id'] == saque_id:
            saque = p
            break

    if request.method == 'POST':
        for i, p in enumerate(dados['pedidos_saque']):
            if p['id'] == saque_id:
                dados['pedidos_saque'][i]['status'] = 'pago'
                dados['pedidos_saque'][i]['data_processamento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break

        for i, u in enumerate(dados['usuarios']):
            if u['id'] == saque['usuario_id']:
                dados['usuarios'][i]['saldo_comissao'] = max(0, u['saldo_comissao'] - saque['valor'])
                break

        salvar_dados(dados)
        flash(f'✅ Saque de {saque["valor"]} MZN confirmado!', 'sucesso')
        return redirect(url_for('admin_saques'))

    for u in dados['usuarios']:
        if u['id'] == saque['usuario_id']:
            saque['usuario_nome'] = u['nome']
            saque['usuario_email'] = u['email']
            break

    return render_template('confirmar_saque.html', saque=saque)

@app.route('/rejeitar_saque/<int:saque_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def rejeitar_saque(saque_id):
    dados = carregar_dados()
    saque = None
    for p in dados['pedidos_saque']:
        if p['id'] == saque_id:
            saque = p
            break

    if request.method == 'POST':
        for i, p in enumerate(dados['pedidos_saque']):
            if p['id'] == saque_id:
                dados['pedidos_saque'][i]['status'] = 'rejeitado'
                break
        salvar_dados(dados)
        flash(f'❌ Saque de {saque["valor"]} MZN rejeitado!', 'erro')
        return redirect(url_for('admin_saques'))

    return render_template('rejeitar_saque.html', saque=saque)

@app.route('/ajustar_saldo/<int:usuario_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def ajustar_saldo(usuario_id):
    dados = carregar_dados()
    usuario = get_usuario_por_id(usuario_id)
    niveis = dados['niveis']

    if request.method == 'POST':
        tipo_saldo = request.form['tipo_saldo']
        valor = float(request.form['valor'])
        operacao = request.form['operacao']
        nivel_id = int(request.form.get('nivel_id', 0))

        for i, u in enumerate(dados['usuarios']):
            if u['id'] == usuario_id:
                if operacao == 'adicionar':
                    dados['usuarios'][i][tipo_saldo] += valor
                else:
                    dados['usuarios'][i][tipo_saldo] = max(0, u[tipo_saldo] - valor)

                if nivel_id > 0:
                    nivel = get_nivel_por_id(nivel_id)
                    if nivel:
                        dados['usuarios'][i]['nivel'] = nivel_id
                        dados['usuarios'][i]['nivel_nome'] = nivel['nome']
                break

        salvar_dados(dados)
        flash('✅ Saldo ajustado!', 'sucesso')
        return redirect(url_for('admin_usuarios'))

    return render_template('ajustar_saldo.html', usuario=usuario, niveis=niveis)

@app.route('/deposito_manual', methods=['POST'])
@admin_obrigatorio
def deposito_manual():
    usuario_id = int(request.form['usuario_id'])
    tipo_saldo = request.form['tipo_saldo']
    valor = float(request.form['valor'])
    nivel_id = int(request.form.get('nivel_id', 0))

    dados = carregar_dados()

    for i, u in enumerate(dados['usuarios']):
        if u['id'] == usuario_id:
            dados['usuarios'][i][tipo_saldo] += valor
            if nivel_id > 0:
                nivel = get_nivel_por_id(nivel_id)
                if nivel:
                    dados['usuarios'][i]['nivel'] = nivel_id
                    dados['usuarios'][i]['nivel_nome'] = nivel['nome']
            break

    salvar_dados(dados)
    flash(f'✅ Adicionado {valor} MZN ao usuário!', 'sucesso')
    return redirect(url_for('admin_usuarios'))

@app.route('/adicionar_produto', methods=['POST'])
@admin_obrigatorio
def adicionar_produto():
    nome = request.form['nome']
    descricao = request.form.get('descricao', '')
    preco = float(request.form['preco'])
    categoria = request.form.get('categoria', 'outros')

    imagem_path = None
    if 'imagem_arquivo' in request.files:
        file = request.files['imagem_arquivo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            imagem_path = f'/{UPLOAD_FOLDER}/{filename}'

    if not imagem_path:
        imagem_path = request.form.get('imagem_url', 'https://placehold.co/400x400/667eea/white?text=Produto')

    dados = carregar_dados()
    novo_produto = {
        "id": get_next_id(dados['produtos']),
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "imagem": imagem_path,
        "categoria": categoria,
        "ativo": 1
    }
    dados['produtos'].append(novo_produto)
    salvar_dados(dados)

    flash('✅ Produto adicionado com sucesso!', 'sucesso')
    return redirect(url_for('admin_editar_shop'))

@app.route('/editar_produto/<int:produto_id>', methods=['POST'])
@admin_obrigatorio
def editar_produto(produto_id):
    nome = request.form['nome']
    descricao = request.form.get('descricao', '')
    preco = float(request.form['preco'])
    categoria = request.form.get('categoria', 'outros')

    imagem_path = None
    if 'imagem_arquivo' in request.files:
        file = request.files['imagem_arquivo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            imagem_path = f'/{UPLOAD_FOLDER}/{filename}'

    dados = carregar_dados()

    for i, p in enumerate(dados['produtos']):
        if p['id'] == produto_id:
            dados['produtos'][i]['nome'] = nome
            dados['produtos'][i]['descricao'] = descricao
            dados['produtos'][i]['preco'] = preco
            dados['produtos'][i]['categoria'] = categoria
            if imagem_path:
                dados['produtos'][i]['imagem'] = imagem_path
            break

    salvar_dados(dados)
    flash('✅ Produto atualizado com sucesso!', 'sucesso')
    return redirect(url_for('admin_editar_shop'))

@app.route('/remover_produto/<int:produto_id>')
@admin_obrigatorio
def remover_produto(produto_id):
    dados = carregar_dados()
    dados['produtos'] = [p for p in dados['produtos'] if p['id'] != produto_id]
    salvar_dados(dados)

    flash('❌ Produto removido!', 'erro')
    return redirect(url_for('admin_editar_shop'))

@app.route('/alternar_produto/<int:produto_id>')
@admin_obrigatorio
def alternar_produto(produto_id):
    dados = carregar_dados()
    for i, p in enumerate(dados['produtos']):
        if p['id'] == produto_id:
            dados['produtos'][i]['ativo'] = 0 if p['ativo'] == 1 else 1
            break
    salvar_dados(dados)

    flash('✅ Status do produto alterado!', 'sucesso')
    return redirect(url_for('admin_editar_shop'))

@app.route('/adicionar_tarefa_multimidia', methods=['POST'])
@admin_obrigatorio
def adicionar_tarefa_multimidia():
    titulo = request.form['titulo']
    descricao = request.form.get('descricao', '')
    tipo = request.form['tipo']
    url = request.form['url']
    recompensa = float(request.form['recompensa'])
    duracao = int(request.form.get('duracao', 30))
    nivel_requerido = int(request.form.get('nivel_requerido', 1))

    dados = carregar_dados()
    nova_tarefa = {
        "id": get_next_id(dados['tarefas_multimidia']),
        "titulo": titulo,
        "descricao": descricao,
        "tipo": tipo,
        "url": url,
        "recompensa": recompensa,
        "duracao_segundos": duracao,
        "nivel_requerido": nivel_requerido,
        "ativo": 1
    }
    dados['tarefas_multimidia'].append(nova_tarefa)
    salvar_dados(dados)

    flash('✅ Tarefa adicionada!', 'sucesso')
    return redirect(url_for('admin_tarefas'))

@app.route('/remover_tarefa_multimidia/<int:tarefa_id>')
@admin_obrigatorio
def remover_tarefa_multimidia(tarefa_id):
    dados = carregar_dados()
    dados['tarefas_multimidia'] = [t for t in dados['tarefas_multimidia'] if t['id'] != tarefa_id]
    salvar_dados(dados)

    flash('❌ Tarefa removida!', 'erro')
    return redirect(url_for('admin_tarefas'))

@app.route('/configurar_link_rapido', methods=['POST'])
@admin_obrigatorio
def configurar_link_rapido():
    nivel_id = int(request.form['nivel_id'])
    url = request.form['url']
    recompensa = float(request.form['recompensa'])

    dados = carregar_dados()

    existe = False
    for i, t in enumerate(dados['tarefas_multimidia']):
        if t['nivel_requerido'] == nivel_id and t['tipo'] == 'link':
            dados['tarefas_multimidia'][i]['url'] = url
            dados['tarefas_multimidia'][i]['recompensa'] = recompensa
            existe = True
            break

    if not existe:
        nova_tarefa = {
            "id": get_next_id(dados['tarefas_multimidia']),
            "titulo": f'Anúncio VIP {nivel_id}',
            "descricao": f'Assista ao anúncio e ganhe {recompensa} MZN',
            "tipo": 'link',
            "url": url,
            "recompensa": recompensa,
            "duracao_segundos": 30,
            "nivel_requerido": nivel_id,
            "ativo": 1
        }
        dados['tarefas_multimidia'].append(nova_tarefa)

    salvar_dados(dados)
    flash(f'✅ Link do VIP {nivel_id} configurado!', 'sucesso')
    return redirect(url_for('admin_tarefas'))

# ==================== INICIALIZAÇÃO ====================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))

    print("=" * 60)
    print("🚀 SERVIDOR INICIADO COM SUCESSO!")
    print("=" * 60)
    print("📍 Acesse: http://localhost:5000")
    print("👑 Admin: admin@admin.com / senha: admin123")
    print("=" * 60)

    app.run(debug=False, host='0.0.0.0', port=PORT)
