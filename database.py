import sqlite3
import os
import datetime

class DatabaseManager:
    def __init__(self, db_file_path):
        self.db_path = db_file_path
        db_dir_path = os.path.dirname(self.db_path)
        if db_dir_path and not os.path.exists(db_dir_path):
            try:
                os.makedirs(db_dir_path, exist_ok=True)
                print(f"INFO: Diretório do banco de dados criado: {db_dir_path}")
            except OSError as e:
                print(f"AVISO: Não foi possível criar o diretório do banco de dados {db_dir_path}. Erro: {e}")
        self.init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;") # Habilita chaves estrangeiras
        return conn

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        conn = self._get_conn()
        cursor = conn.cursor()
        last_row_id = None
        success = False
        result_data = None
        try:
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
                if query.strip().upper().startswith("INSERT"):
                    last_row_id = cursor.lastrowid
                success = True
            
            if fetch_one:
                result_data = cursor.fetchone()
                success = True
            elif fetch_all:
                result_data = cursor.fetchall()
                success = True
            
            if not (commit or fetch_one or fetch_all): # Para DDL ou outras queries sem retorno/commit explícito
                if query.strip().upper().startswith(("CREATE", "ALTER", "DROP")):
                    conn.commit() # DDL statements são implicitamente commitados em alguns DBs, mas explícito é melhor
                success = True

        except sqlite3.Error as e:
            print(f"Erro BD SQLite: {e} | Query: {query} | Params: {params}")
            conn.rollback() # Garante rollback em caso de erro
            success = False
        finally:
            conn.close()
        
        if commit and success:
            return last_row_id if last_row_id is not None else True
        if (fetch_one or fetch_all) and success:
            return result_data
        return success

    def init_db(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )""",
            """CREATE TABLE IF NOT EXISTS funcoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )""",
            """CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                cpf TEXT UNIQUE,
                rg TEXT,
                ctps TEXT,
                serie TEXT,
                pis TEXT,
                departamento_id INTEGER,
                funcao_id INTEGER,
                setor TEXT CHECK(setor IN ('Produtivo', 'Administrativo', 'Outro')),
                data_admissao TEXT,
                data_treinamento TEXT,
                FOREIGN KEY (departamento_id) REFERENCES departamentos (id) ON DELETE SET NULL,
                FOREIGN KEY (funcao_id) REFERENCES funcoes (id) ON DELETE SET NULL
            )"""
            # Adicionar mais tabelas para as próximas etapas aqui
        ]
        print(f"Inicializando banco de dados em: {self.db_path}")
        for query in queries:
            self.execute_query(query)
        print("Banco de dados inicializado com sucesso.")

    # --- DEPARTAMENTOS ---
    def add_departamento(self, nome):
        query = "INSERT INTO departamentos (nome) VALUES (?)"
        return self.execute_query(query, (nome,), commit=True)

    def get_all_departamentos(self):
        query = "SELECT * FROM departamentos ORDER BY nome"
        return self.execute_query(query, fetch_all=True)

    def get_departamento_by_id(self, dep_id):
        query = "SELECT * FROM departamentos WHERE id = ?"
        return self.execute_query(query, (dep_id,), fetch_one=True)

    def update_departamento(self, dep_id, nome):
        query = "UPDATE departamentos SET nome = ? WHERE id = ?"
        return self.execute_query(query, (nome, dep_id), commit=True)

    def delete_departamento(self, dep_id):
        # Antes de deletar, verificar se está em uso por algum funcionário
        funcionarios_com_dep = self.execute_query(
            "SELECT 1 FROM funcionarios WHERE departamento_id = ? LIMIT 1",
            (dep_id,),
            fetch_one=True
        )
        if funcionarios_com_dep:
            return "EM_USO" # Sinaliza que não pode ser excluído
        
        query = "DELETE FROM departamentos WHERE id = ?"
        return self.execute_query(query, (dep_id,), commit=True)

    # --- FUNCOES ---
    def add_funcao(self, nome):
        query = "INSERT INTO funcoes (nome) VALUES (?)"
        return self.execute_query(query, (nome,), commit=True)

    def get_all_funcoes(self):
        query = "SELECT * FROM funcoes ORDER BY nome"
        return self.execute_query(query, fetch_all=True)

    def get_funcao_by_id(self, func_id):
        query = "SELECT * FROM funcoes WHERE id = ?"
        return self.execute_query(query, (func_id,), fetch_one=True)

    def update_funcao(self, func_id, nome):
        query = "UPDATE funcoes SET nome = ? WHERE id = ?"
        return self.execute_query(query, (nome, func_id), commit=True)

    def delete_funcao(self, func_id):
        # Antes de deletar, verificar se está em uso por algum funcionário
        funcionarios_com_funcao = self.execute_query(
            "SELECT 1 FROM funcionarios WHERE funcao_id = ? LIMIT 1",
            (func_id,),
            fetch_one=True
        )
        if funcionarios_com_funcao:
            return "EM_USO"
            
        query = "DELETE FROM funcoes WHERE id = ?"
        return self.execute_query(query, (func_id,), commit=True)

    # --- FUNCIONARIOS ---
    def add_funcionario(self, data):
        query = """INSERT INTO funcionarios 
                   (nome_completo, cpf, rg, ctps, serie, pis, departamento_id, funcao_id, setor, data_admissao, data_treinamento)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            data.get('nome_completo'), data.get('cpf'), data.get('rg'), data.get('ctps'), data.get('serie'),
            data.get('pis'), data.get('departamento_id'), data.get('funcao_id'), data.get('setor'),
            data.get('data_admissao') or None, data.get('data_treinamento') or None
        )
        return self.execute_query(query, params, commit=True)

    def get_all_funcionarios(self):
        query = """
            SELECT f.*, d.nome as departamento_nome, func.nome as funcao_nome
            FROM funcionarios f
            LEFT JOIN departamentos d ON f.departamento_id = d.id
            LEFT JOIN funcoes func ON f.funcao_id = func.id
            ORDER BY f.nome_completo
        """
        return self.execute_query(query, fetch_all=True)

    def get_funcionario_by_id(self, func_id):
        query = """
            SELECT f.*, d.nome as departamento_nome, func.nome as funcao_nome
            FROM funcionarios f
            LEFT JOIN departamentos d ON f.departamento_id = d.id
            LEFT JOIN funcoes func ON f.funcao_id = func.id
            WHERE f.id = ?
        """
        return self.execute_query(query, (func_id,), fetch_one=True)

    def update_funcionario(self, func_id, data):
        query = """UPDATE funcionarios SET
                   nome_completo = ?, cpf = ?, rg = ?, ctps = ?, serie = ?, pis = ?,
                   departamento_id = ?, funcao_id = ?, setor = ?, data_admissao = ?, data_treinamento = ?
                   WHERE id = ?"""
        params = (
            data.get('nome_completo'), data.get('cpf'), data.get('rg'), data.get('ctps'), data.get('serie'),
            data.get('pis'), data.get('departamento_id'), data.get('funcao_id'), data.get('setor'),
            data.get('data_admissao') or None, data.get('data_treinamento') or None,
            func_id
        )
        return self.execute_query(query, params, commit=True)

    def delete_funcionario(self, func_id):
        query = "DELETE FROM funcionarios WHERE id = ?"
        return self.execute_query(query, (func_id,), commit=True)

    def search_funcionarios(self, search_term):
        query = """
            SELECT f.*, d.nome as departamento_nome, func.nome as funcao_nome
            FROM funcionarios f
            LEFT JOIN departamentos d ON f.departamento_id = d.id
            LEFT JOIN funcoes func ON f.funcao_id = func.id
            WHERE f.nome_completo LIKE ? OR f.cpf LIKE ? OR d.nome LIKE ? OR func.nome LIKE ?
            ORDER BY f.nome_completo
        """
        like_term = f"%{search_term}%"
        return self.execute_query(query, (like_term, like_term, like_term, like_term), fetch_all=True)

