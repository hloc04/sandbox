from functools import wraps
from flask import Flask, request, render_template, jsonify, Response
import sys
import subprocess
import io

app = Flask(__name__)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

def check_auth(username, password):
    """Check if a username/password combination is valid."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Install package function
def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError as e:
        return str(e)
    return None

# Run script function
def run_script(script: str, class_name: str, method_name: str, params: dict):
    install_commands = []
    script_lines = script.split('\n')
    script_lines_to_execute = []

    for line in script_lines:
        if line.startswith('!pip install '):
            package = line[len('!pip install '):]
            install_commands.append(package)
        else:
            if line.startswith('import '):
                package = line.split()[1].split('.')[0]
                install_commands.append(package)
            elif line.startswith('from '):
                package = line.split()[1].split('.')[0]
                install_commands.append(package)
            script_lines_to_execute.append(line)
    
    install_errors = []
    for package in install_commands:
        try:
            error = install_package(package)
            if error:
                install_errors.append(error)
        except Exception as e:
            print(e)
    
    if install_errors:
        return None, '\n'.join(install_errors), ""
    
    script = '\n'.join(script_lines_to_execute)
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    try:
        exec_globals = {}
        exec(script, exec_globals)
        cls = exec_globals[class_name]
        instance = cls()
        result = getattr(instance, method_name)(**params)
    except Exception as e:
        result = f"Error: {e}"

    stdout_output = sys.stdout.getvalue()
    stderr_output = sys.stderr.getvalue()

    sys.stdout = old_stdout
    sys.stderr = old_stderr

    return result, stdout_output, stderr_output

# Routes
@app.route('/')
def index():
    return render_template('dynamic.html')

@app.route('/run_script', methods=['POST'])
def run_script_route():
    data = request.json
    script = data.get('script')
    params = data.get('params')
    class_name = data.get('class_name')
    method_name = data.get('method_name')
    
    result, stdout, stderr = run_script(script, class_name, method_name, params)
    return jsonify(result=result, stdout=stdout, stderr=stderr)

# Admin sandbox route
@app.route('/admin/sandbox', methods=['GET', 'POST'])
@requires_auth
def admin_sandbox():
    if request.method == 'POST':
        script = request.form['script']
        class_name = request.form['class_name']
        method_name = request.form['method_name']
        params = request.form.get('params', '{}')
        params = eval(params)  # Convert string representation of dictionary to a dictionary
        
        result, stdout, stderr = run_script(script, class_name, method_name, params)
        return render_template('sandbox.html', result=result, stdout=stdout, stderr=stderr, script=script)
    
    return render_template('sandbox.html', result=None, stdout=None, stderr=None, script='')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
