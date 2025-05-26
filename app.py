import os
import datetime
import sqlite3
import json # Para lidar com a lista de meses_troca no request
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

app.jinja_env.filters['format_date_display'] = format_date_for_display

# --- Rotas Principais ---
@app.route('/')
def dashboard():
    total_funcionarios = len(db.get_all_funcionarios() or [])
    total_departamentos = len(db.get_all_departamentos() or [])
    total_funcoes = len(db.get_all_funcoes() or [])
    total_epis = len(db.get_all_epis() or []) # Adicionado
    return render_template('dashboard.html',
                           total_funcionarios=total_funcionarios,
                           total_departamentos=total_departamentos,
                           total_funcoes=total_funcoes,
                           total_epis=total_epis) # Passado para o template

# --- Rotas para Departamentos (sem alterações nesta etapa) ---
@app.route('/departamentos')
def listar_departamentos():
    departamentos = db.get_all_departamentos()
    return render_template('departamentos.html', departamentos=departamentos or [])

@app.route('/departamentos/json/<int:dep_id>')
def get_departamento_json(dep_id):
    departamento = db.get_departamento_by_id(dep_id)
    if departamento:
        return jsonify(dict(departamento))
    return jsonify({"error": "Departamento não encontrado"}), 404

@app.route('/departamentos/salvar', methods=['POST'])
@app.route('/departamentos/salvar/<int:dep_id>', methods=['POST'])
def salvar_departamento(dep_id=None):
    nome = request.form.get('nome_departamento')
    if not nome:
        flash('O nome do departamento é obrigatório.', 'danger')
        return redirect(url_for('listar_departamentos'))
    try:
        if dep_id:
            if db.update_departamento(dep_id, nome):
                flash('Departamento atualizado com sucesso!', 'success')
            else:
                flash('Erro ao atualizar departamento.', 'danger')
        else:
            if db.add_departamento(nome):
                flash('Departamento adicionado com sucesso!', 'success')
            else:
                flash('Erro ao adicionar departamento. Verifique se já existe.', 'danger')
    except sqlite3.IntegrityError:
        flash(f"Erro: O departamento '{nome}' já existe ou ocorreu um conflito.", 'danger')
    except Exception as e:
        flash(f'Erro ao salvar departamento: {str(e)}', 'danger')
    return redirect(url_for('listar_departamentos'))

@app.route('/departamentos/excluir/<int:dep_id>', methods=['POST'])
def excluir_departamento(dep_id):
    resultado = db.delete_departamento(dep_id)
    if resultado == "EM_USO":
        flash('Não é possível excluir o departamento, pois ele está associado a funcionários.', 'warning')
    elif resultado:
        flash('Departamento excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir departamento.', 'danger')
    return redirect(url_for('listar_departamentos'))

# --- Rotas para Funções (sem alterações nesta etapa) ---
@app.route('/funcoes')
def listar_funcoes():
    funcoes = db.get_all_funcoes()
    return render_template('funcoes.html', funcoes=funcoes or [])

@app.route('/funcoes/json/<int:func_id>')
def get_funcao_json(func_id):
    funcao = db.get_funcao_by_id(func_id)
    if funcao:
        return jsonify(dict(funcao))
    return jsonify({"error": "Função não encontrada"}), 404

@app.route('/funcoes/salvar', methods=['POST'])
@app.route('/funcoes/salvar/<int:func_id>', methods=['POST'])
def salvar_funcao(func_id=None):
    nome = request.form.get('nome_funcao')
    if not nome:
        flash('O nome da função é obrigatório.', 'danger')
        return redirect(url_for('listar_funcoes'))
    try:
        if func_id:
            if db.update_funcao(func_id, nome):
                flash('Função atualizada com sucesso!', 'success')
            else:
                flash('Erro ao atualizar função.', 'danger')
        else:
            if db.add_funcao(nome):
                flash('Função adicionada com sucesso!', 'success')
            else:
                flash('Erro ao adicionar função. Verifique se já existe.', 'danger')
    except sqlite3.IntegrityError:
        flash(f"Erro: A função '{nome}' já existe ou ocorreu um conflito.", 'danger')
    except Exception as e:
        flash(f'Erro ao salvar função: {str(e)}', 'danger')
    return redirect(url_for('listar_funcoes'))

