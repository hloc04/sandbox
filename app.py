from flask import Flask, request, render_template, jsonify
import sys
import subprocess
import io

app = Flask(__name__)

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError as e:
        return str(e)
    return None

def run_script(script: str, class_name: str, method_name: str, params: dict):
    # Parse the script to find !pip install commands
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
                #if not is_standard_library(package):
                install_commands.append(package)
            elif line.startswith('from '):
                package = line.split()[1].split('.')[0]
                #if not is_standard_library(package):
                install_commands.append(package)
            script_lines_to_execute.append(line)
    print(50*"=")
    print(install_commands)
    print(script_lines_to_execute)
    print(50*"=")
    # Install any specified packages
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
    
    # The remaining script to execute
    script = '\n'.join(script_lines_to_execute)
    print(script)
    # Redirect stdout and stderr to capture the outputs
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    # Use a standard globals environment
    try:
        # Execute the script
        exec_globals = {}
        exec(script, exec_globals)
        
        # Instantiate the class and call the run method with params
        cls = exec_globals[class_name]
        instance = cls()
        result = getattr(instance, method_name)(**params)
        
    except Exception as e:
        result = f"Error: {e}"

    # Capture the output
    stdout_output = sys.stdout.getvalue()
    stderr_output = sys.stderr.getvalue()

    # Reset stdout and stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    return result, stdout_output, stderr_output

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

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
