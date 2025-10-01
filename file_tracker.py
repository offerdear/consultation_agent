#!/usr/bin/env python3
"""
File tracking utilities to prevent duplicate adding of files.
"""

import os
import json
from typing import Set

"""Get set of files which have already been processed"""
def get_processed_files() -> Set[str]:
    processed_file = "processed_files.json"
    if os.path.exists(processed_file):
        try:
            with open(processed_file, 'r') as f:
                data = json.load(f)
                return set(data.get('processed_files', []))
        except:
            return set()
    return set()

def mark_file_processed(filename: str):
    """Mark a file as processed"""
    processed_file = "processed_files.json"
    processed_files = get_processed_files()
    processed_files.add(filename)
    
    try:
        with open(processed_file, 'w') as f:
            json.dump({'processed_files': list(processed_files)}, f)
    except Exception as e:
        print(f"Warning: Could not save processed files list: {e}")

def clear_processed_files():
    """Clear the list of processed files (useful for reprocessing all files)"""
    processed_file = "processed_files.json"
    if os.path.exists(processed_file):
        os.remove(processed_file)
        print("✅ Cleared processed files list")
