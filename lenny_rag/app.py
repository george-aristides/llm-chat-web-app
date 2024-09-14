from flask import Flask, render_template, request, jsonify
import subprocess
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Paths
INDEX_PATH = os.path.join('embeddings', 'faiss_index.bin')
CHUNKS_PATH = os.path.join('embeddings', 'chunks.npy')

# Load the FAISS index
index = faiss.read_index(INDEX_PATH)
# Load the text chunks
chunks = np.load(CHUNKS_PATH, allow_pickle=True)
# Initialize the embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['message']
    response = get_model_response(user_input)
    return jsonify({'response': response})

def get_model_response(user_input):
    # Generate embedding for the user input
    user_embedding = embedding_model.encode([user_input])

    # Search for similar chunks
    k = 5  # Number of relevant chunks to retrieve
    distances, indices = index.search(np.array(user_embedding), k)
    retrieved_chunks = [chunks[idx] for idx in indices[0]]

    # Combine retrieved chunks into context
    context = "\n".join(retrieved_chunks)

    # Create the prompt with context
    prompt = f"""You are Lenny, a helpful assistant.

Use the following context to answer the question.

Context:
{context}

Question:
{user_input}

Answer:"""

    # Run the model with the prompt
    process = subprocess.Popen(['ollama', 'run', 'lenny'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(prompt)
    return stdout.strip()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
