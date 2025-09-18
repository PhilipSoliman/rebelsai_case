# RebelsAI Case Study – DocuSight (Intelligent Document Management API)

This project is a **FastAPI-based backend service** that provides intelligent document management endpoints.
It can scan a folder of documents, extract metadata, and perform document classification or sentiment analysis.

---

## Requirements
* Python 3.9+

## Setup
1. Clone this repository.
2. Move to the project directory.
  ```bash
  cd rebelsai_case
  ```
3. Run setup script:
  ```bash
  <your preferred base python> setup_env.py
  ```

## Features

* **Folder Insight Endpoint**

  * Counts documents in a folder (including subdirectories).
  * Extracts metadata such as file name, size, creation date, etc.
  * Saves metadata into a relational database.

* **Document Classification Endpoint**

  * Classifies documents using either:

    * An open-source NLP model (e.g., spaCy + [asent](https://spacy.io/universe/project/asent) for sentiment analysis).
    * Or a generative AI model (OpenAI API / Hugging Face).
  * Stores classification results in the database.

* **Scalability Considerations**

  * Designed with FastAPI for asynchronous request handling.
  * Can be extended with multiprocessing or task queues (Celery, Redis) for parallel document processing.

---

## Tech Stack

* **Python 3.9+**
* **FastAPI** – web framework for building APIs.
* **SQLAlchemy** – ORM for relational database (SQLite/PostgreSQL).
* **spaCy + asent** – NLP and sentiment analysis.
* **Uvicorn** – ASGI server to run the app.

---

## Project Structure

```
client_data/           # Sample documents for testing
docusight/
│── main.py            # FastAPI entrypoint
│── models.py          # SQLAlchemy models
│── database.py        # Database connection and session management
│── config.py          # Configuration settings
│── routes/
│   │── folder.py      # Folder insight endpoints
│   │── classification.py  # Document classification endpoints
```

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**

   ```bash
   uvicorn app.main:app --reload
   ```

3. **Access API docs**
   Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive Swagger UI.

---

## Example Endpoints

* `GET /folder/insight` → Returns total number of documents + metadata.
* `POST /classification/analyze` → Runs classification/sentiment analysis on all documents.

---

## Notes

* In this demo, the app analyzes **local folders** on the server.
* In production, document storage would typically be handled via:

  * File upload APIs,
  * Shared cloud storage (e.g., S3, Azure Blob),
  * Or client-side preprocessing.