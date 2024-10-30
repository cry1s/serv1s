from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import dotenv_values, load_dotenv
import os
import subprocess
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'
PASSWORD_HASH = generate_password_hash(os.getenv('PASSWORD'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def load_script_env(script_name):
    env_path = os.path.join('scripts', f"{script_name}.env")
    if os.path.exists(env_path):
        return dotenv_values(env_path)
    return {}

def get_scripts():
    return [s for s in os.listdir('scripts') if s.endswith('.sh')]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        password = request.form.get('password')
        if check_password_hash(PASSWORD_HASH, password):
            session['authenticated'] = True
            return redirect(url_for('scripts'))
        else:
            flash('Invalid password')
            return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/scripts', methods=['GET'])
@login_required
def scripts():
    return render_template('scripts.html', scripts=get_scripts())

@app.route('/scripts/<script_name>', methods=['GET'])
@login_required
def get_script(script_name):
    env_vars = load_script_env(script_name)
    return jsonify(env_vars)

@app.route('/run', methods=['POST'])
@login_required
def run_script():
    script_name = request.form.get('script_name')
    params = request.form.get('params', '')
    env_vars = json.loads(request.form.get('env_vars', '{}'))
    script_path = os.path.join('scripts', script_name)
    result = subprocess.run(['bash', script_path] + params.split(), env=env_vars, capture_output=True, text=True)
    
    return render_template('scripts.html', scripts=get_scripts(), output=result.stdout, error=result.stderr)

if __name__ == '__main__':
    app.run(debug=True)
