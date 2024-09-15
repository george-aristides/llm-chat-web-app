from flask import Flask, render_template, request, jsonify
import subprocess
import os
import re
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Constants
MAX_ITERATIONS = 3  # Number of CoT iterations
MODEL_NAME = 'lenny_cot'  # Model name

# Define the absolute path for the log file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'app_cot.log')

# Ensure the log directory exists
os.makedirs(BASE_DIR, exist_ok=True)

# Configure logging
logger = logging.getLogger('app_cot_logger')
logger.setLevel(logging.DEBUG)  # Capture all log levels

# Create handlers
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)  # 5MB per file
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # INFO level for console

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Initial log entry to confirm logging is set up
logger.info("Logging is configured successfully.")

def clean_output(output):
    """Strip control characters like spinners or progress indicators from model output."""
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by zero or more control codes
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', output)

@app.route('/')
def home():
    logger.info("Home page accessed.")
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.form.get('message', '').strip()
        if not user_input:
            logger.warning("Empty user input received.")
            return jsonify({'response': "Please enter a valid question."})
        logger.info(f"User input received: {user_input}")
        response = get_model_response(user_input)
        logger.info(f"Response sent to user: {response}")
        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"Exception in /chat route: {e}")
        return jsonify({'response': "I'm sorry, something went wrong while processing your request."})

def get_model_response(user_input):
    try:
        refined_answer = None

        prompt = f"""You are Lenny, a helpful assistant.

Question:
{user_input}

Answer:"""
        
        logger.info("Starting Chain-of-Thought iterations.")
        logger.debug(f"Initial prompt:\n{prompt}")

        # Run the model with the current prompt
        process = subprocess.Popen(
            ['ollama', 'run', MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(prompt, timeout=60)  # 60-second timeout
        exit_code = process.returncode
        logger.debug(f"Subprocess exit code: {exit_code}")

        # Log the raw stdout and stderr
        logger.debug(f"Raw stdout: {stdout}")
        logger.debug(f"Raw stderr: {stderr}")

        # Log the content of stderr for analysis
        if stderr.strip():
            logger.warning(f"Non-empty stderr output:\n{stderr}")

        if exit_code != 0:
            logger.error(f"Subprocess exited with code {exit_code}")
            return "I'm sorry, something went wrong while processing your request."

        # Proceed even if stderr is non-empty, unless critical errors are detected
        # Additional logic to detect critical errors can be added here

        # Check if stdout is empty after stripping whitespace
        if not stdout.strip():
            logger.error("Model returned an empty response.")
            return "I'm sorry, I couldn't formulate a response."

        # Clean up control characters from the model's output
        cleaned_output = clean_output(stdout)
        logger.debug(f"Cleaned model output:\n{cleaned_output}")

        # Normalize whitespace in the refined_answer
        refined_answer = ' '.join(cleaned_output.strip().split())
        logger.debug(f"Refined answer set: {refined_answer}")

        # Final log before returning refined_answer
        logger.info(f"Final refined_answer before return: {refined_answer}")

        # Ensure refined_answer is returned if valid
        return refined_answer if refined_answer else "I'm sorry, something went wrong while processing your request."
    except Exception as e:
        logger.error(f"Exception in get_model_response: {e}")
        return "I'm sorry, something went wrong while processing your request."


if __name__ == '__main__':
    # Log the current PATH for debugging purposes
    logger.debug(f"System PATH: {os.environ.get('PATH')}")
    
    logger.info("Starting Flask application.")
    app.run(host='0.0.0.0', port=8080)
