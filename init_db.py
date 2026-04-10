import sqlite3
import hashlib
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Tabela de usuários
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

# Tabela de níveis (SEM ganho diário automático)
cursor.execute('''
CREATE TABLE IF NOT EXISTS niveis (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    investimento REAL,
    tarefas_por_dia INTEGER DEFAULT 0,
    duracao_dias INTEGER DEFAULT 180
)
''')

# Inserir níveis padrão
niveis = [
    (0, 'Estagiário', 0, 2, 180),
    (1, 'VIP 1', 600, 4, 180),
    (2, 'VIP 2', 3000, 6, 180),
    (3, 'VIP 3', 12000, 8, 180),
    (4, 'VIP 4', 30000, 10, 180),
    (5, 'VIP 5', 90000, 12, 180),
    (6, 'VIP 6', 300000, 15, 180),
    (7, 'VIP 7', 900000, 20, 180),
]
cursor.executemany('INSERT OR IGNORE INTO niveis (id, nome, investimento, tarefas_por_dia, duracao_dias) VALUES (?, ?, ?, ?, ?)', niveis)

# Tabela de pedidos de depósito
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

# Tabela de pedidos de saque
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

# Tabela de tarefas multimídia
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

# Tabela para registrar tarefas assistidas
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

# Inserir tarefas padrão
tarefas_padrao = [
    ("Anúncio 1", "Assista ao anúncio e ganhe 30 MZN", "video", "https://www.youtube.com/embed/dQw4w9WgXcQ", 30, 30, 1),
    ("Anúncio 2", "Assista ao anúncio e ganhe 50 MZN", "video", "https://www.youtube.com/embed/dQw4w9WgXcQ", 50, 30, 1),
    ("Imagem Promocional", "Visualize a imagem e ganhe 20 MZN", "imagem", "https://placehold.co/400x300/667eea/white?text=Ganhe+dinheiro", 20, 10, 1),
]
cursor.executemany('INSERT OR IGNORE INTO tarefas_multimidia (titulo, descricao, tipo, url, recompensa, duracao_segundos, nivel_requerido) VALUES (?, ?, ?, ?, ?, ?, ?)', tarefas_padrao)

# Criar admin padrão
senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
codigo_admin = "ADMIN001"

admin_exists = cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@admin.com',)).fetchone()

if not admin_exists:
    cursor.execute('''
    INSERT INTO usuarios (nome, email, senha, codigo_convite, is_admin, nivel, nivel_nome, saldo_principal, saldo_comissao)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ("Administrador", "admin@admin.com", senha_hash, codigo_admin, 1, 0, "Admin", 0, 0))

conn.commit()
conn.close()

print("=" * 50)
print("✅ Banco de dados criado com sucesso!")
print("=" * 50)
print("📋 Credenciais de acesso:")
print("   Admin: admin@admin.com")
print("   Senha: admin123")
print("=" * 50)
print("🎯 Níveis disponíveis:")
for nivel in niveis:
    print(f"   {nivel[1]}: Investimento {nivel[2]} MZN | {nivel[3]} tarefas/dia")
print("=" * 50)