@app.route('/funcoes/excluir/<int:func_id>', methods=['POST'])
def excluir_funcao(func_id):
    resultado = db.delete_funcao(func_id)
    if resultado == "EM_USO":
        flash('Não é possível excluir a função, pois ela está associada a funcionários.', 'warning')
    elif resultado:
        flash('Função excluída com sucesso!', 'success')
    else:
        flash('Erro ao excluir função.', 'danger')
    return redirect(url_for('listar_funcoes'))

# --- Rotas para Funcionários (sem alterações nesta etapa) ---
@app.route('/funcionarios')
def listar_funcionarios():
    search_query = request.args.get('search', '')
    if search_query:
        funcionarios = db.search_funcionarios(search_query)
    else:
        funcionarios = db.get_all_funcionarios()
    departamentos = db.get_all_departamentos()
    funcoes = db.get_all_funcoes()
    setores = ['Produtivo', 'Administrativo', 'Outro']
    return render_template('funcionarios.html',
                           funcionarios=funcionarios or [],
                           search_query=search_query,
                           departamentos=departamentos or [],
                           funcoes=funcoes or [],
                           setores=setores)

@app.route('/funcionarios/json/<int:func_id>')
def get_funcionario_json(func_id):
    funcionario = db.get_funcionario_by_id(func_id)
    if funcionario:
        func_dict = dict(funcionario)
        func_dict['data_admissao'] = func_dict['data_admissao']
        func_dict['data_treinamento'] = func_dict['data_treinamento']
        return jsonify(func_dict)
    return jsonify({"error": "Funcionário não encontrado"}), 404

@app.route('/funcionarios/salvar', methods=['POST'])
@app.route('/funcionarios/salvar/<int:func_id>', methods=['POST'])
def salvar_funcionario(func_id=None):
    dados_funcionario = {
        'nome_completo': request.form.get('nome_completo'),
        'cpf': request.form.get('cpf'),
        'rg': request.form.get('rg'),
        'ctps': request.form.get('ctps'),
        'serie': request.form.get('serie'),
        'pis': request.form.get('pis'),
        'departamento_id': request.form.get('departamento_id_modal') if request.form.get('departamento_id_modal') else None, # Corrigido para pegar do modal
        'funcao_id': request.form.get('funcao_id_modal') if request.form.get('funcao_id_modal') else None, # Corrigido
        'setor': request.form.get('setor_modal'), # Corrigido
        'data_admissao': format_date_for_db(request.form.get('data_admissao')),
        'data_treinamento': format_date_for_db(request.form.get('data_treinamento'))
    }
    if not dados_funcionario['nome_completo']:
        flash('O nome completo do funcionário é obrigatório.', 'danger')
    else:
        try:
            if func_id:
                if db.update_funcionario(func_id, dados_funcionario):
                    flash('Funcionário atualizado com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar funcionário.', 'danger')
            else:
                if db.add_funcionario(dados_funcionario):
                    flash('Funcionário adicionado com sucesso!', 'success')
                else:
                    flash('Erro ao adicionar funcionário.', 'danger')
        except sqlite3.IntegrityError:
             flash('Erro: CPF já cadastrado ou outro conflito de dados únicos.', 'danger')
        except Exception as e:
            flash(f'Erro ao salvar funcionário: {str(e)}', 'danger')
    return redirect(url_for('listar_funcionarios'))

@app.route('/funcionarios/excluir/<int:func_id>', methods=['POST'])
def excluir_funcionario(func_id):
    if db.delete_funcionario(func_id):
        flash('Funcionário excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir funcionário.', 'danger')
    return redirect(url_for('listar_funcionarios'))

