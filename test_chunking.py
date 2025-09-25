#!/usr/bin/env python3
"""
Simple test script to verify chunking functions work without requiring the full RAG system.
"""

import os
import sys
from chunking import extract_chunks_from_file

def test_file_processing():
    """Test processing files in uploads folder"""
    uploads_path = "uploads"
    
    if not os.path.exists(uploads_path):
        print(f"❌ Uploads folder not found: {uploads_path}")
        return
    
    print(f"🔍 Testing file processing in: {uploads_path}")
    
    # Test each file
    for filename in os.listdir(uploads_path):
        file_path = os.path.join(uploads_path, filename)
        
        if os.path.isfile(file_path):
            file_ext = filename.lower().split('.')[-1]
            
            if file_ext in ['pdf', 'rtf']:
                print(f"\n📄 Testing: {filename}")
                
                # Determine category based on filename
                if 'curriculum' in filename.lower():
                    category = 'Curriculum'
                elif 'pricing' in filename.lower():
                    category = 'Pricing'
                elif 'teacher' in filename.lower():
                    category = 'Teachers'
                elif 'general' in filename.lower():
                    category = 'General Information'
                else:
                    category = 'Documentation'
                
                try:
                    chunks = extract_chunks_from_file(file_path, filename, category)
                    
                    if chunks:
                        print(f"  ✅ Successfully extracted {len(chunks)} chunks")
                        print(f"  📝 Sample chunk (first 100 chars): {chunks[0][0][:100]}...")
                        print(f"  🏷️  Sample metadata: {chunks[0][1]}")
                    else:
                        print(f"  ⚠️  No chunks extracted")
                        
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            else:
                print(f"  ⏭️  Skipping unsupported file: {filename}")

if __name__ == "__main__":
    test_file_processing()
