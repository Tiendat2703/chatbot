# 🎓 Admission Chatbot – AI-powered Admission & Score Lookup Assistant

## 🚀 Overview

This project is an AI-powered chatbot designed to support university admission consultation and score lookup for students. It integrates a Large Language Model (LLM) with **Function Calling** and **Retrieval-Augmented Generation (RAG)** techniques to deliver relevant, accurate, and faithful responses.

## 🧠 Key Features

- 💬 Natural conversation with LLM
- 🛠️ Function Calling to:
  - Check admission scores by major/year
  - Lookup personal academic scores
  - Guide on admission procedures and deadlines
- 🔍 RAG: Retrieve real-time data from local documents and databases
- ✅ 90% Faithfulness and 90% Relevance (evaluated on QA benchmark set)
- 🌐 Built using Python and Flask
- 🗂️ Web-based UI (HTML/CSS/JS + Bootstrap)


## ⚙️ Tech Stack

- **Python 3.10+**
- **Flask** – Web framework
- **LangChain** – For managing LLM and tools
- **OpenAI / LLaMA / Gemini 1.5** – LLM backend
- **FAISS** – Vector store for RAG
- **Pandas, Numpy** – Data processing
- **HTML, CSS, JS** – Frontend

## 📌 Use Cases

- 🧾 Lookup entrance scores for specific majors (from past years)
- 📋 Provide info on admission policies and application steps
- 🧑‍🎓 Help students find matching majors based on their interests/scores

## 🚀 Getting Started

```bash
# Clone the repo
git clone https://github.com/Tiendat2703/chatbot.git
cd chatbot

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
🧪 Evaluation Metrics
Faithfulness: 90% — answers reflect factual sources and functions correctly

Relevance: 90% — highly context-aware responses


📄 License
MIT License – Free to use and modify.

👨‍💻 Author
Tiến Đạt – https://github.com/Tiendat2703

