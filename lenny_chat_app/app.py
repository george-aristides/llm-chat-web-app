from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['message']
    response = get_model_response(user_input)
    return jsonify({'response': response})

def get_model_response(user_input):
    command = f"echo '{user_input}' | ollama run lenny"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
