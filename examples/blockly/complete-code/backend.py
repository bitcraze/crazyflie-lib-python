import os
import subprocess
import tempfile

from flask import Flask
from flask import request
from flask import send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.py')

# Serve files from THIS directory
app = Flask(__name__, static_folder='.', static_url_path='')


@app.route('/')
def index():
    return send_from_directory('.', 'index_cf.html')


@app.route('/run', methods=['POST'])
def run():
    blockly_code = request.data.decode()

    with open(TEMPLATE_PATH) as f:
        template = f.read()

    full_code = template.replace('{{BLOCKLY_CODE}}', blockly_code)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False
    ) as f:
        f.write(full_code)
        filename = f.name

    subprocess.Popen(['python3', filename])
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True)
