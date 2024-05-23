from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required
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
        host="ec2-3-224-58-73.compute-1.amazonaws.com",
        database="de84slt1iucctv",
        user="adaptativa_read",
        password="pe71d6441e182e2458c5fd7701d60d1d0023f68f74dbd0ea0f8e1211d05a14374",
        port="5432"
    )

class User(UserMixin):
    def __init__(self, id, username):  # Corrigido para usar dois sublinhados de cada lado
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


def fetch_pie_chart_data():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.id AS institution_id,
                    i.name AS institution_name,
                    COUNT(DISTINCT ie.user_id) AS total_matriculados
                FROM 
                    institution_enrollments ie
                INNER JOIN institution_classrooms ic ON ic.id = ie.classroom_id  
                INNER JOIN institution_levels il ON il.id = ic.level_id 
                INNER JOIN institution_courses ic3 ON ic3.id = il.course_id 
                INNER JOIN institution_colleges ic2 ON ic2.id = ic3.institution_college_id 
                INNER JOIN institutions i ON i.id = ic2.institution_id
                INNER JOIN regions r ON ic2.region_id = r.id 
                INNER JOIN cities c ON c.id = r.city_id 
                WHERE i.name ILIKE '%2024%'
                AND c.name = 'Tauá' 
                AND i.id IN (335, 336, 337, 338) -- Filtro específico para as instituições com os IDs fornecidos
                GROUP BY i.id, i.name
                ORDER BY i.id;
            """)
            results = cur.fetchall()
            if results:
                labels = [row[1] for row in results]
                data = [row[2] for row in results]  # Total de alunos matriculados
                return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"Erro ao executar consulta SQL: {e}")
    finally:
        conn.close()
    return {'labels': [], 'data': []}

def list_scripts():
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]
    print("Scripts disponíveis:", scripts)
    return scripts

def execute_script(script_name, filters=None):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print("Executando script:", script_path)
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if filters:
        print("Executando com filtros:", filters)
        columns, result = module.execute_query(filters)
    else:
        columns, result = module.execute_query()
    
    return columns, result

@app.route('/')
@login_required
def index():
    scripts = list_scripts()
    pie_chart_data = fetch_pie_chart_data()
    return render_template('index.html', scripts=scripts, pie_chart_data=pie_chart_data)

@app.route('/tabela', methods=['GET'])
@login_required
def tabela():
    script_name = request.args.get('script_name')
    print("Nome do script solicitado:", script_name)
    if script_name in list_scripts():
        filters = {key: value for key, value in request.args.items() if key != 'script_name'}
        columns, data = execute_script(script_name, filters)
        return render_template('tabela.html', columns=columns, data=data, script_name=script_name)
    else:
        print("Script não encontrado:", script_name)
        return "Script not found", 404

@app.route('/filter_data', methods=['GET'])
@login_required
def filter_data():
    script_name = request.args.get('script_name')
    print("Nome do script solicitado para filtro:", script_name)
    if script_name in list_scripts():
        filters = {key: value for key, value in request.args.items() if key != 'script_name'}
        print("Filtros aplicados:", filters)
        columns, data = execute_script(script_name, filters)
        return jsonify(columns=columns, data=data)
    else:
        print("Script não encontrado para filtro:", script_name)
        return jsonify(columns=[], data=[])

if __name__ == '__main__':
    app.run(debug=True)
