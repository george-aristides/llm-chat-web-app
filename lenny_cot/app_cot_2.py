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
        iteration = 0

        prompt = f"""You are Lenny, a helpful assistant.

Question:
{user_input}

Answer:"""
        
        logger.info("Starting Chain-of-Thought iterations.")
        logger.debug(f"Initial prompt:\n{prompt}")

        while iteration < MAX_ITERATIONS:
            logger.info(f"Iteration {iteration + 1}: Generating answer.")
            logger.debug(f"Current prompt:\n{prompt}")

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

            # Check for critical errors in stderr
            critical_errors = ["Traceback", "Error:", "Exception", "Critical"]

            if any(error in stderr for error in critical_errors):
                logger.error(f"Critical error from model during answer generation: {stderr}")
                return "I'm sorry, something went wrong while processing your request."
            else:
                if stderr.strip():
                    logger.warning(f"Non-critical stderr output:\n{stderr}")

            if exit_code != 0:
                logger.error(f"Subprocess exited with code {exit_code}")
                return "I'm sorry, something went wrong while processing your request."

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

            # Evaluation step
            evaluation_prompt = f"""You are Lenny, a helpful assistant.

Evaluate the following answer for completeness and accuracy. Identify any shortcomings or errors.

Answer:
{refined_answer}

Evaluation:"""
            logger.info(f"Iteration {iteration + 1}: Evaluating answer.")
            logger.debug(f"Evaluation prompt:\n{evaluation_prompt}")

            # Run the model to evaluate the answer
            process_eval = subprocess.Popen(
                ['ollama', 'run', MODEL_NAME],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout_eval, stderr_eval = process_eval.communicate(evaluation_prompt, timeout=60)
            exit_code_eval = process_eval.returncode
            logger.debug(f"Evaluation subprocess exit code: {exit_code_eval}")

            # Handle stderr from evaluation
            if any(error in stderr_eval for error in critical_errors):
                logger.error(f"Critical error during evaluation: {stderr_eval}")
                return "I'm sorry, something went wrong while processing your request."
            else:
                if stderr_eval.strip():
                    logger.warning(f"Non-critical stderr output during evaluation:\n{stderr_eval}")

            if exit_code_eval != 0:
                logger.error(f"Evaluation subprocess exited with code {exit_code_eval}")
                return "I'm sorry, something went wrong while processing your request."

            # Check if evaluation indicates the answer is satisfactory
            evaluation = clean_output(stdout_eval).strip().lower()
            logger.debug(f"Evaluation result:\n{evaluation}")

            if any(phrase in evaluation for phrase in ["no shortcomings", "no errors", "correct", "satisfactory"]):
                logger.info("Answer is satisfactory. Ending iterations.")
                break

            # Refinement step
            refinement_prompt = f"""You are Lenny, a helpful assistant.

Based on the following evaluation, refine your previous answer to address the identified shortcomings or errors.

Evaluation:
{evaluation}

Previous Answer:
{refined_answer}

Refined Answer:"""
            logger.info(f"Iteration {iteration + 1}: Refining answer.")
            logger.debug(f"Refinement prompt:\n{refinement_prompt}")

            # Run the model to refine the answer
            process_refine = subprocess.Popen(
                ['ollama', 'run', MODEL_NAME],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout_refine, stderr_refine = process_refine.communicate(refinement_prompt, timeout=60)
            exit_code_refine = process_refine.returncode
            logger.debug(f"Refinement subprocess exit code: {exit_code_refine}")

            # Handle stderr from refinement
            if any(error in stderr_refine for error in critical_errors):
                logger.error(f"Critical error during refinement: {stderr_refine}")
                return "I'm sorry, something went wrong while processing your request."
            else:
                if stderr_refine.strip():
                    logger.warning(f"Non-critical stderr output during refinement:\n{stderr_refine}")

            if exit_code_refine != 0:
                logger.error(f"Refinement subprocess exited with code {exit_code_refine}")
                return "I'm sorry, something went wrong while processing your request."

            # Update refined_answer
            cleaned_refined_output = clean_output(stdout_refine)
            refined_answer = ' '.join(cleaned_refined_output.strip().split())
            logger.debug(f"Updated refined answer: {refined_answer}")

            iteration += 1

        # Final log before returning refined_answer
        logger.info(f"Final refined_answer after CoT: {refined_answer}")

        # Ensure refined_answer is returned if valid
        return refined_answer if refined_answer else "I'm sorry, I couldn't formulate a satisfactory answer."
    except Exception as e:
        logger.error(f"Exception in get_model_response: {e}")
        return "I'm sorry, something went wrong while processing your request."


if __name__ == '__main__':
    # Log the current PATH for debugging purposes
    logger.debug(f"System PATH: {os.environ.get('PATH')}")
    
    logger.info("Starting Flask application.")
    app.run(host='0.0.0.0', port=8080)
