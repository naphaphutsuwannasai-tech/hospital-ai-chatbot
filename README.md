# Hospital AI Chatbot

An intelligent hospital AI chatbot system designed to facilitate the search for department information, phone numbers, locations, and an IT support and ticketing system, supporting multimodal operations (text combined with image uploads).

---

## Key Features

* **Semantic Search:** Search for departments using natural language sentences via the `SentenceTransformer` model, supporting a wide variety of query phrasing.

* **Intent Classification:** Classify user intent categories, such as inquiring about phone numbers (`Phone`), locations (`Location`), or IT support (`IT Support`) using Machine Learning.

* **Computer Vision & OCR:**
    * Automatic IT equipment object detection (e.g., computer monitors, mice, keyboards) using **YOLOv8**.
    * Text extraction from photos (e.g., warning signs, error codes) using **Tesseract OCR** optimized with image preprocessing for high accuracy.
    * Image structural similarity matching (**Image Hashing**) for frequent IT issues.

* **High Performance & Optimized:**
    * **Caching** mechanism for Knowledge Base data in memory to reduce database query load.
    * **Connection Pooling** for efficient MySQL database management.
    * **Thread-safe Logging** to safely record usage history.

* **Admin Panel:** An administrative dashboard to manage department information, synonyms (aliases), and IT troubleshooting guides (Knowledge Base).

---

## Tech Stack

* **Backend:** Python, Flask, Flask-CORS, Waitress (WSGI Server)
* **Database:** MySQL, `mysql-connector-python`

* **AI & Machine Learning:**
    * `scikit-learn` (Logistic Regression for Intent Classification)
    * `sentence-transformers` (Semantic Search)
    * `Ultralytics YOLOv8` (Object Detection)
    * `pytesseract` (OCR)
    * `imagehash` (Image Matching)

* **Frontend:** HTML5, CSS3, JavaScript

---

## Project Structure

```text
├── static/                # Uploaded images and frontend assets
├── data/                  # Initial data files (e.g., hospital.xlsx)
├── app.py                 # Main Flask server and routing
├── ai_excel_chat.py       # Query analysis and caching logic
├── semantic_search.py     # Semantic department search module
├── intent_classifier.py   # Intent classification model loader
├── image_matcher.py       # IT problem image comparison module
├── object_detector.py     # YOLOv8 object detection module
├── ocr_module.py          # Tesseract OCR extraction module
├── db_config.py           # Database configuration and connection pooling
├── logger.py              # Thread-safe logging module
├── requirements.txt       # Required Python libraries
└── .env                   # Environment configuration
```

---

## Demo Screenshot

### Chat Interface

![Chat Interface](assets/chatbot-demo.png)

### Admin Dashboard

![Admin Dashboard](assets/admin-demo.png)

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/hospital-ai-chatbot.git
cd hospital-ai-chatbot
```

---

### 2. Install required dependencies

```bash
pip install -r requirements.txt
```

> Note: You must also install **Tesseract-OCR** on your local system.

---

### 3. Configure MySQL Database

1. Create a database named:

```sql
hospital
```

2. Execute the SQL script to create required tables and relationships.

---

### 4. Create `.env` file

Create a file named `.env` in the project root directory:

```env
DB_HOST=localhost
DB_USER=root
DB_PASS=1234
DB_NAME=hospital
DB_PORT=3306
SECRET_KEY=your_super_secret_key
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
FLASK_ENV=development
```

---

### 5. Run the project

```bash
python app.py
```

Open your browser:

```
http://localhost:5000
```

---

## Admin Panel

Access the management dashboard:

```
http://localhost:5000/admin
```

The admin panel allows administrators to manage:

- Department information
- Department aliases (synonyms)
- IT troubleshooting Knowledge Base

---
