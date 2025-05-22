import numpy as np
import faiss
import google.generativeai as genai

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

#from langchain.embeddings import GPT4AllEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter

genai.configure(api_key="AIzaSyBwLVH64NVzGZ6ISO_jqmsQGX2iXeEyByg")

def create_db_from_doc(pdf_path):
    loader = DirectoryLoader('/content/documents',glob='*.pdf',loader_cls=PyPDFLoader)
    document = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512,chunk_overlap = 50)
    chunks = text_splitter.split_documents(document)
    embedding_model = HuggingFaceEmbeddings(model_name ="all-MiniLM-L6-v2")
    db = FAISS.from_documents(chunks,embedding_model)
    db.save_local('vectostore1/vecto_db_doc')
    return db
import google.generativeai as genai


# Định nghĩa đường dẫn đến FAISS vector DB
vector_db_path = r"vecto_db_csv-20250312T163303Z-001\vecto_db_csv"
#"/content/vectostore/vecto_db1"

# Hàm đọc FAISS index từ local
def read_vectors_db():
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004",
                                                   google_api_key="AIzaSyBwLVH64NVzGZ6ISO_jqmsQGX2iXeEyByg")
    db = FAISS.load_local(vector_db_path, embedding_model, allow_dangerous_deserialization=True)
    return db, embedding_model

# Load database FAISS và model embedding
db, embedding_model = read_vectors_db()

# Hàm tìm kiếm vector gần nhất trong FAISS
def search_faiss(query, texts, top_k=3):
    query_embedding = np.array([embedding_model.embed_query(query)]).astype("float32")
    
    # Lấy index từ FAISS DB
    index = db.index
    distances, indices = index.search(query_embedding, top_k)
    texts = list(texts)
    retrieved_texts = [texts[i] for i in indices[0] if i < len(texts)]
    return retrieved_texts

# Hàm generate bằng Gemini
def generate_with_gemini(query, texts):
    relevant_texts = search_faiss(query, texts)

    # Trích xuất nội dung văn bản từ các Document
    context = "\n".join([doc.page_content for doc in relevant_texts])

    prompt = f"""Dựa trên tài liệu sau hãy đọc hết tất cả nội dung trong dữ liệu và lấy tất cả các năm, hãy trả lời câu hỏi:\n\n{context}\n\nCâu hỏi: {query}\nTrả lời:"""

    model = genai.GenerativeModel("models/gemini-1.5-pro")
    response = model.generate_content(prompt, generation_config={"max_output_tokens": 10000})
    return response.text

# Test câu hỏi
#doc_texts = db.docstore._dict.values()  # Lấy lại danh sách văn bản từ FAISS
#query = "còn của trường bách khoa là bao nhiêu á"
#response = generate_with_gemini(query, doc_texts)
#print(response)
 
def main(query):
    doc_texts = db.docstore._dict.values()  # Lấy lại danh sách văn bản từ FAISS
    response = generate_with_gemini(query, doc_texts) 
    return response

