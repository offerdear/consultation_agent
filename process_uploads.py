#!/usr/bin/env python3
"""
Startup script to process existing files in the uploads folder and add them to the knowledge base.
This script can be run independently or integrated into the main application startup.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_inmemory import InMemoryRAG
from chunking import extract_chunks_from_file
from utils import store_embeddings_with_metadata
from file_tracker import get_processed_files, mark_file_processed

# Default categories for different file types
DEFAULT_CATEGORIES = {
    'pdf': 'Documentation',
    'rtf': 'Information',
    'txt': 'Text',
    'docx': 'Document'
}

def get_file_category(filename: str, custom_categories: Dict[str, str] = None) -> str:
    """
    Determine category for a file based on filename patterns or custom mapping.
    
    Args:
        filename: Name of the file
        custom_categories: Custom mapping of filename patterns to categories
    
    Returns:
        Category string for the file
    """
    filename_lower = filename.lower()
    
    # Custom category mapping (can be extended)
    if custom_categories:
        for pattern, category in custom_categories.items():
            if pattern.lower() in filename_lower:
                return category
    
    # Default pattern-based categorization
    if 'curriculum' in filename_lower:
        return 'Curriculum'
    elif 'pricing' in filename_lower:
        return 'Pricing'
    elif 'teacher' in filename_lower:
        return 'Teachers'
    elif 'general' in filename_lower:
        return 'General Information'
    elif 'guide' in filename_lower or 'manual' in filename_lower:
        return 'User Guide'
    else:
        # Fallback to file extension
        file_ext = filename.split('.')[-1].lower()
        return DEFAULT_CATEGORIES.get(file_ext, 'Documentation')

def scan_uploads_folder(uploads_path: str) -> List[Tuple[str, str]]:
    """
    Scan the uploads folder for supported files that haven't been processed yet.
    
    Args:
        uploads_path: Path to the uploads folder
    
    Returns:
        List of (file_path, filename) tuples
    """
    supported_extensions = {'.pdf', '.rtf', '.txt', '.docx'}
    files_found = []
    processed_files = get_processed_files()
    
    if not os.path.exists(uploads_path):
        print(f"❌ Uploads folder not found: {uploads_path}")
        return files_found
    
    print(f"🔍 Scanning uploads folder: {uploads_path}")
    
    for filename in os.listdir(uploads_path):
        file_path = os.path.join(uploads_path, filename)
        
        # Skip directories and hidden files
        if os.path.isdir(file_path) or filename.startswith('.'):
            continue
        
        # Check if file has supported extension
        file_ext = Path(filename).suffix.lower()
        if file_ext in supported_extensions:
            if filename in processed_files:
                print(f"  ✅ Already processed: {filename}")
            else:
                files_found.append((file_path, filename))
                print(f"  📄 Found (unprocessed): {filename}")
        else:
            print(f"  ⚠️  Skipping unsupported file: {filename}")
    
    return files_found

def process_file(file_path: str, filename: str, category: str, rag_system: InMemoryRAG) -> bool:
    """
    Process a single file and add it to the knowledge base.
    
    Args:
        file_path: Full path to the file
        filename: Name of the file
        category: Category for the file
        rag_system: RAG system instance
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"🔄 Processing: {filename} (Category: {category})")
        
        # Extract chunks from the file
        chunks = extract_chunks_from_file(file_path, filename, category)
        
        if not chunks:
            print(f"  ⚠️  No chunks extracted from {filename}")
            return False
        
        print(f"  📝 Extracted {len(chunks)} chunks")
        
        # Store chunks in knowledge base
        doc_ids = store_embeddings_with_metadata(rag_system, chunks)
        
        if doc_ids:
            print(f"  ✅ Successfully added {len(doc_ids)} chunks to knowledge base")
            # Mark file as processed
            mark_file_processed(filename)
            return True
        else:
            print(f"  ❌ Failed to add chunks to knowledge base")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {filename}: {e}")
        return False

def process_uploads_folder(
    uploads_path: str = "uploads",
    custom_categories: Dict[str, str] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Process all files in the uploads folder and add them to the knowledge base.
    
    Args:
        uploads_path: Path to the uploads folder
        custom_categories: Custom category mapping
        dry_run: If True, only show what would be processed without actually doing it
    
    Returns:
        Dictionary with processing statistics
    """
    print("🚀 Starting uploads folder processing...")
    print(f"📁 Uploads path: {uploads_path}")
    print(f"🔧 Dry run: {dry_run}")
    
    # Initialize RAG system
    if not dry_run:
        try:
            rag_system = InMemoryRAG()
            print(f"✅ RAG system initialized")
            print(f"📊 Current knowledge base size: {len(rag_system.knowledge_base)}")
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            return {"error": 1, "processed": 0, "failed": 0}
    else:
        rag_system = None
    
    # Scan for files
    files_to_process = scan_uploads_folder(uploads_path)
    
    if not files_to_process:
        print("ℹ️  No files found to process")
        return {"processed": 0, "failed": 0, "skipped": 0}
    
    print(f"\n📋 Found {len(files_to_process)} files to process")
    
    # Process each file
    stats = {"processed": 0, "failed": 0, "skipped": 0}
    
    for file_path, filename in files_to_process:
        # Determine category
        category = get_file_category(filename, custom_categories)
        
        if dry_run:
            print(f"🔍 Would process: {filename} → Category: {category}")
            stats["processed"] += 1
        else:
            # Check if file is already processed (optional - can be enhanced)
            success = process_file(file_path, filename, category, rag_system)
            
            if success:
                stats["processed"] += 1
            else:
                stats["failed"] += 1
    
    # Print final statistics
    print(f"\n📊 Processing Summary:")
    print(f"  ✅ Processed: {stats['processed']}")
    print(f"  ❌ Failed: {stats['failed']}")
    print(f"  ⏭️  Skipped: {stats.get('skipped', 0)}")
    
    if not dry_run and rag_system:
        print(f"📈 Final knowledge base size: {len(rag_system.knowledge_base)}")
    
    return stats

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Process existing files in uploads folder")
    parser.add_argument(
        "--uploads-path", 
        default="uploads", 
        help="Path to uploads folder (default: uploads)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be processed without actually doing it"
    )
    parser.add_argument(
        "--category", 
        action="append", 
        nargs=2, 
        metavar=("PATTERN", "CATEGORY"),
        help="Custom category mapping (can be used multiple times)"
    )
    
    args = parser.parse_args()
    
    # Build custom categories dictionary
    custom_categories = {}
    if args.category:
        for pattern, category in args.category:
            custom_categories[pattern] = category
    
    # Process files
    stats = process_uploads_folder(
        uploads_path=args.uploads_path,
        custom_categories=custom_categories,
        dry_run=args.dry_run
    )
    
    # Exit with appropriate code
    if stats.get("error"):
        sys.exit(1)
    elif stats["failed"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

