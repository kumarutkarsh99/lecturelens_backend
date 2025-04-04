import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

import nltk
from nltk.corpus import stopwords
from collections import Counter

nltk.download('punkt')
nltk.download('stopwords')

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set! Make sure it's in your Railway environment variables.")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Allowed File Extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def summarize_text(text, sentence_count=3):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    return " ".join(str(sentence) for sentence in summarizer(parser.document, sentence_count))

def extract_keywords(text, num_keywords=5):
    words = nltk.word_tokenize(text.lower())
    filtered_words = [word for word in words if word.isalnum() and word not in stopwords.words('english')]
    return [word for word, _ in Counter(filtered_words).most_common(num_keywords)]

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(200), unique=True, nullable=False)
    text_content = db.Column(db.Text, nullable=False, index=True)
    tags = db.Column(db.String(200))
    summary = db.Column(db.Text)
    keywords = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Ensure database tables exist
with app.app_context():
    db.create_all()

# File Upload Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Tesseract & Poppler
pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
POPPLER_PATH = os.getenv('POPPLER_PATH', '')

@app.route('/upload', methods=['POST'])
def upload_note():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        text_content = ""
        file_ext = os.path.splitext(unique_filename)[1].lower()

        try:
            if file_ext == ".pdf":
                pages = convert_from_path(file_path, poppler_path=POPPLER_PATH if POPPLER_PATH else None)
                text_content = "\n".join([pytesseract.image_to_string(page) for page in pages])
            else:
                text_content = pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            return jsonify({'error': 'OCR processing failed', 'details': str(e)}), 500
        
        summary = summarize_text(text_content)
        keywords = extract_keywords(text_content)
        tags = request.form.get('tags', ", ".join(keywords))
        
        try:
            note = Note(
                file_name=unique_filename, 
                text_content=text_content, 
                tags=tags,
                summary=summary,
                keywords=", ".join(keywords)
            )
            db.session.add(note)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'File already exists'}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Database error', 'details': str(e)}), 500
        
        return jsonify({
            'message': 'File uploaded and processed successfully',
            'filename': unique_filename,
            'summary': summary,
            'keywords': keywords
        }), 200
    except Exception as e:
        return jsonify({'error': 'Unexpected error occurred', 'details': str(e)}), 500

@app.route('/search', methods=['GET'])
def search_notes():
    query = request.args.get('q', '')
    filters = [Note.text_content.ilike(f'%{query}%')] if query else []

    results = Note.query.filter(*filters).all() if filters else Note.query.all()
    notes_data = [{
        'id': note.id,
        'file_name': note.file_name,
        'tags': note.tags,
        'summary': note.summary,
        'keywords': note.keywords,
        'text_excerpt': (note.text_content[:200] + '...') if len(note.text_content) > 200 else note.text_content,
        'file_url': request.host_url + 'files/' + note.file_name,
        'created_at': note.created_at.isoformat()
    } for note in results]
    
    return jsonify(notes_data)

@app.route('/files/<filename>')
def serve_file(filename):
    if not allowed_file(filename):
        return jsonify({'error': 'Access denied'}), 403
    return send_from_directory(UPLOAD_FOLDER, secure_filename(filename))

@app.route('/delete/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({'error': 'Note not found'}), 404
        
        file_path = os.path.join(UPLOAD_FOLDER, note.file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(note)
        db.session.commit()
        
        return jsonify({'message': 'Note deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting note', 'details': str(e)}), 500

@app.route('/')
def home():
    return "LectureLens Flask Server is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

