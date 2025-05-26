import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import DatabaseManager # Importa a classe DatabaseManager

# --- Configurações Globais ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = "controle_epis.db"
DB_FULL_PATH = os.path.join(BASE_DIR, DB_NAME)

# --- Inicialização do Flask App ---
app = Flask(__name__)
app.secret_key = os.urandom(24) # Chave secreta para flash messages

# --- Instância do DatabaseManager ---
db = DatabaseManager(DB_FULL_PATH)

# --- Context Processor para datas ---
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now(datetime.timezone.utc)}

def format_date_for_display(date_str_iso):
    if not date_str_iso:
        return ""
    try:
        # Tenta converter de YYYY-MM-DD para DD/MM/YYYY
        dt_obj = datetime.datetime.strptime(str(date_str_iso), '%Y-%m-%d')
        return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        return str(date_str_iso) # Retorna como está se não for o formato esperado

def format_date_for_db(date_str_display):
    if not date_str_display:
        return None
    try:
        # Tenta converter de DD/MM/YYYY para YYYY-MM-DD
        dt_obj = datetime.datetime.strptime(str(date_str_display), '%d/%m/%Y')
        return dt_obj.strftime('%Y-%m-%d')
    except ValueError:
        # Se já estiver no formato do DB ou for inválido, tenta retornar como está ou None
        if len(str(date_str_display).split('-')) == 3: # Simples checagem se parece YYYY-MM-DD
            return str(date_str_display)
        return None


app.jinja_env.filters['format_date_display'] = format_date_for_display

# --- Rotas Principais ---
@app.route('/')
def dashboard():
    # Futuramente, buscar estatísticas do banco
    total_funcionarios = len(db.get_all_funcionarios() or [])
    return render_template('dashboard.html', total_funcionarios=total_funcionarios)

# --- Rotas para Departamentos ---
@app.route('/departamentos')
def listar_departamentos():
    departamentos = db.get_all_departamentos()
    return render_template('departamentos.html', departamentos=departamentos or [])

@app.route('/departamentos/novo', methods=['GET', 'POST'])
def novo_departamento():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if not nome:
            flash('O nome do departamento é obrigatório.', 'danger')
        else:
            try:
                if db.add_departamento(nome):
                    flash('Departamento adicionado com sucesso!', 'success')
                    return redirect(url_for('listar_departamentos'))
                else:
                    flash('Erro ao adicionar departamento. Verifique se já existe.', 'danger')
            except sqlite3.IntegrityError: # Trata o caso de nome UNIQUE
                 flash(f"Erro: O departamento '{nome}' já existe.", 'danger')
            except Exception as e:
                flash(f'Erro ao adicionar departamento: {str(e)}', 'danger')
    return render_template('form_departamento.html', titulo="Novo Departamento", departamento=None)

