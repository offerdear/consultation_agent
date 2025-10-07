#!/usr/bin/env python3
"""
Simple startup processor that can be imported and called from the main application.
This provides a clean interface for processing uploads folder on startup.
"""

import os
from typing import Dict, Optional
from process_uploads import process_uploads_folder
from file_tracker import get_processed_files, mark_file_processed, clear_processed_files

def process_existing_uploads(
    uploads_path: str = "uploads",
    custom_categories: Optional[Dict[str, str]] = None,
    verbose: bool = True
) -> Dict[str, int]:
    """
    Process existing files in uploads folder and add them to knowledge base.
    
    Args:
        uploads_path: Path to uploads folder
        custom_categories: Custom category mapping
        verbose: Whether to print progress messages
    
    Returns:
        Dictionary with processing statistics
    """
    if verbose:
        print("🔄 Processing existing files in uploads folder...")
    
    # Default custom categories for common file patterns
    default_categories = {
        'curriculum': 'Curriculum',
        'pricing': 'Pricing', 
        'teacher': 'Teachers',
        'general': 'General Information',
        'guide': 'User Guide',
        'manual': 'User Guide',
    }
    
    # Merge with provided custom categories
    if custom_categories:
        default_categories.update(custom_categories)
    
    # Process files
    stats = process_uploads_folder(
        uploads_path=uploads_path,
        custom_categories=default_categories,
        dry_run=False
    )
    
    if verbose:
        if stats.get("error"):
            print("❌ Error occurred during processing")
        elif stats["failed"] > 0:
            print(f"⚠️  Processing completed with {stats['failed']} failures")
        else:
            print("✅ All files processed successfully")
    
    return stats


def should_process_uploads() -> bool:
    """
    Check if uploads folder should be processed.
    Only processes files that haven't been processed yet.
    
    Returns:
        True if there are unprocessed files
    """
    uploads_path = "uploads"
    
    print("In should_process_uploads")

    # Check if uploads folder exists
    if not os.path.exists(uploads_path):
        print(f"📁 Uploads folder does NOT exist: {uploads_path}")
        return False
    
    print(f"Uploads folder exists {uploads_path}")
    
    # Get list of already processed files
    processed_files = get_processed_files()
    print(f"processed files {processed_files}")
    # Check for unprocessed supported files
    supported_extensions = {'.pdf', '.rtf', '.txt', '.docx'}
    
    for filename in os.listdir(uploads_path):
        print(f"filename {filename}")
        if os.path.isfile(os.path.join(uploads_path, filename)):
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext in supported_extensions and filename not in processed_files:
                print("File is supported and not processed")
                return True
    
    return False


if __name__ == "__main__":
    # Can be run standalone for testing
    if should_process_uploads():
        stats = process_existing_uploads()
        print(f"Processing completed: {stats}")
    else:
        print("No files to process in uploads folder")

