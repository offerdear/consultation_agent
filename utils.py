from typing import List, Tuple, Dict
import os

"""Store embeddings with metadata in the in-memory RAG system"""
def store_embeddings_with_metadata(rag_system, chunk_tuples: List[Tuple[str, Dict]]):
    if not chunk_tuples:
        print("⚠️ Warning: No chunks provided to store")
        return
    
    # Filter out empty chunks
    valid_chunks = [(text, metadata) for text, metadata in chunk_tuples 
                   if text and text.strip()]
    
    if not valid_chunks:
        print("⚠️ Warning: No valid chunks found after filtering")
        return
    
    print(f"Storing {len(valid_chunks)} chunks with embeddings...")
    
    # Use batch method for efficiency
    doc_ids = rag_system.add_knowledge_batch(valid_chunks)
    
    print(f"✅ Successfully stored {len(doc_ids)} chunks in knowledge base")
    return doc_ids

"""Clear all knowledge from the RAG system"""
def clear_knowledge_base(rag_system):
    rag_system.clear_knowledge_base()
    print("✅ Knowledge base cleared")

"""Statistics about knowledge base"""
def get_knowledge_stats(rag_system):
    total_items = len(rag_system.knowledge_base)
    
    if total_items == 0:
        print("📊 Knowledge base is empty")
        return
    
    # Count by category
    categories = {}
    types = {}
    
    for item in rag_system.knowledge_base:
        metadata = item.get('metadata', {})
        
        category = metadata.get('category', 'Unknown')
        doc_type = metadata.get('type', 'Unknown')
        
        categories[category] = categories.get(category, 0) + 1
        types[doc_type] = types.get(doc_type, 0) + 1
    
    print(f"📊 Knowledge Base Statistics:")
    print(f"  Total items: {total_items}")
    print(f"  Categories: {len(categories)} - {dict(list(categories.items())[:5])}")
    print(f"  Types: {len(types)} - {dict(list(types.items())[:5])}")

"""To create a backup of the knowledge base"""
def backup_knowledge_base(rag_system, backup_path: str = "./backup"):
    import shutil
    import datetime
    
    os.makedirs(backup_path, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_path, f"rag_backup_{timestamp}")
    
    try:
        # Copy the entire persist directory
        shutil.copytree(rag_system.persist_directory, backup_dir)
        print(f"✅ Backup created at: {backup_dir}")
        return backup_dir
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

"""Restore knowledge base from a backup"""
def restore_knowledge_base(rag_system, backup_path: str):
    import shutil
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup path does not exist: {backup_path}")
        return False
    
    try:
        # Remove current data
        if os.path.exists(rag_system.persist_directory):
            shutil.rmtree(rag_system.persist_directory)
        
        # Restore from backup
        shutil.copytree(backup_path, rag_system.persist_directory)
        
        # Reload the data
        rag_system.load_persisted_data()
        
        print(f"✅ Knowledge base restored from: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

"""Search knowledge base by metadata only (no semantic search)"""
def search_knowledge_by_metadata(rag_system, **metadata_filters) -> List[Dict]:
    results = []
    
    for item in rag_system.knowledge_base:
        metadata = item.get('metadata', {})
        match = True
        
        for key, value in metadata_filters.items():
            if key not in metadata or metadata[key] != value:
                match = False
                break
        
        if match:
            results.append({
                'id': item['id'],
                'content': item['content'],
                'metadata': metadata,
                'timestamp': item.get('timestamp', 'Unknown')
            })
    
    return results

"""Export knowledge base to JSON file"""
def export_knowledge_to_json(rag_system, output_path: str):
    import json
    
    # Prepare data for JSON export (exclude embeddings for size)
    export_data = []
    for item in rag_system.knowledge_base:
        export_item = {
            'id': item['id'],
            'content': item['content'],
            'metadata': item['metadata'],
            'timestamp': item.get('timestamp', 'Unknown')
        }
        export_data.append(export_item)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Knowledge base exported to: {output_path}")
        print(f"📊 Exported {len(export_data)} items")
        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False