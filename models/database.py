import sqlite3
from datetime import datetime
from config import DATABASE_FILE

class DatabaseManager:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dados_salvos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                chave TEXT NOT NULL,
                valor TEXT NOT NULL,
                categoria TEXT DEFAULT 'geral',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, chave)
            )
        """)

        cursor.execute("PRAGMA table_info(dados_salvos)")
        colunas = [coluna[1] for coluna in cursor.fetchall()]

        if 'session_id' not in colunas:
            print("Migrando banco de dados para suporte a sessões...")
            cursor.execute("ALTER TABLE dados_salvos ADD COLUMN session_id TEXT DEFAULT 'legacy'")
            print(" Migração concluída!")

        conn.commit()
        conn.close()
        print(f"Banco de dados inicializado: {self.db_file}")

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def salvar_dados(self, chave, valor, categoria="geral", session_id=None):
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT valor FROM dados_salvos WHERE session_id = ? AND chave = ?',
                (session_id, chave)
            )
            resultado_existente = cursor.fetchone()

            if resultado_existente:
                valor_antigo = resultado_existente[0]
                cursor.execute("""
                    UPDATE dados_salvos 
                    SET valor = ?, categoria = ?, data_atualizacao = CURRENT_TIMESTAMP 
                    WHERE session_id = ? AND chave = ?
                """, (valor, categoria, session_id, chave))
                operacao = "atualizado"
            else:
                cursor.execute("""
                    INSERT INTO dados_salvos (session_id, chave, valor, categoria)
                    VALUES (?, ?, ?, ?)
                """, (session_id, chave, valor, categoria))
                operacao = "salvo"

            conn.commit()
            conn.close()

            print(f"Dado {operacao} para sessão {session_id[:8]}...: {chave} = {valor}")

            return {
                "status": "sucesso",
                "chave": chave,
                "valor": valor,
                "operacao": operacao,
                "session_id": session_id[:8] + "..."
            }

        except Exception as e:
            return {"status": "erro", "mensagem": str(e)}

    def buscar_dados(self, chave=None, categoria=None, session_id=None):
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if chave:
                cursor.execute("""
                    SELECT chave, valor, categoria, data_criacao, data_atualizacao
                    FROM dados_salvos WHERE session_id = ? AND chave = ?
                """, (session_id, chave))
                resultado = cursor.fetchone()

                if resultado:
                    conn.close()
                    return {
                        "status": "sucesso",
                        "encontrado": True,
                        "chave": resultado[0],
                        "valor": resultado[1],
                        "session_id": session_id[:8] + "..."
                    }
                else:
                    conn.close()
                    return {
                        "status": "sucesso",
                        "encontrado": False,
                        "mensagem": f"Nenhum dado encontrado para '{chave}' na sessão atual"
                    }
            else:
                query = """
                    SELECT chave, valor, categoria, data_criacao
                    FROM dados_salvos
                    WHERE session_id = ?
                """
                params = [session_id]
                
                if categoria:
                    query += " AND categoria = ?"
                    params.append(categoria)
                
                query += " ORDER BY data_atualizacao DESC LIMIT 20"
                
                cursor.execute(query, params)
                resultados = cursor.fetchall()

                dados = []
                for resultado in resultados:
                    dados.append({
                        "chave": resultado[0],
                        "valor": resultado[1],
                        "categoria": resultado[2],
                        "criado_em": resultado[3]
                    })

                conn.close()
                return {
                    "status": "sucesso",
                    "total_encontrados": len(dados),
                    "dados": dados,
                    "session_id": session_id[:8] + "..."
                }

        except Exception as e:
            return {"status": "erro", "mensagem": str(e)}

    def deletar_dados(self, chave, session_id=None):
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT valor FROM dados_salvos WHERE session_id = ? AND chave = ?',
                (session_id, chave)
            )
            resultado_existente = cursor.fetchone()

            if not resultado_existente:
                conn.close()
                return {
                    "status": "erro",
                    "mensagem": f"Dado '{chave}' não encontrado na sessão atual"
                }

            cursor.execute(
                'DELETE FROM dados_salvos WHERE session_id = ? AND chave = ?',
                (session_id, chave)
            )

            conn.commit()
            conn.close()

            print(f"Dado deletado da sessão {session_id[:8]}...: {chave}")

            return {
                "status": "sucesso",
                "chave": chave,
                "mensagem": f"Dado '{chave}' removido com sucesso",
                "session_id": session_id[:8] + "..."
            }

        except Exception as e:
            return {"status": "erro", "mensagem": str(e)}

    def listar_categorias(self, session_id=None):
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT categoria, COUNT(*) as total
                FROM dados_salvos 
                WHERE session_id = ? 
                GROUP BY categoria 
                ORDER BY total DESC
            """, (session_id,))
            
            resultados = cursor.fetchall()
            
            categorias = []
            for resultado in resultados:
                categorias.append({
                    "categoria": resultado[0],
                    "total_itens": resultado[1]
                })

            conn.close()

            return {
                "status": "sucesso",
                "categorias": categorias,
                "total_categorias": len(categorias),
                "session_id": session_id[:8] + "..."
            }

        except Exception as e:
            return {"status": "erro", "mensagem": str(e)}

    def cleanup_expired_sessions(self, active_session_ids):
        """ NOVO: Limpar dados de sessões expiradas"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT session_id FROM dados_salvos")
            all_sessions = [row[0] for row in cursor.fetchall()]
        
            orphaned_sessions = [sid for sid in all_sessions if sid not in active_session_ids and sid != 'legacy']
            
            if orphaned_sessions:
                placeholders = ','.join(['?' for _ in orphaned_sessions])
                cursor.execute(f"DELETE FROM dados_salvos WHERE session_id IN ({placeholders})", orphaned_sessions)
                deleted_count = cursor.rowcount
                
                conn.commit()
                print(f" Limpeza automática: {deleted_count} dados órfãos removidos de {len(orphaned_sessions)} sessões")
                
                conn.close()
                return {"status": "sucesso", "deleted_count": deleted_count, "orphaned_sessions": len(orphaned_sessions)}
            
            conn.close()
            return {"status": "sucesso", "deleted_count": 0, "orphaned_sessions": 0}
            
        except Exception as e:
            print(f" Erro na limpeza automática: {e}")
            return {"status": "erro", "mensagem": str(e)}

db_manager = DatabaseManager()