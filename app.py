import os
import datetime
import sqlite3
import json
import re # Importado para limpar o CNPJ
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
    if not date_str_iso:
        return ""
    try:
        dt_obj = datetime.datetime.strptime(str(date_str_iso), '%Y-%m-%d')
        return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        return str(date_str_iso)

def format_date_for_db(date_str_display):
    if not date_str_display:
        return None
    try:
        dt_obj = datetime.datetime.strptime(str(date_str_display), '%d/%m/%Y')
        return dt_obj.strftime('%Y-%m-%d')
    except ValueError:
        if len(str(date_str_display).split('-')) == 3:
            return str(date_str_display)
        return None

def format_cnpj_for_display(cnpj_str):
    if not cnpj_str:
        return ""
    # Remove todos os caracteres não numéricos
    cnpj_limpo = re.sub(r'\D', '', str(cnpj_str))
    if len(cnpj_limpo) == 14:
        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    return cnpj_str # Retorna o original se não tiver 14 dígitos

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

# --- Rotas para Departamentos (sem alterações) ---
@app.route('/departamentos')
def listar_departamentos():
    departamentos = db.get_all_departamentos()
    return render_template('departamentos.html', departamentos=departamentos or [])

@app.route('/departamentos/json/<int:dep_id>')
def get_departamento_json(dep_id):
    departamento = db.get_departamento_by_id(dep_id)
    if departamento: return jsonify(dict(departamento))
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
                else: flash('Erro ao atualizar departamento.', 'danger')
            else:
                if db.add_departamento(nome): flash('Departamento adicionado!', 'success')
                else: flash('Erro ao adicionar. Verifique se já existe.', 'danger')
        except sqlite3.IntegrityError: flash(f"Erro: O departamento '{nome}' já existe.", 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_departamentos'))

@app.route('/departamentos/excluir/<int:dep_id>', methods=['POST'])
def excluir_departamento(dep_id):
    res = db.delete_departamento(dep_id)
    if res == "EM_USO": flash('Departamento em uso, não pode ser excluído.', 'warning')
    elif res: flash('Departamento excluído!', 'success')
    else: flash('Erro ao excluir departamento.', 'danger')
    return redirect(url_for('listar_departamentos'))

# --- Rotas para Funções (sem alterações) ---
@app.route('/funcoes')
def listar_funcoes():
    funcoes = db.get_all_funcoes()
    return render_template('funcoes.html', funcoes=funcoes or [])

@app.route('/funcoes/json/<int:func_id>')
def get_funcao_json(func_id):
    funcao = db.get_funcao_by_id(func_id)
    if funcao: return jsonify(dict(funcao))
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
                else: flash('Erro ao atualizar função.', 'danger')
            else:
                if db.add_funcao(nome): flash('Função adicionada!', 'success')
                else: flash('Erro ao adicionar. Verifique se já existe.', 'danger')
        except sqlite3.IntegrityError: flash(f"Erro: A função '{nome}' já existe.", 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_funcoes'))

@app.route('/funcoes/excluir/<int:func_id>', methods=['POST'])
def excluir_funcao(func_id):
    res = db.delete_funcao(func_id)
    if res == "EM_USO": flash('Função em uso, não pode ser excluída.', 'warning')
    elif res: flash('Função excluída!', 'success')
    else: flash('Erro ao excluir função.', 'danger')
    return redirect(url_for('listar_funcoes'))

# --- Rotas para Funcionários (sem alterações) ---
@app.route('/funcionarios')
def listar_funcionarios():
    search = request.args.get('search', '')
    funcionarios = db.search_funcionarios(search) if search else db.get_all_funcionarios()
    return render_template('funcionarios.html',
                           funcionarios=funcionarios or [],
                           search_query=search,
                           departamentos=db.get_all_departamentos() or [],
                           funcoes=db.get_all_funcoes() or [],
                           setores=['Produtivo', 'Administrativo', 'Outro'])

@app.route('/funcionarios/json/<int:func_id>')
def get_funcionario_json(func_id):
    f = db.get_funcionario_by_id(func_id)
    if f: return jsonify(dict(f))
    return jsonify({"error": "Funcionário não encontrado"}), 404

@app.route('/funcionarios/salvar', methods=['POST'])
@app.route('/funcionarios/salvar/<int:func_id>', methods=['POST'])
def salvar_funcionario(func_id=None):
    data = {
        'nome_completo': request.form.get('nome_completo'), 'cpf': request.form.get('cpf'),
        'rg': request.form.get('rg'), 'ctps': request.form.get('ctps'), 'serie': request.form.get('serie'),
        'pis': request.form.get('pis'), 'departamento_id': request.form.get('departamento_id_modal'),
        'funcao_id': request.form.get('funcao_id_modal'), 'setor': request.form.get('setor_modal'),
        'data_admissao': format_date_for_db(request.form.get('data_admissao')),
        'data_treinamento': format_date_for_db(request.form.get('data_treinamento'))
    }
    if not data['nome_completo']: flash('Nome completo é obrigatório.', 'danger')
    else:
        try:
            if func_id:
                if db.update_funcionario(func_id, data): flash('Funcionário atualizado!', 'success')
                else: flash('Erro ao atualizar funcionário.', 'danger')
            else:
                if db.add_funcionario(data): flash('Funcionário adicionado!', 'success')
                else: flash('Erro ao adicionar funcionário.', 'danger')
        except sqlite3.IntegrityError: flash('Erro: CPF duplicado ou conflito de dados.', 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_funcionarios'))

@app.route('/funcionarios/excluir/<int:func_id>', methods=['POST'])
def excluir_funcionario(func_id):
    if db.delete_funcionario(func_id): flash('Funcionário excluído!', 'success')
    else: flash('Erro ao excluir funcionário.', 'danger')
    return redirect(url_for('listar_funcionarios'))

# --- Rotas para EPIs (sem alterações) ---
@app.route('/epis')
def listar_epis():
    search = request.args.get('search', '')
    epis = db.search_epis(search) if search else db.get_all_epis()
    return render_template('epis.html',
                           epis_lista=epis or [],
                           search_query=search,
                           unidades_periodicidade=['dias', 'semanas', 'meses', 'anos'],
                           meses_do_ano=[{"valor": str(i), "nome": datetime.date(2000, i, 1).strftime('%B').capitalize()} for i in range(1, 13)])

@app.route('/epis/json/<int:epi_id>')
def get_epi_json(epi_id):
    epi = db.get_epi_by_id(epi_id)
    if epi: return jsonify(epi)
    return jsonify({"error": "EPI não encontrado"}), 404

@app.route('/epis/salvar', methods=['POST'])
@app.route('/epis/salvar/<int:epi_id>', methods=['POST'])
def salvar_epi(epi_id=None):
    val_str = request.form.get('periodicidade_valor')
    data = {
        'nome': request.form.get('nome_epi'), 'marca': request.form.get('marca_epi'),
        'ca': request.form.get('ca_epi'), 'observacoes': request.form.get('observacoes_epi'),
        'periodicidade_valor': int(val_str) if val_str and val_str.isdigit() else None,
        'periodicidade_unidade': request.form.get('periodicidade_unidade_epi'),
        'meses_troca': request.form.getlist('meses_troca_epi[]')
    }
    if not data['nome']: flash('Nome do EPI é obrigatório.', 'danger')
    else:
        try:
            if epi_id:
                if db.update_epi(epi_id, data): flash('EPI atualizado!', 'success')
                else: flash('Erro ao atualizar EPI.', 'danger')
            else:
                if db.add_epi(data): flash('EPI adicionado!', 'success')
                else: flash('Erro ao adicionar EPI.', 'danger')
        except sqlite3.IntegrityError: flash('Erro: Conflito de dados ao salvar EPI.', 'danger')
        except Exception as e: flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('listar_epis'))

@app.route('/epis/excluir/<int:epi_id>', methods=['POST'])
def excluir_epi(epi_id):
    if db.delete_epi(epi_id): flash('EPI excluído!', 'success')
    else: flash('Erro ao excluir EPI.', 'danger')
    return redirect(url_for('listar_epis'))

# --- Rotas para Fornecedores ---
@app.route('/fornecedores')
def listar_fornecedores():
    search_query = request.args.get('search', '')
    if search_query:
        fornecedores_lista = db.search_fornecedores(search_query)
    else:
        fornecedores_lista = db.get_all_fornecedores()
    return render_template('fornecedores.html',
                           fornecedores_lista=fornecedores_lista or [],
                           search_query=search_query)

@app.route('/fornecedores/json/<int:fornecedor_id>')
def get_fornecedor_json(fornecedor_id):
    fornecedor = db.get_fornecedor_by_id(fornecedor_id)
    if fornecedor:
        # Formatar CNPJ para exibição no modal se necessário (já formatado na tabela)
        forn_dict = dict(fornecedor)
        # forn_dict['cnpj'] = format_cnpj_for_display(forn_dict['cnpj']) # Opcional, se quiser formatado no input também
        return jsonify(forn_dict)
    return jsonify({"error": "Fornecedor não encontrado"}), 404

@app.route('/consultar_cnpj/<string:cnpj>')
def consultar_cnpj_api(cnpj):
    cnpj_limpo = re.sub(r'\D', '', cnpj) # Usar re.sub para limpar
    if len(cnpj_limpo) != 14:
        return jsonify({"error": "CNPJ inválido. Deve conter 14 dígitos."}), 400

    fornecedor_existente = db.get_fornecedor_by_cnpj(cnpj_limpo)
    if fornecedor_existente:
        return jsonify({"data": dict(fornecedor_existente), "exists_in_db": True})

    try:
        response = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=10)
        response.raise_for_status()
        data = response.json()
        dados_formatados = {
            "cnpj": data.get("cnpj"), "razao_social": data.get("razao_social"),
            "nome_fantasia": data.get("nome_fantasia"), "logradouro": data.get("logradouro"),
            "numero": data.get("numero"), "complemento": data.get("complemento"),
            "bairro": data.get("bairro"), "cep": data.get("cep"),
            "municipio": data.get("municipio"), "uf": data.get("uf"),
            "telefone": data.get("ddd_telefone_1") or data.get("ddd_telefone_2"),
            "email": data.get("email"), "exists_in_db": False
        }
        return jsonify({"data": dados_formatados, "exists_in_db": False})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout ao consultar BrasilAPI."}), 504
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
             return jsonify({"error": f"CNPJ não encontrado na BrasilAPI."}), 404
        return jsonify({"error": f"Erro na BrasilAPI: {e.response.status_code}."}), e.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão ao consultar BrasilAPI."}), 500
    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500


@app.route('/fornecedores/salvar', methods=['POST'])
@app.route('/fornecedores/salvar/<int:fornecedor_id>', methods=['POST'])
def salvar_fornecedor(fornecedor_id=None):
    dados_fornecedor = {
        'cnpj': re.sub(r'\D', '', request.form.get('cnpj_fornecedor') or ""),
        'razao_social': request.form.get('razao_social_fornecedor'),
        'nome_fantasia': request.form.get('nome_fantasia_fornecedor'),
        'logradouro': request.form.get('logradouro_fornecedor'),
        'numero': request.form.get('numero_fornecedor'),
        'complemento': request.form.get('complemento_fornecedor'),
        'bairro': request.form.get('bairro_fornecedor'),
        'cep': re.sub(r'\D', '', request.form.get('cep_fornecedor') or ""), # Limpar CEP também
        'municipio': request.form.get('municipio_fornecedor'),
        'uf': request.form.get('uf_fornecedor'),
        'telefone': request.form.get('telefone_fornecedor'),
        'email': request.form.get('email_fornecedor'),
        'observacoes': request.form.get('observacoes_fornecedor')
    }

    if not dados_fornecedor['cnpj'] or len(dados_fornecedor['cnpj']) != 14 :
        flash('CNPJ é obrigatório e deve conter 14 dígitos.', 'danger')
    elif not dados_fornecedor['razao_social']:
        flash('Razão Social é obrigatória.', 'danger')
    else:
        try:
            if fornecedor_id:
                if db.update_fornecedor(fornecedor_id, dados_fornecedor):
                    flash('Fornecedor atualizado com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar fornecedor.', 'danger')
            else:
                existente = db.get_fornecedor_by_cnpj(dados_fornecedor['cnpj'])
                if existente:
                    flash(f"Erro: O CNPJ {format_cnpj_for_display(dados_fornecedor['cnpj'])} já está cadastrado para '{existente['razao_social']}'.", 'danger')
                elif db.add_fornecedor(dados_fornecedor):
                    flash('Fornecedor adicionado com sucesso!', 'success')
                else:
                    flash('Erro ao adicionar fornecedor.', 'danger')
        except sqlite3.IntegrityError:
             flash(f"Erro: O CNPJ '{format_cnpj_for_display(dados_fornecedor['cnpj'])}' já está cadastrado ou ocorreu um conflito de dados.", 'danger')
        except Exception as e:
            flash(f'Erro ao salvar fornecedor: {str(e)}', 'danger')
    return redirect(url_for('listar_fornecedores'))

@app.route('/fornecedores/excluir/<int:fornecedor_id>', methods=['POST'])
def excluir_fornecedor(fornecedor_id):
    if db.delete_fornecedor(fornecedor_id):
        flash('Fornecedor excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir fornecedor.', 'danger')
    return redirect(url_for('listar_fornecedores'))


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
