import fitz  # PyMuPDF
import re
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredRTFLoader


"""Extract chunks from PDF files"""
def extract_chunks_from_pdf( file_bytes: bytes, filename: str, category: str = None, ):
    print("Processing PDF file:", filename)
    print("Category:", category)
    
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)

        chunks_with_metadata = []

        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            
            # Skip empty pages
            if not page_text.strip():
                continue

            chunks = text_splitter.split_text(page_text)
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Only add non-empty chunks
                    metadata = {
                        "source": filename,
                        "category": category or "Unknown",
                        "page": page_num + 1,
                        "chunk_id": f"{filename}_{page_num+1}_{i}",
                        "file_type": "pdf"
                    }
                    chunks_with_metadata.append((chunk, metadata))
        
        doc.close()
        return chunks_with_metadata
        
    except Exception as e:
        print(f"Error processing PDF file {filename}: {e}")
        return []


"""Extract chunks from RTF files"""
def extract_chunks_from_rtf( file_path: str, filename: str, category: str = None, ):
    print("Processing RTF file:", filename)
    print("Category:", category)
    
    try:
        # Use UnstructuredRTFLoader to load RTF content
        loader = UnstructuredRTFLoader(file_path, mode="elements", strategy="fast")
        documents = loader.load()
        
        # Combine all document content
        full_text = "\n\n".join([doc.page_content for doc in documents])
        
        if not full_text.strip():
            print(f"No text content found in RTF file {filename}")
            return []
        
        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = text_splitter.split_text(full_text)
        
        chunks_with_metadata = []
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Only add non-empty chunks
                metadata = {
                    "source": filename,
                    "category": category or "Unknown",
                    "file_type": "rtf",
                    "chunk_id": f"{filename}_{i}"
                }
                chunks_with_metadata.append((chunk, metadata))
        
        return chunks_with_metadata
        
    except Exception as e:
        print(f"  ⚠️  UnstructuredRTFLoader failed ({e}), trying fallback parser")
        
        # Fallback: Simple RTF text extraction
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Remove RTF formatting codes (basic approach)
            rtf_patterns = [
                r'\\[a-z]+\d*\s?',  # RTF commands like \b, \f1, etc.
                r'\\[{}]',          # RTF braces
                r'\\[\\]',          # Escaped backslashes
            ]
            
            for pattern in rtf_patterns:
                content = re.sub(pattern, '', content)
            
            # Remove extra whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            
            if content:
                print(f"  ✅ Successfully parsed with fallback parser")
                # Split into chunks
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                chunks = text_splitter.split_text(content)
                
                chunks_with_metadata = []
                for i, chunk in enumerate(chunks):
                    if chunk.strip():  # Only add non-empty chunks
                        metadata = {
                            "source": filename,
                            "category": category or "Unknown",
                            "file_type": "rtf",
                            "chunk_id": f"{filename}_{i}"
                        }
                        chunks_with_metadata.append((chunk, metadata))
                
                return chunks_with_metadata
            else:
                print(f"  ❌ No text content found in RTF file {filename}")
                return []
                
        except Exception as fallback_error:
            print(f"  ❌ Fallback parser also failed: {fallback_error}")
            return []


"""Extract chunks from any supported file type"""
def extract_chunks_from_file( file_path: str, filename: str, category: str = None, ):
    file_extension = filename.lower().split('.')[-1]
    
    if file_extension == 'pdf':
        # Read PDF as bytes
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        return extract_chunks_from_pdf(file_bytes, filename, category)
    
    elif file_extension == 'rtf':
        return extract_chunks_from_rtf(file_path, filename, category)
    
    else:
        print(f"Unsupported file type: {file_extension}")
        return []
