# Backend - Talent Match AI

This folder contains the Flask backend for Talent Match AI.

## ⚙️ Prerequisites

* **Python 3.9+**
* **pip**
* **Node.js**
* **npm**
* A valid **Groq API key**

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your Groq API key:

```env
GROQ_API_KEY=your_api_key_here
```

Start the server:

```bash
python app.py
```

The backend runs on `http://localhost:5000`.

Note: Make sure your environment file is excluded from Git using `.gitignore`.