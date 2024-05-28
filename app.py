from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import os
import importlib.util
import psycopg2

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def get_db_connection():
    return psycopg2.connect(
        host="ec2-44-220-222-138.compute-1.amazonaws.com",
        database="de84slt1iucctv",
        user="adaptativa_read",
        password="pe71d6441e182e2458c5fd7701d60d1d0023f68f74dbd0ea0f8e1211d05a14374",
        port="5432"
    )

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, user_name FROM educator_users WHERE id = %s', (user_id,))
    user_data = cur.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('password')
        if username and password:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, user_name, encrypted_password FROM educator_users WHERE user_name = %s', (username,))
            user_data = cur.fetchone()
            conn.close()
            if user_data and bcrypt.check_password_hash(user_data[2], password):
                user = User(id=user_data[0], username=user_data[1])
                login_user(user)
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Usuário ou senha inválidos")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("https://taua2024-5674f4a1f8a4.herokuapp.com/login?next=%2F")

def list_scripts():
    """Lista os scripts Python disponíveis na pasta 'scripts'."""
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]
    print("Scripts disponíveis:", scripts)
    return scripts

def execute_script(script_name, filters=None):
    """Executa a função 'execute_query' do script selecionado e retorna seus resultados."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print("Executando script:", script_path)
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Adiciona filtros se forem fornecidos
    if filters:
        columns, result = module.execute_query(filters)
    else:
        columns, result = module.execute_query()
    
    return columns, result

@app.route('/')
@login_required
def index():
    scripts = list_scripts()
    return render_template('index.html', scripts=scripts)

@app.route('/execute', methods=['GET'])
@login_required
def execute():
    script_name = request.args.get('script')
    display_mode = request.args.get('display', 'tabela')

    if script_name in list_scripts():
        columns, data = execute_script(script_name)
        return render_template('tabela.html', columns=columns, data=data)
    else:
        return "Script not found", 404

@app.route('/filter_data', methods=['GET'])
@login_required
def filter_data():
    script_name = request.args.get('script_name')
    print("Nome do script solicitado para filtro:", script_name)
    if script_name in list_scripts():
        filters = {}
        for key, value in request.args.items():
            if key not in ('script_name',):
                filters[key] = value

        print("Filtros aplicados:", filters)
        columns, data = execute_script(script_name, filters)
        return jsonify(columns=columns, data=data)
    else:
        return jsonify(columns=[], data=[])

if __name__ == '__main__':
    app.run(debug=True)
