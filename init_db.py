import sqlite3
import hashlib
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# ==================== TABELA DE USUÁRIOS ====================
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

# ==================== TABELA DE NÍVEIS ====================
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

# Inserir níveis padrão
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

# ==================== TABELA DE PEDIDOS DE DEPÓSITO ====================
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
    data_confirmacao TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
''')

# ==================== TABELA DE PEDIDOS DE SAQUE ====================
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
    observacao TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
''')

# ==================== TABELA DE TAREFAS MULTIMÍDIA ====================
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

# ==================== TABELA DE TAREFAS ASSISTIDAS ====================
cursor.execute('''
CREATE TABLE IF NOT EXISTS tarefas_assistidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    tarefa_id INTEGER,
    data_assistida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ganho REAL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (tarefa_id) REFERENCES tarefas_multimidia(id)
)
''')

# ==================== TABELA DE GANHOS DIÁRIOS ====================
cursor.execute('''
CREATE TABLE IF NOT EXISTS ganhos_diarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    data DATE,
    valor REAL,
    pago INTEGER DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
''')

# ==================== TABELA DE PRODUTOS (SHOP) ====================
cursor.execute('''
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    imagem TEXT,
    categoria TEXT DEFAULT 'outros',
    ativo INTEGER DEFAULT 1,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# ==================== TABELA DE COMPRAS (SHOP) ====================
cursor.execute('''
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    produto_id INTEGER,
    valor REAL,
    data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
)
''')

# ==================== INSERIR PRODUTOS PADRÃO (SHOP) ====================
produtos_padrao = [
    ('Smartphone XYZ', 'Smartphone de última geração com 128GB', 5000, 'https://placehold.co/400x400/667eea/white?text=Smartphone', 'eletronicos'),
    ('Fones Bluetooth', 'Fones de ouvido sem fio com cancelamento de ruído', 800, 'https://placehold.co/400x400/667eea/white?text=Fones', 'eletronicos'),
    ('Power Bank 10000mAh', 'Carregador portátil de alta capacidade', 400, 'https://placehold.co/400x400/667eea/white?text=Power+Bank', 'eletronicos'),
    ('Smartwatch Pro', 'Relógio inteligente com monitor cardíaco', 1500, 'https://placehold.co/400x400/667eea/white?text=Smartwatch', 'eletronicos'),
    ('Camiseta Premium', 'Camiseta 100% algodão, várias cores', 300, 'https://placehold.co/400x400/667eea/white?text=Camiseta', 'moda'),
    ('Calça Jeans', 'Calça jeans moderna e confortável', 600, 'https://placehold.co/400x400/667eea/white?text=Calça+Jeans', 'moda'),
    ('Tênis Esportivo', 'Tênis confortável para corrida e academia', 1200, 'https://placehold.co/400x400/667eea/white?text=Tênis', 'moda'),
    ('Jaqueta Corta-vento', 'Jaqueta leve e resistente', 800, 'https://placehold.co/400x400/667eea/white?text=Jaqueta', 'moda'),
    ('Cadeira Gamer', 'Cadeira ergonômica para jogos', 8000, 'https://placehold.co/400x400/667eea/white?text=Cadeira+Gamer', 'moveis'),
    ('Mesa Digitalizadora', 'Mesa para desenho digital', 2500, 'https://placehold.co/400x400/667eea/white?text=Mesa+Digital', 'moveis'),
    ('Estante Modular', 'Estante moderna para livros', 1200, 'https://placehold.co/400x400/667eea/white?text=Estante', 'moveis'),
    ('Voucher Amazon', 'Voucher de compras na Amazon', 100, 'https://placehold.co/400x400/667eea/white?text=Voucher+Amazon', 'vouchers'),
    ('Voucher Netflix', 'Mensalidade Netflix Premium', 300, 'https://placehold.co/400x400/667eea/white?text=Voucher+Netflix', 'vouchers'),
    ('Voucher Spotify', 'Mensalidade Spotify Premium', 200, 'https://placehold.co/400x400/667eea/white?text=Voucher+Spotify', 'vouchers'),
    ('Voucher Uber', 'Voucher de corridas Uber', 150, 'https://placehold.co/400x400/667eea/white?text=Voucher+Uber', 'vouchers'),
]
cursor.executemany('INSERT OR IGNORE INTO produtos (nome, descricao, preco, imagem, categoria) VALUES (?, ?, ?, ?, ?)', produtos_padrao)

# ==================== INSERIR TAREFAS PADRÃO ====================
tarefas_padrao = [
    ('Anúncio Diário', 'Clique para assistir e ganhar', 'link', 'https://omg10.com/4/10861968', 10, 30, 1),
]
cursor.executemany('INSERT OR IGNORE INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, duracao_segundos, nivel_requerido) VALUES (?, ?, ?, ?, ?, ?, ?)', tarefas_padrao)

# ==================== CRIAR ADMIN PADRÃO ====================
senha_hash = hashlib.sha256("Braz0033@".encode()).hexdigest()
codigo_admin = "ADMIN001"

admin_exists = cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@admin.com',)).fetchone()

if not admin_exists:
    cursor.execute('''
    INSERT INTO usuarios (nome, email, senha, codigo_convite, is_admin, nivel, nivel_nome, saldo_principal, saldo_comissao)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ("Administrador", "admin@admin.com", senha_hash, codigo_admin, 1, 0, "Admin", 0, 0))

# ==================== COMMIT E FINALIZAÇÃO ====================
conn.commit()
conn.close()

print("=" * 60)
print("✅ Banco de dados criado com sucesso!")
print("=" * 60)
print("📋 Credenciais de acesso:")
print("   Admin: admin@admin.com")
print("   Senha: admin123")
print("=" * 60)
print("🎯 Níveis disponíveis:")
for nivel in niveis:
    print(f"   {nivel[1]}: Investimento {nivel[2]} MZN | {nivel[3]} tarefas/dia | +{nivel[4]} MZN por anúncio")
print("=" * 60)
print("🛒 Produtos disponíveis no Shop:")
for produto in produtos_padrao:
    print(f"   {produto[0]} - {produto[2]} MZN ({produto[4]})")
print("=" * 60)
