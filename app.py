from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import secrets
import os
import json
import subprocess
import sys
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_mude_para_algo_seguro_123456')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Criar pasta para comprovantes
if not os.path.exists('comprovantes'):
    os.makedirs('comprovantes')

# ==================== FUNÇÃO PARA CRIAR BANCO DE DADOS ====================
def criar_banco_se_necessario():
    """Cria o banco de dados se não existir"""
    if not os.path.exists('database.db'):
        print("=" * 50)
        print("📌 Banco de dados não encontrado!")
        print("🔄 Criando banco de dados...")
        print("=" * 50)
        
        try:
            # Executar o init_db.py
            result = subprocess.run([sys.executable, 'init_db.py'], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Banco de dados criado com sucesso!")
                print(result.stdout)
            else:
                print("❌ Erro ao criar banco de dados:")
                print(result.stderr)
                
                # Tentar criar diretamente com SQL
                criar_banco_direto()
                
        except Exception as e:
            print(f"❌ Erro ao executar init_db.py: {str(e)}")
            criar_banco_direto()
    else:
        print("✅ Banco de dados já existe!")
        # Verificar se as tabelas estão corretas
        verificar_tabelas()

def criar_banco_direto():
    """Cria o banco de dados diretamente se o init_db.py falhar"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Criar tabela de usuários
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT,
            senha TEXT NOT NULL,
            codigo_convite TEXT UNIQUE NOT NULL,
            convidado_por TEXT,
            nivel INTEGER DEFAULT 0,
            nivel_nome TEXT DEFAULT 'Estagiário',
            validade_inicio TEXT,
            validade_fim TEXT,
            saldo_principal REAL DEFAULT 0,
            saldo_comissao REAL DEFAULT 0,
            ganhos_hoje REAL DEFAULT 0,
            ganhos_ontem REAL DEFAULT 0,
            ganhos_semana REAL DEFAULT 0,
            ganhos_mes REAL DEFAULT 0,
            ganhos_total REAL DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Criar tabela de níveis
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS niveis (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            investimento REAL,
            tarefas_por_dia INTEGER DEFAULT 0,
            recompensa_por_anuncio REAL DEFAULT 0,
            duracao_dias INTEGER DEFAULT 180
        )
        ''')
        
        # Inserir níveis
        niveis = [
            (0, 'Estagiário', 0, 2, 0, 180),
            (1, 'VIP 1', 600, 5, 4, 180),
            (2, 'VIP 2', 3000, 10, 10, 180),
            (3, 'VIP 3', 12000, 10, 40, 180),
            (4, 'VIP 4', 30000, 10, 100, 180),
            (5, 'VIP 5', 90000, 20, 100, 180),
            (6, 'VIP 6', 300000, 20, 500, 180),
            (7, 'VIP 7', 900000, 20, 1500, 180),
        ]
        cursor.executemany('INSERT OR IGNORE INTO niveis (id, nome, investimento, tarefas_por_dia, recompensa_por_anuncio, duracao_dias) VALUES (?, ?, ?, ?, ?, ?)', niveis)
        
        # Criar tabela de pedidos de depósito
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos_deposito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            valor REAL,
            nivel_desejado INTEGER,
            comprovante TEXT,
            metodo_pagamento TEXT,
            numero_pagamento TEXT,
            nome_titular TEXT,
            status TEXT DEFAULT 'pendente',
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_confirmacao TIMESTAMP
        )
        ''')
        
        # Criar tabela de pedidos de saque
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos_saque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            valor REAL,
            valor_liquido REAL,
            taxa REAL,
            metodo TEXT,
            numero_conta TEXT,
            nome_titular TEXT,
            email_paypal TEXT,
            status TEXT DEFAULT 'pendente',
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_processamento TIMESTAMP,
            observacao TEXT
        )
        ''')
        
        # Criar tabela de tarefas multimídia
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas_multimidia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            tipo TEXT DEFAULT 'video',
            url TEXT NOT NULL,
            thumbnail TEXT,
            recompensa REAL NOT NULL,
            duracao_segundos INTEGER DEFAULT 30,
            nivel_requerido INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Criar tabela de tarefas assistidas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas_assistidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tarefa_id INTEGER,
            data_assistida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ganho REAL
        )
        ''')
        
        # Criar tabela de ganhos diários
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ganhos_diarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            data DATE,
            valor REAL,
            pago INTEGER DEFAULT 0
        )
        ''')
        
        # Criar admin padrão
        senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
        codigo_admin = "ADMIN001"
        
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@admin.com',))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, codigo_convite, is_admin, nivel, nivel_nome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("Administrador", "admin@admin.com", senha_hash, codigo_admin, 1, 0, "Admin"))
        
        # Inserir tarefa padrão (link de anúncio)
        cursor.execute('SELECT id FROM tarefas_multimidia LIMIT 1')
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, duracao_segundos, nivel_requerido)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("Anúncio Diário", "Clique para assistir e ganhar", "link", "https://example.com/anuncio", 10, 30, 1))
        
        conn.commit()
        conn.close()
        
        print("✅ Banco de dados criado diretamente com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar banco diretamente: {str(e)}")

def verificar_tabelas():
    """Verifica se as tabelas necessárias existem"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        tabelas = ['usuarios', 'niveis', 'pedidos_deposito', 'pedidos_saque', 'tarefas_multimidia', 'tarefas_assistidas']
        for tabela in tabelas:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
            if not cursor.fetchone():
                print(f"⚠️ Tabela {tabela} não encontrada! Recriando...")
                criar_banco_direto()
                break
        
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {str(e)}")

# Executar criação do banco na inicialização
criar_banco_se_necessario()

# ==================== FUNÇÕES AUXILIARES ====================
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login primeiro', 'erro')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login primeiro', 'erro')
            return redirect(url_for('login'))
        conn = get_db()
        usuario = conn.execute('SELECT is_admin FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        conn.close()
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
        
        conn = get_db()
        
        convidado_por = None
        nome_convidante = None
        if codigo_convite:
            convite_valido = conn.execute('SELECT id, nome FROM usuarios WHERE codigo_convite = ?', (codigo_convite,)).fetchone()
            if convite_valido:
                convidado_por = codigo_convite
                nome_convidante = convite_valido['nome']
        
        validade_fim = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
        
        try:
            conn.execute('''
                INSERT INTO usuarios (nome, email, telefone, senha, codigo_convite, convidado_por, validade_inicio, validade_fim)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, email, telefone, senha_hash, codigo_proprio, convidado_por, 
                  datetime.now().strftime('%Y-%m-%d'), validade_fim))
            conn.commit()
            
            if nome_convidante:
                flash(f'✅ Cadastro realizado! Você foi convidado por {nome_convidante}', 'sucesso')
            else:
                flash('Cadastro realizado com sucesso! Faça login.', 'sucesso')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email já cadastrado!', 'erro')
        finally:
            conn.close()
    
    return render_template('cadastro.html', codigo_ref=codigo_ref)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha_hash)).fetchone()
        conn.close()
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['is_admin'] = usuario['is_admin']
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
    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    
    total_convidados = conn.execute('SELECT COUNT(*) as total FROM usuarios WHERE convidado_por = ?', 
                                    (usuario['codigo_convite'],)).fetchone()['total']
    
    comissao_indicacao = conn.execute('''
        SELECT COALESCE(SUM(p.valor * 0.15), 0) as total 
        FROM pedidos_deposito p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE u.convidado_por = ? AND p.status = 'confirmado'
    ''', (usuario['codigo_convite'],)).fetchone()['total']
    
    conn.close()
    
    return render_template('painel.html', usuario=usuario, 
                          total_convidados=total_convidados, comissao_indicacao=comissao_indicacao)

@app.route('/api/saldo')
@login_obrigatorio
def api_saldo():
    conn = get_db()
    usuario = conn.execute('SELECT saldo_principal, saldo_comissao FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    conn.close()
    return jsonify({
        'saldo_principal': usuario['saldo_principal'],
        'saldo_comissao': usuario['saldo_comissao'],
        'total': usuario['saldo_principal'] + usuario['saldo_comissao']
    })

@app.route('/tarefas')
@login_obrigatorio
def tarefas():
    try:
        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        
        # Verificar se é domingo
        hoje = date.today()
        is_domingo = hoje.weekday() == 6
        
        # Buscar nível do usuário
        nivel_usuario = conn.execute('SELECT * FROM niveis WHERE id = ?', (usuario['nivel'],)).fetchone()
        
        if nivel_usuario:
            limite_diario = nivel_usuario['tarefas_por_dia']
            recompensa_anuncio = nivel_usuario['recompensa_por_anuncio']
        else:
            limite_diario = 2
            recompensa_anuncio = 0
        
        if is_domingo:
            limite_diario = 0
        
        # Contar tarefas feitas hoje
        tarefas_feitas_hoje = conn.execute('''
            SELECT COUNT(*) as total 
            FROM tarefas_assistidas 
            WHERE usuario_id = ? AND date(data_assistida) = date('now')
        ''', (session['usuario_id'],)).fetchone()['total']
        
        # Buscar todos os níveis
        niveis = conn.execute('SELECT * FROM niveis ORDER BY id').fetchall()
        
        # Calcular progresso
        progresso = {}
        for nivel in niveis:
            nivel_id = nivel['id']
            total_tarefas_nivel = conn.execute('''
                SELECT COUNT(*) as total FROM tarefas_multimidia 
                WHERE nivel_requerido = ? AND ativo = 1
            ''', (nivel_id,)).fetchone()['total']
            
            feitas_nivel = conn.execute('''
                SELECT COUNT(DISTINCT t.id) as total 
                FROM tarefas_multimidia t
                JOIN tarefas_assistidas ut ON t.id = ut.tarefa_id
                WHERE ut.usuario_id = ? AND t.nivel_requerido = ?
            ''', (session['usuario_id'], nivel_id)).fetchone()['total']
            
            progresso[nivel_id] = {'total': total_tarefas_nivel, 'feitas': feitas_nivel}
        
        conn.close()
        
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
        flash(f'Erro: {str(e)}', 'erro')
        return redirect(url_for('painel'))

@app.route('/clicar_tarefa', methods=['POST'])
@login_obrigatorio
def clicar_tarefa():
    conn = get_db()
    
    # Buscar nível do usuário
    usuario = conn.execute('SELECT nivel FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    nivel_info = conn.execute('SELECT tarefas_por_dia, recompensa_por_anuncio FROM niveis WHERE id = ?', (usuario['nivel'],)).fetchone()
    
    if nivel_info:
        limite_diario = nivel_info['tarefas_por_dia']
        recompensa = nivel_info['recompensa_por_anuncio']
    else:
        limite_diario = 0
        recompensa = 0
    
    # Verificar se é domingo
    if date.today().weekday() == 6:
        conn.close()
        return jsonify({'sucesso': False, 'erro': 'Domingo não é dia de tarefas! Volte amanhã.'})
    
    # Verificar limite diário
    tarefas_feitas_hoje = conn.execute('''
        SELECT COUNT(*) as total FROM tarefas_assistidas 
        WHERE usuario_id = ? AND date(data_assistida) = date('now')
    ''', (session['usuario_id'],)).fetchone()['total']
    
    if tarefas_feitas_hoje >= limite_diario:
        conn.close()
        return jsonify({'sucesso': False, 'erro': f'Você já atingiu o limite de {limite_diario} tarefas hoje!'})
    
    # Buscar o link da tarefa
    link_tarefa = conn.execute('SELECT url FROM tarefas_multimidia WHERE ativo = 1 LIMIT 1').fetchone()
    url = link_tarefa['url'] if link_tarefa else '#'
    
    # Registrar tarefa concluída
    conn.execute('''
        INSERT INTO tarefas_assistidas (usuario_id, tarefa_id, ganho) 
        VALUES (?, ?, ?)
    ''', (session['usuario_id'], 0, recompensa))
    
    # Adicionar saldo
    conn.execute('''
        UPDATE usuarios SET saldo_comissao = saldo_comissao + ?, ganhos_total = ganhos_total + ? 
        WHERE id = ?
    ''', (recompensa, recompensa, session['usuario_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'sucesso': True, 'recompensa': recompensa, 'url': url})

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
        
        conn = get_db()
        conn.execute('''
            INSERT INTO pedidos_deposito (usuario_id, valor, status, comprovante, metodo_pagamento, numero_pagamento, nome_titular)
            VALUES (?, ?, 'pendente', ?, 'mpesa', ?, ?)
        ''', (session['usuario_id'], valor, comprovante_path, numero_pagamento, nome_titular))
        conn.commit()
        conn.close()
        
        flash(f'✅ Pedido de depósito de {valor} MZN enviado! Aguarde confirmação.', 'sucesso')
        return redirect(url_for('painel'))
    
    return render_template('depositos.html')

@app.route('/saque', methods=['GET', 'POST'])
@login_obrigatorio
def saque():
    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
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
        
        taxa = max(valor * 0.05, 10)
        valor_liquido = valor - taxa
        
        conn.execute('''
            INSERT INTO pedidos_saque (usuario_id, valor, valor_liquido, taxa, metodo, numero_conta, nome_titular, email_paypal, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendente')
        ''', (session['usuario_id'], valor, valor_liquido, taxa, metodo, numero_conta, nome_titular, email_paypal))
        
        conn.commit()
        conn.close()
        
        flash(f'✅ Saque de {valor} MZN solicitado! Taxa: {taxa:.2f} MZN', 'sucesso')
        return redirect(url_for('painel'))
    
    conn.close()
    return render_template('saque.html', saldo_total=saldo_total, saldo_principal=usuario['saldo_principal'],
                         saldo_comissao=usuario['saldo_comissao'], pode_sacar=pode_sacar)

@app.route('/convidar')
@login_obrigatorio
def convidar():
    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    convidados = conn.execute('''
        SELECT nome, nivel_nome, data_registro FROM usuarios 
        WHERE convidado_por = ? ORDER BY data_registro DESC
    ''', (usuario['codigo_convite'],)).fetchall()
    
    conn.close()
    return render_template('convidar.html', usuario=usuario, convidados=convidados, total_convidados=len(convidados))

@app.route('/vip', methods=['GET', 'POST'])
@login_obrigatorio
def vip():
    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    niveis = conn.execute('SELECT * FROM niveis WHERE id > 0 ORDER BY id').fetchall()
    
    if request.method == 'POST':
        novo_nivel_id = int(request.form['nivel_id'])
        novo_nivel = conn.execute('SELECT * FROM niveis WHERE id = ?', (novo_nivel_id,)).fetchone()
        
        if novo_nivel:
            valor_novo_vip = novo_nivel['investimento']
            saldo_total = usuario['saldo_principal'] + usuario['saldo_comissao']
            nivel_atual = usuario['nivel']
            
            if novo_nivel_id > nivel_atual:
                if saldo_total >= valor_novo_vip:
                    if usuario['saldo_principal'] >= valor_novo_vip:
                        novo_saldo_principal = usuario['saldo_principal'] - valor_novo_vip
                        conn.execute('UPDATE usuarios SET saldo_principal = ? WHERE id = ?', 
                                   (novo_saldo_principal, session['usuario_id']))
                    else:
                        restante = valor_novo_vip - usuario['saldo_principal']
                        conn.execute('UPDATE usuarios SET saldo_principal = 0 WHERE id = ?', (session['usuario_id'],))
                        conn.execute('UPDATE usuarios SET saldo_comissao = saldo_comissao - ? WHERE id = ?', 
                                   (restante, session['usuario_id']))
                    
                    nova_validade = (datetime.now() + timedelta(days=novo_nivel['duracao_dias'])).strftime('%Y-%m-%d')
                    conn.execute('''
                        UPDATE usuarios 
                        SET nivel = ?, nivel_nome = ?, validade_inicio = ?, validade_fim = ?
                        WHERE id = ?
                    ''', (novo_nivel['id'], novo_nivel['nome'], datetime.now().strftime('%Y-%m-%d'), nova_validade, session['usuario_id']))
                    
                    conn.commit()
                    flash(f'✅ Parabéns! Você fez upgrade para {novo_nivel["nome"]}!', 'sucesso')
                else:
                    falta = valor_novo_vip - saldo_total
                    flash(f'❌ Saldo insuficiente! Você precisa de {falta:.2f} MZN para fazer upgrade.', 'erro')
            else:
                flash(f'❌ Você já possui um nível igual ou superior!', 'erro')
        
        conn.close()
        return redirect(url_for('vip'))
    
    conn.close()
    return render_template('vip.html', usuario=usuario, niveis=niveis)

# ==================== PAINEL ADMIN ====================

@app.route('/admin_painel')
@admin_obrigatorio
def admin_painel():
    conn = get_db()
    
    total_usuarios = conn.execute('SELECT COUNT(*) as total FROM usuarios').fetchone()['total']
    pendentes_deposito = conn.execute('SELECT COUNT(*) as total FROM pedidos_deposito WHERE status = "pendente"').fetchone()['total']
    pendentes_saque = conn.execute('SELECT COUNT(*) as total FROM pedidos_saque WHERE status = "pendente"').fetchone()['total']
    total_saldo_sistema = conn.execute('SELECT COALESCE(SUM(saldo_principal + saldo_comissao), 0) as total FROM usuarios').fetchone()['total']
    
    ultimos_pedidos = conn.execute('''
        SELECT p.*, u.nome 
        FROM pedidos_deposito p
        JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.data_pedido DESC
        LIMIT 10
    ''').fetchall()
    
    stats = {
        'total_usuarios': total_usuarios,
        'pendentes_deposito': pendentes_deposito,
        'pendentes_saque': pendentes_saque,
        'total_saldo_sistema': total_saldo_sistema
    }
    
    conn.close()
    return render_template('admin_painel.html', stats=stats, ultimos_pedidos=ultimos_pedidos)

@app.route('/admin/stats')
@admin_obrigatorio
def admin_stats():
    conn = get_db()
    data = {
        'total_usuarios': conn.execute('SELECT COUNT(*) as total FROM usuarios').fetchone()['total'],
        'pendentes_deposito': conn.execute('SELECT COUNT(*) as total FROM pedidos_deposito WHERE status = "pendente"').fetchone()['total'],
        'pendentes_saque': conn.execute('SELECT COUNT(*) as total FROM pedidos_saque WHERE status = "pendente"').fetchone()['total'],
        'total_saldo_sistema': conn.execute('SELECT COALESCE(SUM(saldo_principal + saldo_comissao), 0) as total FROM usuarios').fetchone()['total']
    }
    conn.close()
    return jsonify(data)

@app.route('/admin_depositos')
@admin_obrigatorio
def admin_depositos():
    conn = get_db()
    pedidos = conn.execute('''
        SELECT p.*, u.nome, u.email, u.telefone
        FROM pedidos_deposito p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.status = 'pendente'
        ORDER BY p.data_pedido DESC
    ''').fetchall()
    
    historico = conn.execute('''
        SELECT p.*, u.nome
        FROM pedidos_deposito p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.status != 'pendente'
        ORDER BY p.data_pedido DESC
        LIMIT 50
    ''').fetchall()
    
    conn.close()
    return render_template('admin_depositos.html', pedidos=pedidos, historico=historico)

@app.route('/admin_saques')
@admin_obrigatorio
def admin_saques():
    conn = get_db()
    pendentes = conn.execute('''
        SELECT p.*, u.nome as usuario_nome, u.email as usuario_email
        FROM pedidos_saque p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.status = 'pendente'
        ORDER BY p.data_pedido DESC
    ''').fetchall()
    
    historico = conn.execute('''
        SELECT p.*, u.nome as usuario_nome
        FROM pedidos_saque p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.status != 'pendente'
        ORDER BY p.data_pedido DESC
        LIMIT 50
    ''').fetchall()
    
    conn.close()
    return render_template('admin_saques.html', pendentes=pendentes, historico=historico)

@app.route('/admin_usuarios')
@admin_obrigatorio
def admin_usuarios():
    conn = get_db()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY id').fetchall()
    niveis = conn.execute('SELECT * FROM niveis').fetchall()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=usuarios, niveis=niveis)

@app.route('/admin_tarefas')
@admin_obrigatorio
def admin_tarefas():
    conn = get_db()
    tarefas = conn.execute('SELECT * FROM tarefas_multimidia ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_tarefas.html', tarefas=tarefas)

@app.route('/admin/confirmar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def confirmar_deposito(pedido_id):
    conn = get_db()
    pedido = conn.execute('SELECT p.*, u.nome, u.email, u.telefone FROM pedidos_deposito p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?', (pedido_id,)).fetchone()
    
    if request.method == 'POST':
        conn.execute('UPDATE pedidos_deposito SET status = "confirmado", data_confirmacao = CURRENT_TIMESTAMP WHERE id = ?', (pedido_id,))
        conn.execute('UPDATE usuarios SET saldo_principal = saldo_principal + ? WHERE id = ?', (pedido['valor'], pedido['usuario_id']))
        conn.commit()
        flash(f'✅ Depósito de {pedido["valor"]} MZN confirmado!', 'sucesso')
        return redirect(url_for('admin_depositos'))
    
    return render_template('confirmar_deposito.html', pedido=pedido)

@app.route('/admin/rejeitar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def rejeitar_deposito(pedido_id):
    conn = get_db()
    pedido = conn.execute('SELECT p.*, u.nome FROM pedidos_deposito p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?', (pedido_id,)).fetchone()
    
    if request.method == 'POST':
        conn.execute('UPDATE pedidos_deposito SET status = "rejeitado" WHERE id = ?', (pedido_id,))
        conn.commit()
        flash(f'❌ Depósito de {pedido["valor"]} MZN rejeitado!', 'erro')
        return redirect(url_for('admin_depositos'))
    
    return render_template('rejeitar_deposito.html', pedido=pedido)

@app.route('/admin/confirmar_saque/<int:saque_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def confirmar_saque(saque_id):
    conn = get_db()
    saque = conn.execute('SELECT p.*, u.nome as usuario_nome, u.email as usuario_email FROM pedidos_saque p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?', (saque_id,)).fetchone()
    
    if request.method == 'POST':
        conn.execute('UPDATE usuarios SET saldo_comissao = MAX(saldo_comissao - ?, 0) WHERE id = ?', (saque['valor'], saque['usuario_id']))
        conn.execute('UPDATE pedidos_saque SET status = "pago", data_processamento = CURRENT_TIMESTAMP WHERE id = ?', (saque_id,))
        conn.commit()
        flash(f'✅ Saque de {saque["valor"]} MZN confirmado!', 'sucesso')
        return redirect(url_for('admin_saques'))
    
    return render_template('confirmar_saque.html', saque=saque)

@app.route('/admin/rejeitar_saque/<int:saque_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def rejeitar_saque(saque_id):
    conn = get_db()
    saque = conn.execute('SELECT p.*, u.nome as usuario_nome FROM pedidos_saque p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?', (saque_id,)).fetchone()
    
    if request.method == 'POST':
        conn.execute('UPDATE pedidos_saque SET status = "rejeitado", data_processamento = CURRENT_TIMESTAMP WHERE id = ?', (saque_id,))
        conn.commit()
        flash(f'❌ Saque de {saque["valor"]} MZN rejeitado!', 'erro')
        return redirect(url_for('admin_saques'))
    
    return render_template('rejeitar_saque.html', saque=saque)

@app.route('/admin/ajustar_saldo/<int:usuario_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def ajustar_saldo(usuario_id):
    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
    niveis = conn.execute('SELECT * FROM niveis').fetchall()
    
    if request.method == 'POST':
        tipo_saldo = request.form['tipo_saldo']
        valor = float(request.form['valor'])
        operacao = request.form['operacao']
        nivel_id = int(request.form.get('nivel_id', 0))
        
        if operacao == 'adicionar':
            conn.execute(f'UPDATE usuarios SET {tipo_saldo} = {tipo_saldo} + ? WHERE id = ?', (valor, usuario_id))
        else:
            conn.execute(f'UPDATE usuarios SET {tipo_saldo} = MAX({tipo_saldo} - ?, 0) WHERE id = ?', (valor, usuario_id))
        
        if nivel_id > 0:
            nivel = conn.execute('SELECT * FROM niveis WHERE id = ?', (nivel_id,)).fetchone()
            if nivel:
                nova_validade = (datetime.now() + timedelta(days=nivel['duracao_dias'])).strftime('%Y-%m-%d')
                conn.execute('UPDATE usuarios SET nivel = ?, nivel_nome = ?, validade_inicio = ?, validade_fim = ? WHERE id = ?',
                            (nivel['id'], nivel['nome'], datetime.now().strftime('%Y-%m-%d'), nova_validade, usuario_id))
        
        conn.commit()
        flash('✅ Saldo ajustado!', 'sucesso')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('ajustar_saldo.html', usuario=usuario, niveis=niveis)

@app.route('/admin/deposito_manual', methods=['POST'])
@admin_obrigatorio
def deposito_manual():
    usuario_id = int(request.form['usuario_id'])
    tipo_saldo = request.form['tipo_saldo']
    valor = float(request.form['valor'])
    nivel_id = int(request.form.get('nivel_id', 0))
    
    conn = get_db()
    conn.execute(f'UPDATE usuarios SET {tipo_saldo} = {tipo_saldo} + ? WHERE id = ?', (valor, usuario_id))
    
    if nivel_id > 0:
        nivel = conn.execute('SELECT * FROM niveis WHERE id = ?', (nivel_id,)).fetchone()
        if nivel:
            nova_validade = (datetime.now() + timedelta(days=nivel['duracao_dias'])).strftime('%Y-%m-%d')
            conn.execute('UPDATE usuarios SET nivel = ?, nivel_nome = ?, validade_inicio = ?, validade_fim = ? WHERE id = ?',
                        (nivel['id'], nivel['nome'], datetime.now().strftime('%Y-%m-%d'), nova_validade, usuario_id))
    
    conn.commit()
    flash(f'✅ Adicionado {valor} MZN ao usuário!', 'sucesso')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/adicionar_tarefa_multimidia', methods=['POST'])
@admin_obrigatorio
def adicionar_tarefa_multimidia():
    titulo = request.form['titulo']
    descricao = request.form.get('descricao', '')
    tipo = request.form['tipo']
    url = request.form['url']
    recompensa = float(request.form['recompensa'])
    duracao = int(request.form.get('duracao', 30))
    nivel_requerido = int(request.form.get('nivel_requerido', 1))
    
    conn = get_db()
    conn.execute('''
        INSERT INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, duracao_segundos, nivel_requerido)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (titulo, descricao, tipo, url, recompensa, duracao, nivel_requerido))
    conn.commit()
    conn.close()
    
    flash('✅ Tarefa adicionada!', 'sucesso')
    return redirect(url_for('admin_tarefas'))

@app.route('/admin/remover_tarefa_multimidia/<int:tarefa_id>')
@admin_obrigatorio
def remover_tarefa_multimidia(tarefa_id):
    conn = get_db()
    conn.execute('DELETE FROM tarefas_multimidia WHERE id = ?', (tarefa_id,))
    conn.commit()
    conn.close()
    flash('❌ Tarefa removida!', 'erro')
    return redirect(url_for('admin_tarefas'))

# ==================== INICIALIZAÇÃO ====================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 SERVIDOR INICIADO COM SUCESSO!")
    print("=" * 60)
    print(f"📍 Acesse: http://localhost:{PORT}")
    print("👑 Admin: admin@admin.com / admin123")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=PORT)
