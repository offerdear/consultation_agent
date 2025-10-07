from flask import Flask, render_template, request, jsonify, send_file
from rag_inmemory import InMemoryRAG 
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_openai import OpenAIEmbeddings
from chunking import extract_chunks_from_file
from utils import store_embeddings_with_metadata
from startup_processor import process_existing_uploads, should_process_uploads
from file_tracker import clear_processed_files
from consultation_engine import ConsultationEngine
import os

# Tell Flask where to find the templates and static folders
app = Flask(__name__)

# ... all your existing routes and logic follow here ...
#app = Flask(__name__)

# Initialize the in-memory RAG system
rag = InMemoryRAG()
consultation_engine = ConsultationEngine(rag)

app.config['UPLOAD_FOLDER'] = 'uploads'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Process existing files in uploads folder on startup
if should_process_uploads():
    print("📄 Processing existing files in uploads folder...")
    # Pass the existing rag instance instead of creating a new one
    from process_uploads import scan_uploads_folder, process_file, get_file_category
    
    files_to_process = scan_uploads_folder(app.config['UPLOAD_FOLDER'])
    stats = {"processed": 0, "failed": 0}
    
    for file_path, filename in files_to_process:
        category = get_file_category(filename, {
            'curriculum': 'Curriculum',
            'pricing': 'Pricing', 
            'teacher': 'Teachers',
            'general': 'General Information',
        })
        success = process_file(file_path, filename, category, rag)  # Use existing rag
        if success:
            stats["processed"] += 1
        else:
            stats["failed"] += 1
    
    print(f"✅ Startup processing completed: {stats['processed']} files processed")
else:
    print("ℹ️ No need to process existing files")

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'rtf'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    # Redirect to chatbot 
    print("🔥 HOME ROUTE HIT!") # test
    return render_template('new_chat.html')

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/upload', methods=['GET'])
def upload_page():
    # Show the upload form
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Validate file input
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Validate form inputs
    category = request.form.get('category')
    if not category:
        return jsonify({'error': 'Missing category'}), 400

    # Save uploaded file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get chunks with chunking.py
    chunks = extract_chunks_from_file( filepath, filename=filename, category=category, )

    # Store chunks + metadata into in-memory system 
    store_embeddings_with_metadata(rag, chunks)

    return render_template('upload.html', success=True)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    categories = rag.get_categories()
    return jsonify({'categories': categories})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        message = data.get("message")
        category = data.get("category")
        mode = data.get("mode")
        session_id = data.get("session_id", rag.current_session_id)

        # For consultation mode, category is optional. For FAQ mode, category is required.
        if not message or not mode or (mode == 'faq' and not category):
            return jsonify({"error": "Message and mode are required. For FAQ mode, category is required."}), 400

        response = rag.generate_agentic_response(
            user_input=message,
            category=category,
            mode=mode,
            session_id=session_id
        )

        return jsonify({"response": response})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/consultation', methods=['POST'])
def handle_consultation():
    """Handle interactive consultation requests"""
    try:
        data = request.get_json()
        message = data.get("message", "")
        action_type = data.get("action_type", "text")  # text, button_click, form_submit
        session_id = data.get("session_id")
        
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        # Handle consultation flow
        result = consultation_engine.handle_message(message, session_id, action_type)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

"""Get next assessment question"""
@app.route('/api/assessment/question', methods=['POST'])
def get_assessment_question():
    session_id = request.json.get('session_id')
    consultation = rag.consultation_manager.get_consultation(session_id)
    if consultation is None:
        consultation = rag.consultation_manager.start_consultation(session_id)
    
    question = rag.assessment_engine.get_next_question(session_id, consultation)
    return jsonify({"question": question})

"""Submit assessment answer"""
@app.route('/api/assessment/answer', methods=['POST'])
def submit_assessment_answer():
    data = request.get_json()
    session_id = data.get('session_id')
    answer_index = data.get('answer_index')
    
    consultation = rag.consultation_manager.get_consultation(session_id)
    if consultation is None:
        consultation = rag.consultation_manager.start_consultation(session_id)
    result = rag.assessment_engine.process_answer(session_id, consultation, answer_index)
    
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Get system status information"""
    try:
        status = {
            'knowledge_items': len(rag.knowledge_base),
            'context_items': len(rag.context_base),
            'categories': len(rag.categories),
            'session_id': rag.current_session_id,
            'conversation_turns': len(rag.conversation_history)
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Clear knowledge base or context"""
    try:
        data = request.get_json()
        clear_type = data.get('type', 'knowledge')
        
        if clear_type == 'knowledge':
            rag.clear_knowledge_base()
            return jsonify({'message': 'Knowledge base cleared'})
        elif clear_type == 'context':
            rag.clear_context()
            return jsonify({'message': 'Context cleared'})
        else:
            return jsonify({'error': 'Invalid clear type'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-uploads', methods=['POST'])
def process_uploads_route():
    """Manually process existing files in uploads folder"""
    try:
        stats = process_existing_uploads(verbose=False)
        return jsonify({
            'message': 'Uploads processing completed',
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-processed-files', methods=['POST'])
def clear_processed_files_route():
    """Clear the list of processed files (allows reprocessing all files)"""
    try:
        clear_processed_files()
        return jsonify({'message': 'Processed files list cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
