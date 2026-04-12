from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import secrets
import os
import json
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_mude_para_algo_seguro_123456')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Configuração para upload de imagens
UPLOAD_FOLDER = 'static/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Criar pasta para comprovantes
if not os.path.exists('comprovantes'):
    os.makedirs('comprovantes')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== CORREÇÃO AUTOMÁTICA DO BANCO ====================
def corrigir_banco_automaticamente():
    """Corrige o banco de dados automaticamente sem apagar dados"""
    try:
        # Se o banco não existir, NÃO FAZ NADA
        if not os.path.exists('database.db'):
            print("⚠️ Banco de dados não encontrado! Execute init_db.py manualmente.")
            return  # Sair sem criar nada
        
        # Se existe, apenas verificar e ajustar colunas
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Verificar colunas da tabela usuarios
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = [c[1] for c in cursor.fetchall()]
        
        # Apenas ADICIONAR colunas faltantes, NUNCA apagar dados
        colunas_necessarias = {
            'telefone': 'TEXT',
            'validade_inicio': 'TEXT',
            'validade_fim': 'TEXT',
            'ganhos_hoje': 'REAL DEFAULT 0',
            'ganhos_ontem': 'REAL DEFAULT 0',
            'ganhos_semana': 'REAL DEFAULT 0',
            'ganhos_mes': 'REAL DEFAULT 0',
            'ganhos_total': 'REAL DEFAULT 0'
        }
        
        for coluna, tipo in colunas_necessarias.items():
            if coluna not in colunas:
                try:
                    cursor.execute(f'ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}')
                    print(f'✅ Coluna {coluna} adicionada')
                except:
                    pass
        
        # Verificar colunas da tabela niveis
        cursor.execute("PRAGMA table_info(niveis)")
        colunas_niveis = [c[1] for c in cursor.fetchall()]
        
        if 'tarefas_por_dia' not in colunas_niveis:
            cursor.execute('ALTER TABLE niveis ADD COLUMN tarefas_por_dia INTEGER DEFAULT 0')
        
        if 'recompensa_por_anuncio' not in colunas_niveis:
            cursor.execute('ALTER TABLE niveis ADD COLUMN recompensa_por_anuncio REAL DEFAULT 0')
        
        # NUNCA atualizar valores dos níveis (isso pode corromper)
        # Remova a parte que atualiza os níveis
        
        conn.commit()
        conn.close()
        print('✅ Banco de dados verificado (sem recriação)!')
        
    except Exception as e:
        print(f'❌ Erro na correção do banco: {e}')
        
corrigir_banco_automaticamente()

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
        try:
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
            
            conn.close()
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('Email já cadastrado!', 'erro')
            return redirect(url_for('cadastro'))
        except Exception as e:
            print(f"❌ Erro no cadastro: {str(e)}")
            flash(f'Erro ao cadastrar: {str(e)}', 'erro')
            return redirect(url_for('cadastro'))
    
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
        SELECT COALESCE(SUM(p.valor * 0.25), 0) as total 
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
        
        hoje = date.today()
        is_domingo = hoje.weekday() == 6
        
        nivel_usuario = conn.execute('SELECT * FROM niveis WHERE id = ?', (usuario['nivel'],)).fetchone()
        
        if nivel_usuario:
            limite_diario = nivel_usuario['tarefas_por_dia'] if nivel_usuario['tarefas_por_dia'] else 2
            recompensa_anuncio = nivel_usuario['recompensa_por_anuncio'] if nivel_usuario['recompensa_por_anuncio'] else 0
        else:
            limite_diario = 2
            recompensa_anuncio = 0
        
        if is_domingo:
            limite_diario = 0
        
        tarefas_feitas_hoje = conn.execute('''
            SELECT COUNT(*) as total 
            FROM tarefas_assistidas 
            WHERE usuario_id = ? AND date(data_assistida) = date('now')
        ''', (session['usuario_id'],)).fetchone()['total']
        
        niveis = conn.execute('SELECT * FROM niveis ORDER BY id').fetchall()
        
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
        flash(f'Erro ao carregar tarefas: {str(e)}', 'erro')
        return redirect(url_for('painel'))

