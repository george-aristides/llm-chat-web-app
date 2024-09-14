import os
import PyPDF2
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Paths
PDF_PATH = os.path.join('data', 'your_document.pdf')
INDEX_PATH = os.path.join('embeddings', 'faiss_index.bin')
index = faiss.read_index(INDEX_PATH)
CHUNKS_PATH = os.path.join('embeddings', 'chunks.npy')

# Ensure directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('embeddings', exist_ok=True)

def extract_text(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    text = ''
    for page in reader.pages:
        text += page.extract_text()
    return text

# import os
# import PyPDF2
# from sentence_transformers import SentenceTransformer
# import faiss
# import numpy as np

# # Paths
# DATA_DIR = 'data'
# EMBEDDINGS_DIR = 'embeddings'
# INDEX_PATH = os.path.join(EMBEDDINGS_DIR, 'faiss_index.bin')
# CHUNKS_PATH = os.path.join(EMBEDDINGS_DIR, 'chunks.npy')

# # Ensure directories exist
# os.makedirs(DATA_DIR, exist_ok=True)
# os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# def get_pdf_path():
#     # List all files in the data directory
#     files = os.listdir(DATA_DIR)
#     # Filter out PDF files
#     pdf_files = [f for f in files if f.lower().endswith('.pdf')]
#     if not pdf_files:
#         raise FileNotFoundError("No PDF files found in the 'data' directory.")
#     elif len(pdf_files) > 1:
#         raise FileExistsError("Multiple PDF files found in the 'data' directory. Please ensure only one PDF is present.")
#     else:
#         return os.path.join(DATA_DIR, pdf_files[0])

# def extract_text(pdf_path):
#     reader = PyPDF2.PdfReader(pdf_path)
#     text = ''
#     for page in reader.pages:
#         text += page.extract_text()
#     return text

def split_text(text, max_length=500):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ''
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + '. '
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + '. '
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def create_embeddings(chunks):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(chunks)
    return embeddings

def save_embeddings(embeddings, chunks):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    np.save(CHUNKS_PATH, chunks)

if __name__ == '__main__':
    text = extract_text(PDF_PATH)
    chunks = split_text(text)
    embeddings = create_embeddings(chunks)
    save_embeddings(embeddings, chunks)