# --- Rotas para EPIs ---
@app.route('/epis')
def listar_epis():
    search_query = request.args.get('search', '')
    if search_query:
        epis_lista = db.search_epis(search_query)
    else:
        epis_lista = db.get_all_epis()
    
    # Para o formulário no modal
    unidades_periodicidade = ['dias', 'semanas', 'meses', 'anos']
    meses_do_ano = [
        {"valor": "1", "nome": "Janeiro"}, {"valor": "2", "nome": "Fevereiro"},
        {"valor": "3", "nome": "Março"}, {"valor": "4", "nome": "Abril"},
        {"valor": "5", "nome": "Maio"}, {"valor": "6", "nome": "Junho"},
        {"valor": "7", "nome": "Julho"}, {"valor": "8", "nome": "Agosto"},
        {"valor": "9", "nome": "Setembro"}, {"valor": "10", "nome": "Outubro"},
        {"valor": "11", "nome": "Novembro"}, {"valor": "12", "nome": "Dezembro"}
    ]

    return render_template('epis.html',
                           epis_lista=epis_lista or [],
                           search_query=search_query,
                           unidades_periodicidade=unidades_periodicidade,
                           meses_do_ano=meses_do_ano)

@app.route('/epis/json/<int:epi_id>')
def get_epi_json(epi_id):
    epi = db.get_epi_by_id(epi_id)
    if epi:
        return jsonify(epi) # epi já é um dict com meses_troca como lista
    return jsonify({"error": "EPI não encontrado"}), 404

@app.route('/epis/salvar', methods=['POST'])
@app.route('/epis/salvar/<int:epi_id>', methods=['POST'])
def salvar_epi(epi_id=None):
    try:
        periodicidade_valor_str = request.form.get('periodicidade_valor')
        dados_epi = {
            'nome': request.form.get('nome_epi'), # Nomes dos campos do modal de EPI
            'marca': request.form.get('marca_epi'),
            'ca': request.form.get('ca_epi'),
            'periodicidade_valor': int(periodicidade_valor_str) if periodicidade_valor_str and periodicidade_valor_str.isdigit() else None,
            'periodicidade_unidade': request.form.get('periodicidade_unidade_epi'),
            'meses_troca': request.form.getlist('meses_troca_epi[]'), # Pega lista de meses do select múltiplo
            'observacoes': request.form.get('observacoes_epi')
        }
    except Exception as e:
        flash(f"Erro ao processar dados do formulário: {str(e)}", "danger")
        return redirect(url_for('listar_epis'))


    if not dados_epi['nome']:
        flash('O nome do EPI é obrigatório.', 'danger')
    else:
        try:
            if epi_id: # Edição
                if db.update_epi(epi_id, dados_epi):
                    flash('EPI atualizado com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar EPI.', 'danger')
            else: # Novo
                if db.add_epi(dados_epi):
                    flash('EPI adicionado com sucesso!', 'success')
                else:
                    flash('Erro ao adicionar EPI.', 'danger')
        except sqlite3.IntegrityError:
             flash('Erro: Conflito de dados ao salvar o EPI (ex: CA duplicado, se for único).', 'danger')
        except Exception as e:
            flash(f'Erro ao salvar EPI: {str(e)}', 'danger')
    return redirect(url_for('listar_epis'))

@app.route('/epis/excluir/<int:epi_id>', methods=['POST'])
def excluir_epi(epi_id):
    if db.delete_epi(epi_id):
        flash('EPI excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir EPI.', 'danger')
    return redirect(url_for('listar_epis'))


if __name__ == '__main__':
    static_dir = os.path.join(BASE_DIR, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    templates_dir = os.path.join(BASE_DIR, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    css_file_path = os.path.join(static_dir, 'style.css')
    if not os.path.exists(css_file_path):
        with open(css_file_path, 'w') as f:
            f.write("/* Estilos CSS básicos aqui */\nbody { font-family: sans-serif; margin: 20px; }\n.flash-messages .alert { margin-top: 15px; }")
        print(f"Ficheiro '{css_file_path}' criado.")
    app.run(debug=True)
