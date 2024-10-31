import queue
import threading
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import dotenv_values, load_dotenv
import os
import subprocess
import json
import subprocess
import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'
PASSWORD_HASH = generate_password_hash(os.getenv('PASSWORD'))

# Декоратор для проверки авторизации
def login_required(f):
    from functools import wraps
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
    try:
        return [s for s in os.listdir('scripts') if s.endswith('.sh')]
    except:
        return ["No scripts yet. Make the 'scripts' folder in your workspace and add there some! Add scriptname.sh.env file to add default variables"]

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

@app.route('/run_script', methods=['GET'])
@login_required
def run_script():
    script_name = request.args.get('script_name')
    env_vars = json.loads(request.args.get('env_vars', '{}'))
    script_path = os.path.join('scripts', script_name)

    allowed_keys = load_script_env(script_name).keys()
    env_vars = {key: value for key, value in env_vars.items() if key in allowed_keys}

    log_filename = f"{script_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(os.path.dirname(__file__), 'logs', log_filename)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def generate_output():
        def enqueue_output(pipe, output_queue, isstderr, log_file):
            for line in iter(pipe.readline, ''):
                if isstderr:
                    formatted_line = f"<span style='color: red;'>{line}</span>\n\n"
                else:
                    formatted_line = line

                log_file.write(line)
                log_file.flush()

                output_queue.put(formatted_line)

            pipe.close()

        with open(log_path, 'a') as log_file:
            process = subprocess.Popen(
                ['bash', script_path],
                env={**os.environ, **env_vars},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            output_queue = queue.Queue()

            stdout_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_queue, False, log_file))
            stderr_thread = threading.Thread(target=enqueue_output, args=(process.stderr, output_queue, True, log_file))
            stdout_thread.start()
            stderr_thread.start()

            while stdout_thread.is_alive() or stderr_thread.is_alive() or not output_queue.empty():
                try:
                    line = output_queue.get(timeout=0.1)
                    yield f"data: {line}\n\n"
                except queue.Empty:
                    pass

            stdout_thread.join()
            stderr_thread.join()
            process.wait()

    return Response(generate_output(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
