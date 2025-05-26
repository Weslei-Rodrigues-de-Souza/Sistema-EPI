import os
import datetime
import sqlite3
import json
import re 
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import DatabaseManager

# --- Configurações Globais ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = "controle_epis.db"
DB_FULL_PATH = os.path.join(BASE_DIR, DB_NAME)

# --- Inicialização do Flask App ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Instância do DatabaseManager ---
db = DatabaseManager(DB_FULL_PATH)

# --- Context Processor e Filters para Templates ---
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now(datetime.timezone.utc)}

def format_date_for_display(date_str_iso):
    if not date_str_iso: return ""
    try: return datetime.datetime.strptime(str(date_str_iso), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError: return str(date_str_iso)

def format_date_for_db(date_str_display):
    if not date_str_display: return None
    try: return datetime.datetime.strptime(str(date_str_display), '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        if len(str(date_str_display).split('-')) == 3: return str(date_str_display)
        return None

def format_cnpj_for_display(cnpj_str):
    if not cnpj_str: return ""
    cnpj_limpo = re.sub(r'\D', '', str(cnpj_str))
    if len(cnpj_limpo) == 14: return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    return cnpj_str

app.jinja_env.filters['format_date_display'] = format_date_for_display
app.jinja_env.filters['format_cnpj'] = format_cnpj_for_display

# --- Rotas Principais ---
@app.route('/')
def dashboard():
    total_funcionarios = len(db.get_all_funcionarios() or [])
    total_departamentos = len(db.get_all_departamentos() or [])
    total_funcoes = len(db.get_all_funcoes() or [])
    total_epis = len(db.get_all_epis() or [])
    total_fornecedores = len(db.get_all_fornecedores() or [])
    return render_template('dashboard.html',
                           total_funcionarios=total_funcionarios,
                           total_departamentos=total_departamentos,
                           total_funcoes=total_funcoes,
                           total_epis=total_epis,
                           total_fornecedores=total_fornecedores)

# --- Rotas para Departamentos ---
@app.route('/departamentos')
def listar_departamentos():
    return render_template('departamentos.html', departamentos=db.get_all_departamentos() or [])
@app.route('/departamentos/json/<int:dep_id>')
def get_departamento_json(dep_id):
    d = db.get_departamento_by_id(dep_id)
    if d: return jsonify(dict(d))
    return jsonify({"error": "Departamento não encontrado"}), 404
@app.route('/departamentos/salvar', methods=['POST'])
@app.route('/departamentos/salvar/<int:dep_id>', methods=['POST'])
def salvar_departamento(dep_id=None):
    nome = request.form.get('nome_departamento')
    if not nome: flash('O nome do departamento é obrigatório.', 'danger')
    else:
        try:
            if dep_id:
                if db.update_departamento(dep_id, nome): flash('Departamento atualizado!', 'success')
            else:
                if db.add_departamento(nome): flash('Departamento adicionado!', 'success')
        except sqlite3.IntegrityError: flash(f"Erro: O departamento '{nome}' já existe.", 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_departamentos'))
@app.route('/departamentos/excluir/<int:dep_id>', methods=['POST'])
def excluir_departamento(dep_id):
    res = db.delete_departamento(dep_id)
    if res == "EM_USO_FUNCIONARIO": flash('Departamento associado a funcionário(s).', 'warning')
    elif res == "EM_USO_FUNCAO": flash('Departamento associado a função(ões) na tela de Relações.', 'warning')
    elif res: flash('Departamento excluído!', 'success')
    else: flash('Erro ao excluir.', 'danger')
    return redirect(url_for('listar_departamentos'))

# --- Rotas para Funções ---
@app.route('/funcoes')
def listar_funcoes():
    return render_template('funcoes.html', funcoes=db.get_all_funcoes() or [])
@app.route('/funcoes/json/<int:func_id>')
def get_funcao_json(func_id):
    f = db.get_funcao_by_id(func_id)
    if f: return jsonify(dict(f))
    return jsonify({"error": "Função não encontrada"}), 404
@app.route('/funcoes/salvar', methods=['POST'])
@app.route('/funcoes/salvar/<int:func_id>', methods=['POST'])
def salvar_funcao(func_id=None):
    nome = request.form.get('nome_funcao')
    if not nome: flash('O nome da função é obrigatório.', 'danger')
    else:
        try:
            if func_id:
                if db.update_funcao(func_id, nome): flash('Função atualizada!', 'success')
            else:
                if db.add_funcao(nome): flash('Função adicionada!', 'success')
        except sqlite3.IntegrityError: flash(f"Erro: A função '{nome}' já existe.", 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_funcoes'))
@app.route('/funcoes/excluir/<int:func_id>', methods=['POST'])
def excluir_funcao(func_id):
    res = db.delete_funcao(func_id)
    if res == "EM_USO_FUNCIONARIO": flash('Função associada a funcionário(s).', 'warning')
    elif res == "EM_USO_DEPARTAMENTO": flash('Função associada a departamento(s) na tela de Relações.', 'warning')
    elif res: flash('Função excluída!', 'success')
    else: flash('Erro ao excluir.', 'danger')
    return redirect(url_for('listar_funcoes'))

# --- Rotas para Funcionários ---
@app.route('/funcionarios')
def listar_funcionarios():
    search = request.args.get('search', '')
    funcionarios = db.search_funcionarios(search) if search else db.get_all_funcionarios()
    return render_template('funcionarios.html', funcionarios=funcionarios or [], search_query=search, departamentos=db.get_all_departamentos() or [], funcoes=db.get_all_funcoes() or [], setores=['Produtivo', 'Administrativo', 'Outro'])
@app.route('/funcionarios/json/<int:func_id>')
def get_funcionario_json(func_id):
    f = db.get_funcionario_by_id(func_id)
    if f: return jsonify(dict(f))
    return jsonify({"error": "Funcionário não encontrado"}), 404
@app.route('/funcionarios/salvar', methods=['POST'])
@app.route('/funcionarios/salvar/<int:func_id>', methods=['POST'])
def salvar_funcionario(func_id=None):
    data = {'nome_completo': request.form.get('nome_completo'), 'cpf': request.form.get('cpf'), 'rg': request.form.get('rg'), 'ctps': request.form.get('ctps'), 'serie': request.form.get('serie'), 'pis': request.form.get('pis'), 'departamento_id': request.form.get('departamento_id_modal'), 'funcao_id': request.form.get('funcao_id_modal'), 'setor': request.form.get('setor_modal'), 'data_admissao': format_date_for_db(request.form.get('data_admissao')), 'data_treinamento': format_date_for_db(request.form.get('data_treinamento'))}
    if not data['nome_completo']: flash('Nome completo é obrigatório.', 'danger')
    else:
        try:
            if func_id:
                if db.update_funcionario(func_id, data): flash('Funcionário atualizado!', 'success')
            else:
                if db.add_funcionario(data): flash('Funcionário adicionado!', 'success')
        except sqlite3.IntegrityError: flash('Erro: CPF duplicado ou conflito.', 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_funcionarios'))
@app.route('/funcionarios/excluir/<int:func_id>', methods=['POST'])
def excluir_funcionario(func_id):
    if db.delete_funcionario(func_id): flash('Funcionário excluído!', 'success')
    else: flash('Erro ao excluir.', 'danger')
    return redirect(url_for('listar_funcionarios'))

# --- Rotas para EPIs ---
@app.route('/epis')
def listar_epis():
    search = request.args.get('search', '')
    epis = db.search_epis(search) if search else db.get_all_epis()
    return render_template('epis.html', epis_lista=epis or [], search_query=search, unidades_periodicidade=['dias', 'semanas', 'meses', 'anos'], meses_do_ano=[{"valor": str(i), "nome": datetime.date(2000, i, 1).strftime('%B').capitalize()} for i in range(1, 13)])
@app.route('/epis/json/<int:epi_id>')
def get_epi_json(epi_id):
    epi = db.get_epi_by_id(epi_id)
    if epi: return jsonify(epi)
    return jsonify({"error": "EPI não encontrado"}), 404
@app.route('/epis/salvar', methods=['POST'])
@app.route('/epis/salvar/<int:epi_id>', methods=['POST'])
def salvar_epi(epi_id=None):
    val_str = request.form.get('periodicidade_valor')
    data = {'nome': request.form.get('nome_epi'), 'marca': request.form.get('marca_epi'), 'ca': request.form.get('ca_epi'), 'observacoes': request.form.get('observacoes_epi'), 'periodicidade_valor': int(val_str) if val_str and val_str.isdigit() else None, 'periodicidade_unidade': request.form.get('periodicidade_unidade_epi'), 'meses_troca': request.form.getlist('meses_troca_epi[]')}
    if not data['nome']: flash('Nome do EPI é obrigatório.', 'danger')
    else:
        try:
            if epi_id:
                if db.update_epi(epi_id, data): flash('EPI atualizado!', 'success')
            else:
                if db.add_epi(data): flash('EPI adicionado!', 'success')
        except sqlite3.IntegrityError: flash('Erro: Conflito ao salvar EPI.', 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_epis'))
@app.route('/epis/excluir/<int:epi_id>', methods=['POST'])
def excluir_epi(epi_id):
    if db.delete_epi(epi_id): flash('EPI excluído!', 'success')
    else: flash('Erro ao excluir.', 'danger')
    return redirect(url_for('listar_epis'))

# --- Rotas para Fornecedores ---
@app.route('/fornecedores')
def listar_fornecedores():
    search = request.args.get('search', '')
    fornecedores = db.search_fornecedores(search) if search else db.get_all_fornecedores()
    return render_template('fornecedores.html', fornecedores_lista=fornecedores or [], search_query=search)
@app.route('/fornecedores/json/<int:fornecedor_id>')
def get_fornecedor_json(fornecedor_id):
    f = db.get_fornecedor_by_id(fornecedor_id)
    if f: return jsonify(dict(f))
    return jsonify({"error": "Fornecedor não encontrado"}), 404
@app.route('/consultar_cnpj/<string:cnpj>')
def consultar_cnpj_api(cnpj):
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) != 14: return jsonify({"error": "CNPJ inválido."}), 400
    existente = db.get_fornecedor_by_cnpj(cnpj_limpo)
    if existente: return jsonify({"data": dict(existente), "exists_in_db": True})
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=10)
        r.raise_for_status()
        data_api = r.json()
        dados = {"cnpj": data_api.get("cnpj"), "razao_social": data_api.get("razao_social"), "nome_fantasia": data_api.get("nome_fantasia"), "logradouro": data_api.get("logradouro"), "numero": data_api.get("numero"), "complemento": data_api.get("complemento"), "bairro": data_api.get("bairro"), "cep": data_api.get("cep"), "municipio": data_api.get("municipio"), "uf": data_api.get("uf"), "telefone": data_api.get("ddd_telefone_1"), "email": data_api.get("email"), "exists_in_db": False}
        return jsonify({"data": dados, "exists_in_db": False})
    except requests.exceptions.Timeout: return jsonify({"error": "Timeout BrasilAPI."}), 504
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404: return jsonify({"error": "CNPJ não encontrado na BrasilAPI."}), 404
        return jsonify({"error": f"Erro BrasilAPI: {e.response.status_code}."}), e.response.status_code
    except Exception as e: return jsonify({"error": f"Erro: {str(e)}"}), 500
@app.route('/fornecedores/salvar', methods=['POST'])
@app.route('/fornecedores/salvar/<int:fornecedor_id>', methods=['POST'])
def salvar_fornecedor(fornecedor_id=None):
    data = {'cnpj': re.sub(r'\D', '', request.form.get('cnpj_fornecedor') or ""), 'razao_social': request.form.get('razao_social_fornecedor'), 'nome_fantasia': request.form.get('nome_fantasia_fornecedor'), 'logradouro': request.form.get('logradouro_fornecedor'), 'numero': request.form.get('numero_fornecedor'), 'complemento': request.form.get('complemento_fornecedor'), 'bairro': request.form.get('bairro_fornecedor'), 'cep': re.sub(r'\D', '', request.form.get('cep_fornecedor') or ""), 'municipio': request.form.get('municipio_fornecedor'), 'uf': request.form.get('uf_fornecedor'), 'telefone': request.form.get('telefone_fornecedor'), 'email': request.form.get('email_fornecedor'), 'observacoes': request.form.get('observacoes_fornecedor')}
    if not data['cnpj'] or len(data['cnpj']) != 14: flash('CNPJ inválido.', 'danger')
    elif not data['razao_social']: flash('Razão Social obrigatória.', 'danger')
    else:
        try:
            if fornecedor_id:
                if db.update_fornecedor(fornecedor_id, data): flash('Fornecedor atualizado!', 'success')
            else:
                if db.get_fornecedor_by_cnpj(data['cnpj']): flash(f"Erro: CNPJ {format_cnpj_for_display(data['cnpj'])} já cadastrado.", 'danger')
                elif db.add_fornecedor(data): flash('Fornecedor adicionado!', 'success')
        except sqlite3.IntegrityError: flash(f"Erro: CNPJ '{format_cnpj_for_display(data['cnpj'])}' já cadastrado.", 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_fornecedores'))
@app.route('/fornecedores/excluir/<int:fornecedor_id>', methods=['POST'])
def excluir_fornecedor(fornecedor_id):
    if db.delete_fornecedor(fornecedor_id): flash('Fornecedor excluído!', 'success')
    else: flash('Erro ao excluir.', 'danger')
    return redirect(url_for('listar_fornecedores'))

# --- Rotas para Relação Departamento x Função ---
@app.route('/relacionar_departamento_funcao', methods=['GET'])
def relacionar_departamento_funcao_view():
    departamentos = db.get_all_departamentos()
    funcoes = db.get_all_funcoes() # Carrega todas as funções
    
    # Para depuração: verificar se as funções estão sendo carregadas
    # print("Funções carregadas para o template:", funcoes) 
    
    return render_template('relacionar_departamento_funcao.html',
                           departamentos=departamentos or [],
                           funcoes_todas=funcoes or []) # Passa para o template

@app.route('/relacionar_departamento_funcao/funcoes_associadas/<int:departamento_id>', methods=['GET'])
def get_funcoes_associadas_a_departamento_json(departamento_id):
    funcoes_ids_associadas = db.get_funcoes_by_departamento_id(departamento_id)
    return jsonify(funcoes_ids_associadas)

@app.route('/relacionar_departamento_funcao/salvar', methods=['POST'])
def salvar_relacao_departamento_funcao():
    departamento_id = request.form.get('departamento_id_relacao')
    funcoes_selecionadas_ids = request.form.getlist('funcoes_associadas[]') 
    
    if not departamento_id:
        flash('Selecione um departamento para atualizar as relações.', 'danger')
        return redirect(url_for('relacionar_departamento_funcao_view'))

    funcoes_selecionadas_ids = [int(id_str) for id_str in funcoes_selecionadas_ids if id_str.isdigit()]

    if db.update_funcoes_for_departamento(int(departamento_id), funcoes_selecionadas_ids):
        flash('Relações entre departamento e funções atualizadas com sucesso!', 'success')
    else:
        flash('Erro ao atualizar relações.', 'danger')
    return redirect(url_for('relacionar_departamento_funcao_view', departamento_id_focus=departamento_id))


if __name__ == '__main__':
    static_dir = os.path.join(BASE_DIR, 'static')
    if not os.path.exists(static_dir): os.makedirs(static_dir)
    templates_dir = os.path.join(BASE_DIR, 'templates')
    if not os.path.exists(templates_dir): os.makedirs(templates_dir)
    css_file_path = os.path.join(static_dir, 'style.css')
    if not os.path.exists(css_file_path):
        with open(css_file_path, 'w') as f: f.write("/* Estilos CSS */")
        print(f"Ficheiro '{css_file_path}' criado.")
    app.run(debug=True)
