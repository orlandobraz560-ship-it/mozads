import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Verificar se a coluna já existe
    cursor.execute("PRAGMA table_info(tarefas_multimidia)")
    colunas = [coluna[1] for coluna in cursor.fetchall()]
    
    if 'nivel_requerido' not in colunas:
        print("📌 Adicionando coluna nivel_requerido...")
        cursor.execute("ALTER TABLE tarefas_multimidia ADD COLUMN nivel_requerido INTEGER DEFAULT 1")
        print("✅ Coluna adicionada com sucesso!")
    else:
        print("✅ Coluna nivel_requerido já existe!")
    
    conn.commit()
    print("🎉 Banco de dados atualizado com sucesso!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    
finally:
    conn.close()