# /api/clear
from rag_inmemory import InMemoryRAG 
from utils import clear_knowledge_base
from file_tracker import clear_processed_files

rag = InMemoryRAG()

clear_knowledge_base(rag)
clear_processed_files()

