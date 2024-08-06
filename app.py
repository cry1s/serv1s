from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'

PASSWORD_HASH = generate_password_hash(os.getenv('PASSWORD'))

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

@app.route('/scripts', methods=['GET', 'POST'])
def scripts():
    if not session.get('authenticated'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        script_name = request.form.get('script')
        params = request.form.get(f'params_{script_name}', '')
        env_vars = request.form.get(f'env_vars_{script_name}', '')
        env = {k: v for k, v in (x.split('=') for x in env_vars.split() if '=' in x)}

        script_path = os.path.join('scripts', script_name)
        result = subprocess.run(['bash', script_path] + params.split(), env=env, capture_output=True, text=True)

        return render_template('scripts.html', scripts=os.listdir('scripts'), output=result.stdout, error=result.stderr)

    return render_template('scripts.html', scripts=os.listdir('scripts'))

if __name__ == '__main__':
    app.run(debug=True)