@app.route('/departamentos/editar/<int:dep_id>', methods=['GET', 'POST'])
def editar_departamento(dep_id):
    departamento = db.get_departamento_by_id(dep_id)
    if not departamento:
        flash('Departamento não encontrado.', 'danger')
        return redirect(url_for('listar_departamentos'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        if not nome:
            flash('O nome do departamento é obrigatório.', 'danger')
        else:
            try:
                if db.update_departamento(dep_id, nome):
                    flash('Departamento atualizado com sucesso!', 'success')
                    return redirect(url_for('listar_departamentos'))
                else:
                    flash('Erro ao atualizar departamento.', 'danger')
            except sqlite3.IntegrityError:
                 flash(f"Erro: O nome '{nome}' já está em uso por outro departamento.", 'danger')
            except Exception as e:
                flash(f'Erro ao atualizar departamento: {str(e)}', 'danger')
    return render_template('form_departamento.html', titulo="Editar Departamento", departamento=departamento)

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

# --- Rotas para Funções ---
@app.route('/funcoes')
def listar_funcoes():
    funcoes = db.get_all_funcoes()
    return render_template('funcoes.html', funcoes=funcoes or [])

@app.route('/funcoes/novo', methods=['GET', 'POST'])
def nova_funcao():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if not nome:
            flash('O nome da função é obrigatório.', 'danger')
        else:
            try:
                if db.add_funcao(nome):
                    flash('Função adicionada com sucesso!', 'success')
                    return redirect(url_for('listar_funcoes'))
                else:
                    flash('Erro ao adicionar função. Verifique se já existe.', 'danger')
            except sqlite3.IntegrityError:
                 flash(f"Erro: A função '{nome}' já existe.", 'danger')
            except Exception as e:
                flash(f'Erro ao adicionar função: {str(e)}', 'danger')
    return render_template('form_funcao.html', titulo="Nova Função", funcao=None)

@app.route('/funcoes/editar/<int:func_id>', methods=['GET', 'POST'])
def editar_funcao(func_id):
    funcao = db.get_funcao_by_id(func_id)
    if not funcao:
        flash('Função não encontrada.', 'danger')
        return redirect(url_for('listar_funcoes'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        if not nome:
            flash('O nome da função é obrigatório.', 'danger')
        else:
            try:
                if db.update_funcao(func_id, nome):
                    flash('Função atualizada com sucesso!', 'success')
                    return redirect(url_for('listar_funcoes'))
                else:
                    flash('Erro ao atualizar função.', 'danger')
            except sqlite3.IntegrityError:
                flash(f"Erro: O nome '{nome}' já está em uso por outra função.", 'danger')
            except Exception as e:
                flash(f'Erro ao atualizar função: {str(e)}', 'danger')
    return render_template('form_funcao.html', titulo="Editar Função", funcao=funcao)

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

# --- Rotas para Funcionários ---
@app.route('/funcionarios')
def listar_funcionarios():
    search_query = request.args.get('search', '')
    if search_query:
        funcionarios = db.search_funcionarios(search_query)
    else:
        funcionarios = db.get_all_funcionarios()
    return render_template('funcionarios.html', funcionarios=funcionarios or [], search_query=search_query)

@app.route('/funcionarios/novo', methods=['GET', 'POST'])
def novo_funcionario():
    departamentos = db.get_all_departamentos()
    funcoes = db.get_all_funcoes()

    if request.method == 'POST':
        dados_funcionario = {
            'nome_completo': request.form.get('nome_completo'),
            'cpf': request.form.get('cpf'),
            'rg': request.form.get('rg'),
            'ctps': request.form.get('ctps'),
            'serie': request.form.get('serie'),
            'pis': request.form.get('pis'),
            'departamento_id': request.form.get('departamento_id') if request.form.get('departamento_id') else None,
            'funcao_id': request.form.get('funcao_id') if request.form.get('funcao_id') else None,
            'setor': request.form.get('setor'),
            'data_admissao': format_date_for_db(request.form.get('data_admissao')),
            'data_treinamento': format_date_for_db(request.form.get('data_treinamento'))
        }
        if not dados_funcionario['nome_completo']:
            flash('O nome completo do funcionário é obrigatório.', 'danger')
        else:
            try:
                if db.add_funcionario(dados_funcionario):
                    flash('Funcionário adicionado com sucesso!', 'success')
                    return redirect(url_for('listar_funcionarios'))
                else:
                    flash('Erro ao adicionar funcionário. Verifique os dados, especialmente o CPF (deve ser único).', 'danger')
            except sqlite3.IntegrityError:
                 flash('Erro: CPF já cadastrado para outro funcionário.', 'danger')
            except Exception as e:
                flash(f'Erro ao adicionar funcionário: {str(e)}', 'danger')
        # Se houver erro, renderiza o formulário novamente com os dados preenchidos
        return render_template('form_funcionario.html',
                               titulo="Novo Funcionário",
                               funcionario=dados_funcionario, # Passa os dados de volta para o form
                               departamentos=departamentos,
                               funcoes=funcoes,
                               setores=['Produtivo', 'Administrativo', 'Outro'])


    return render_template('form_funcionario.html',
                           titulo="Novo Funcionário",
                           funcionario=None,
                           departamentos=departamentos,
                           funcoes=funcoes,
                           setores=['Produtivo', 'Administrativo', 'Outro'])

@app.route('/funcionarios/editar/<int:func_id>', methods=['GET', 'POST'])
def editar_funcionario(func_id):
    funcionario = db.get_funcionario_by_id(func_id)
    if not funcionario:
        flash('Funcionário não encontrado.', 'danger')
        return redirect(url_for('listar_funcionarios'))

    departamentos = db.get_all_departamentos()
    funcoes = db.get_all_funcoes()

    if request.method == 'POST':
        dados_funcionario = {
            'nome_completo': request.form.get('nome_completo'),
            'cpf': request.form.get('cpf'),
            'rg': request.form.get('rg'),
            'ctps': request.form.get('ctps'),
            'serie': request.form.get('serie'),
            'pis': request.form.get('pis'),
            'departamento_id': request.form.get('departamento_id') if request.form.get('departamento_id') else None,
            'funcao_id': request.form.get('funcao_id') if request.form.get('funcao_id') else None,
            'setor': request.form.get('setor'),
            'data_admissao': format_date_for_db(request.form.get('data_admissao')),
            'data_treinamento': format_date_for_db(request.form.get('data_treinamento'))
        }
        if not dados_funcionario['nome_completo']:
            flash('O nome completo do funcionário é obrigatório.', 'danger')
        else:
            try:
                if db.update_funcionario(func_id, dados_funcionario):
                    flash('Funcionário atualizado com sucesso!', 'success')
                    return redirect(url_for('listar_funcionarios'))
                else:
                    flash('Erro ao atualizar funcionário.', 'danger')
            except sqlite3.IntegrityError:
                 flash('Erro: CPF já cadastrado para outro funcionário.', 'danger')
            except Exception as e:
                flash(f'Erro ao atualizar funcionário: {str(e)}', 'danger')
        # Se houver erro, renderiza o formulário novamente com os dados preenchidos
        # É importante converter as datas de volta para o formato de display se houver erro
        funcionario_para_template = dict(funcionario) # Converte sqlite3.Row para dict
        funcionario_para_template.update(dados_funcionario) # Atualiza com os dados do form
        funcionario_para_template['data_admissao'] = request.form.get('data_admissao') # Mantém o formato de entrada
        funcionario_para_template['data_treinamento'] = request.form.get('data_treinamento') # Mantém o formato de entrada

        return render_template('form_funcionario.html',
                               titulo="Editar Funcionário",
                               funcionario=funcionario_para_template,
                               departamentos=departamentos,
                               funcoes=funcoes,
                               setores=['Produtivo', 'Administrativo', 'Outro'])

    # Para o método GET, formata as datas para exibição
    funcionario_edit = dict(funcionario) # Converte sqlite3.Row para dict para poder modificar
    funcionario_edit['data_admissao'] = format_date_for_display(funcionario['data_admissao'])
    funcionario_edit['data_treinamento'] = format_date_for_display(funcionario['data_treinamento'])

    return render_template('form_funcionario.html',
                           titulo="Editar Funcionário",
                           funcionario=funcionario_edit,
                           departamentos=departamentos,
                           funcoes=funcoes,
                           setores=['Produtivo', 'Administrativo', 'Outro'])

@app.route('/funcionarios/excluir/<int:func_id>', methods=['POST'])
def excluir_funcionario(func_id):
    if db.delete_funcionario(func_id):
        flash('Funcionário excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir funcionário.', 'danger')
    return redirect(url_for('listar_funcionarios'))


if __name__ == '__main__':
    # Cria o diretório static se não existir
    static_dir = os.path.join(BASE_DIR, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Cria o diretório templates se não existir
    templates_dir = os.path.join(BASE_DIR, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    # Cria o arquivo style.css se não existir
    css_file_path = os.path.join(static_dir, 'style.css')
    if not os.path.exists(css_file_path):
        with open(css_file_path, 'w') as f:
            f.write("/* Estilos CSS básicos aqui */\nbody { font-family: sans-serif; margin: 20px; }\n.flash-messages .alert { margin-top: 15px; }")
        print(f"Arquivo '{css_file_path}' criado.")

    app.run(debug=True)