@app.route('/clicar_tarefa', methods=['POST'])
@login_obrigatorio
def clicar_tarefa():
    try:
        conn = get_db()
        
        URL_FIXO = "https://omg10.com/4/10861968"
        
        usuario = conn.execute('SELECT nivel FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        nivel_info = conn.execute('SELECT tarefas_por_dia, recompensa_por_anuncio FROM niveis WHERE id = ?', (usuario['nivel'],)).fetchone()
        
        if nivel_info:
            limite_diario = nivel_info['tarefas_por_dia'] if nivel_info['tarefas_por_dia'] else 2
            recompensa = nivel_info['recompensa_por_anuncio'] if nivel_info['recompensa_por_anuncio'] else 0
        else:
            limite_diario = 2
            recompensa = 0
        
        if date.today().weekday() == 6:
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Domingo não é dia de tarefas! Volte amanhã.'})
        
        tarefas_feitas_hoje = conn.execute('''
            SELECT COUNT(*) as total FROM tarefas_assistidas 
            WHERE usuario_id = ? AND date(data_assistida) = date('now')
        ''', (session['usuario_id'],)).fetchone()['total']
        
        if tarefas_feitas_hoje >= limite_diario:
            conn.close()
            return jsonify({'sucesso': False, 'erro': f'Você já atingiu o limite de {limite_diario} tarefas hoje!'})
        
        conn.execute('''
            INSERT INTO tarefas_assistidas (usuario_id, tarefa_id, ganho) 
            VALUES (?, ?, ?)
        ''', (session['usuario_id'], 0, recompensa))
        
        conn.execute('''
            UPDATE usuarios SET saldo_comissao = saldo_comissao + ?, ganhos_total = ganhos_total + ? 
            WHERE id = ?
        ''', (recompensa, recompensa, session['usuario_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': True, 'recompensa': recompensa, 'url': URL_FIXO})
    
    except Exception as e:
        print(f"❌ ERRO em /clicar_tarefa: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)})

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
                    
                    if usuario['convidado_por']:
                        comissao = valor_novo_vip * 0.25
                        conn.execute('''
                            UPDATE usuarios 
                            SET saldo_comissao = saldo_comissao + ?, 
                                ganhos_total = ganhos_total + ? 
                            WHERE codigo_convite = ?
                        ''', (comissao, comissao, usuario['convidado_por']))
                        
                        flash(f'✅ Seu convidante recebeu {comissao:.2f} MZN de comissão (25%)!', 'info')
                    
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

# ==================== SHOP (MARKETPLACE) ====================

@app.route('/shop')
@login_obrigatorio
def shop():
    try:
        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        produtos = conn.execute('SELECT * FROM produtos WHERE ativo = 1 ORDER BY id').fetchall()
        conn.close()
        return render_template('shop.html', usuario=usuario, produtos=produtos)
    
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
        
        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        produto = conn.execute('SELECT * FROM produtos WHERE id = ? AND ativo = 1', (produto_id,)).fetchone()
        
        if not produto:
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Produto não encontrado!'})
        
        saldo_total = usuario['saldo_principal'] + usuario['saldo_comissao']
        
        if saldo_total < preco:
            conn.close()
            return jsonify({'sucesso': False, 'erro': f'Saldo insuficiente!'})
        
        if usuario['saldo_principal'] >= preco:
            novo_saldo_principal = usuario['saldo_principal'] - preco
            conn.execute('UPDATE usuarios SET saldo_principal = ? WHERE id = ?', (novo_saldo_principal, session['usuario_id']))
        else:
            restante = preco - usuario['saldo_principal']
            conn.execute('UPDATE usuarios SET saldo_principal = 0 WHERE id = ?', (session['usuario_id'],))
            conn.execute('UPDATE usuarios SET saldo_comissao = saldo_comissao - ? WHERE id = ?', (restante, session['usuario_id']))
        
        conn.execute('''
            INSERT INTO compras (usuario_id, produto_id, valor, data_compra)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session['usuario_id'], produto_id, preco))
        
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': True})
    
    except Exception as e:
        print(f"❌ Erro em /comprar_produto: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)})

# ==================== ADMIN - GERENCIAR PRODUTOS ====================

@app.route('/admin_editar_shop')
@admin_obrigatorio
def admin_editar_shop():
    conn = get_db()
    produtos = conn.execute('SELECT * FROM produtos ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_editar_shop.html', produtos=produtos)

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
    
    conn = get_db()
    conn.execute('''
        INSERT INTO produtos (nome, descricao, preco, imagem, categoria, ativo)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (nome, descricao, preco, imagem_path, categoria))
    conn.commit()
    conn.close()
    
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
    
    if not imagem_path:
        imagem_url = request.form.get('imagem_url', '')
        if imagem_url:
            imagem_path = imagem_url
    
    conn = get_db()
    
    if imagem_path:
        conn.execute('''
            UPDATE produtos 
            SET nome = ?, descricao = ?, preco = ?, imagem = ?, categoria = ?
            WHERE id = ?
        ''', (nome, descricao, preco, imagem_path, categoria, produto_id))
    else:
        conn.execute('''
            UPDATE produtos 
            SET nome = ?, descricao = ?, preco = ?, categoria = ?
            WHERE id = ?
        ''', (nome, descricao, preco, categoria, produto_id))
    
    conn.commit()
    conn.close()
    
    flash('✅ Produto atualizado com sucesso!', 'sucesso')
    return redirect(url_for('admin_editar_shop'))

@app.route('/remover_produto/<int:produto_id>')
@admin_obrigatorio
def remover_produto(produto_id):
    conn = get_db()
    conn.execute('DELETE FROM produtos WHERE id = ?', (produto_id,))
    conn.commit()
    conn.close()
    
    flash('❌ Produto removido!', 'erro')
    return redirect(url_for('admin_editar_shop'))

@app.route('/alternar_produto/<int:produto_id>')
@admin_obrigatorio
def alternar_produto(produto_id):
    conn = get_db()
    produto = conn.execute('SELECT ativo FROM produtos WHERE id = ?', (produto_id,)).fetchone()
    
    if produto:
        novo_status = 0 if produto['ativo'] == 1 else 1
        conn.execute('UPDATE produtos SET ativo = ? WHERE id = ?', (novo_status, produto_id))
        flash(f'✅ Produto {"ativado" if novo_status == 1 else "desativado"}!', 'sucesso')
    
    conn.commit()
    conn.close()
    return redirect(url_for('admin_editar_shop'))

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

# ==================== ADMIN - CONFIGURAR LINK RÁPIDO ====================

@app.route('/configurar_link_rapido', methods=['POST'])
@admin_obrigatorio
def configurar_link_rapido():
    nivel_id = int(request.form['nivel_id'])
    url = request.form['url']
    recompensa = float(request.form['recompensa'])
    
    conn = get_db()
    
    # Verificar se já existe link para este nível
    existe = conn.execute('SELECT id FROM tarefas_multimidia WHERE nivel_requerido = ? AND tipo = "link"', (nivel_id,)).fetchone()
    
    if existe:
        # Atualizar link existente
        conn.execute('''
            UPDATE tarefas_multimidia 
            SET url = ?, recompensa = ?, titulo = ?, descricao = ?
            WHERE nivel_requerido = ? AND tipo = "link"
        ''', (url, recompensa, f'Anúncio VIP {nivel_id}', f'Assista ao anúncio e ganhe {recompensa} MZN', nivel_id))
        flash(f'✅ Link do VIP {nivel_id} atualizado!', 'sucesso')
    else:
        # Criar novo link
        conn.execute('''
            INSERT INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, nivel_requerido, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (f'Anúncio VIP {nivel_id}', f'Assista ao anúncio e ganhe {recompensa} MZN', 'link', url, recompensa, nivel_id, 1))
        flash(f'✅ Link do VIP {nivel_id} adicionado!', 'sucesso')
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_tarefas'))

# ==================== ADMIN - EDITAR TAREFA ====================

@app.route('/editar_tarefa/<int:tarefa_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def editar_tarefa(tarefa_id):
    conn = get_db()
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        url = request.form['url']
        recompensa = float(request.form['recompensa'])
        nivel_requerido = int(request.form['nivel_requerido'])
        
        conn.execute('''
            UPDATE tarefas_multimidia 
            SET titulo = ?, descricao = ?, url = ?, recompensa = ?, nivel_requerido = ?
            WHERE id = ?
        ''', (titulo, descricao, url, recompensa, nivel_requerido, tarefa_id))
        conn.commit()
        conn.close()
        
        flash('✅ Tarefa atualizada!', 'sucesso')
        return redirect(url_for('admin_tarefas'))
    
    tarefa = conn.execute('SELECT * FROM tarefas_multimidia WHERE id = ?', (tarefa_id,)).fetchone()
    niveis = conn.execute('SELECT * FROM niveis WHERE id > 0').fetchall()
    conn.close()
    
    return render_template('editar_tarefa.html', tarefa=tarefa, niveis=niveis)

@app.route('/confirmar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
@admin_obrigatorio
def confirmar_deposito(pedido_id):
    conn = get_db()
    pedido = conn.execute('SELECT p.*, u.nome, u.email, u.telefone FROM pedidos_deposito p JOIN usuarios u ON p.usuario_id = u.id WHERE p.id = ?', (pedido_id,)).fetchone()
    
    if request.method == 'POST':
        conn.execute('UPDATE usuarios SET saldo_principal = saldo_principal + ? WHERE id = ?', (pedido['valor'], pedido['usuario_id']))
        conn.execute('UPDATE pedidos_deposito SET status = "confirmado", data_confirmacao = CURRENT_TIMESTAMP WHERE id = ?', (pedido_id,))
        conn.commit()
        flash(f'✅ Depósito de {pedido["valor"]} MZN confirmado!', 'sucesso')
        return redirect(url_for('admin_depositos'))
    
    return render_template('confirmar_deposito.html', pedido=pedido)

@app.route('/rejeitar_deposito/<int:pedido_id>', methods=['GET', 'POST'])
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

@app.route('/confirmar_saque/<int:saque_id>', methods=['GET', 'POST'])
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

@app.route('/rejeitar_saque/<int:saque_id>', methods=['GET', 'POST'])
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

@app.route('/ajustar_saldo/<int:usuario_id>', methods=['GET', 'POST'])
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

@app.route('/deposito_manual', methods=['POST'])
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
    
    conn = get_db()
    conn.execute('''
        INSERT INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, duracao_segundos, nivel_requerido)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (titulo, descricao, tipo, url, recompensa, duracao, nivel_requerido))
    conn.commit()
    conn.close()
    
    flash('✅ Tarefa adicionada!', 'sucesso')
    return redirect(url_for('admin_tarefas'))

@app.route('/remover_tarefa_multimidia/<int:tarefa_id>')
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
    print("📍 Acesse: https://mozads.onrender.com")
    print("👑 Admin: admin@admin.com / senha: admin123")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=PORT)
