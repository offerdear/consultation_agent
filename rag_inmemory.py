import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple
import uuid
import json
import pickle
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from consultation_engine import ConsultationEngine
import re
from openai import OpenAI

# Load environment variables
load_dotenv()

class InMemoryRAG:
    """Initialize In-Memory RAG system"""
    def __init__(self, persist_directory: str = "./vector_cache"):
        
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable. Check your .env file.")

        # Initialize OpenAI client (AI-first approach)
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Storage for knowledge base and context
        self.knowledge_base: List[Dict] = []  # List of {id, content, metadata, embedding}
        self.context_base: List[Dict] = []    # List of conversation contexts
        
        # File paths for persistence
        self.persist_directory = persist_directory
        self.knowledge_file = os.path.join(persist_directory, "knowledge_base.pkl")
        self.context_file = os.path.join(persist_directory, "context_base.pkl")
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Load persisted data if avail
        self.load_persisted_data()
    
        # New conversation modes
        self.conversation_mode = None  # 'faq' or 'consultation'

        
        # ? Categories - TBD
        self.categories = ["Curriculum", "Pricing", "Teachers", "Textbooks", "About Us", "Contact", "Other"]
        
        # Conversation state
        self.conversation_history: List[Dict] = []
        self.current_session_id = str(uuid.uuid4())
        self.active_procedures: Dict[str, Dict] = {}
        
        # Dynamic device attributes
        self.selected_category: Optional[str] = None
        
        print("✅ In-Memory RAG System initialized successfully!")
        print(f"✅ Session ID: {self.current_session_id}")
        print(f"✅ Knowledge base items: {len(self.knowledge_base)}")
        print(f"✅ Context items: {len(self.context_base)}")
    

    """Load persisted knowledge and context from files"""
    def load_persisted_data(self):
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'rb') as f:
                    self.knowledge_base = pickle.load(f)
                print(f"✅ Loaded {len(self.knowledge_base)} items from knowledge cache")
        except Exception as e:
            print(f"⚠️  Could not load knowledge cache: {e}")
            self.knowledge_base = []
        
        try:
            if os.path.exists(self.context_file):
                with open(self.context_file, 'rb') as f:
                    self.context_base = pickle.load(f)
                print(f"✅ Loaded {len(self.context_base)} items from context cache")
        except Exception as e:
            print(f"⚠️  Could not load context cache: {e}")
            self.context_base = []
    
    """Save knowledge and context to files for persistence"""
    def save_persisted_data(self):
        try:
            with open(self.knowledge_file, 'wb') as f:
                pickle.dump(self.knowledge_base, f)
            print(f"✅ Saved {len(self.knowledge_base)} items to knowledge cache")
        except Exception as e:
            print(f"❌ Could not save knowledge cache: {e}")
        
        try:
            with open(self.context_file, 'wb') as f:
                pickle.dump(self.context_base, f)
            print(f"✅ Saved {len(self.context_base)} items to context cache")
        except Exception as e:
            print(f"❌ Could not save context cache: {e}")
    
    def get_categories(self) -> List[str]:
        """Get all available information categories"""
        return list(self.categories)

    '''
    def get_all_info_for_category(self, category: str) -> List[Dict]:
        """Get all info for a specific category"""
        if category not in self.categories:
            return []
        
        return  -- self.categories[categor]
    '''
    

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI API"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [embedding.embedding for embedding in response.data]
    

    def add_knowledge(self, content: str, metadata: Dict = None) -> str:
        """Add content to knowledge base with embeddings"""
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        
        doc_id = str(uuid.uuid4())
        
        # Get embedding for the content
        embedding = self.get_embeddings([content])[0]
        
        # Create knowledge item
        knowledge_item = {
            'id': doc_id,
            'content': content,
            'metadata': metadata or {},
            'embedding': embedding,
            'timestamp': datetime.now().isoformat()
        }
        
        self.knowledge_base.append(knowledge_item)
        
        # Save to disk
        self.save_persisted_data()
        return doc_id

    
    def add_knowledge_batch(self, content_tuples: List[Tuple[str, Dict]]):
        """Add multiple content items to knowledge base efficiently"""
        if not content_tuples:
            return []
        
        # Extract content and metadata
        contents = [item[0] for item in content_tuples if item[0] and item[0].strip()]
        metadatas = [item[1] if len(item) > 1 else {} for item in content_tuples if item[0] and item[0].strip()]
        
        if not contents:
            return []
        
        # Get embeddings for all content at once
        embeddings = self.get_embeddings(contents)
        
        doc_ids = []
        for content, metadata, embedding in zip(contents, metadatas, embeddings):
            doc_id = str(uuid.uuid4())
            
            knowledge_item = {
                'id': doc_id,
                'content': content,
                'metadata': metadata or {},
                'embedding': embedding,
                'timestamp': datetime.now().isoformat()
            }
            
            self.knowledge_base.append(knowledge_item)
            doc_ids.append(doc_id)
        
        # Save to disk
        self.save_persisted_data()
        print(f"✅ Added {len(doc_ids)} items to knowledge base")
        
        return doc_ids
    

    def search_knowledge_base(self, query: str, limit: int = 5, filters: Dict = None) -> List[Dict]:
        """Search the knowledge base using cosine similarity"""
        if not self.knowledge_base:
            return []
        
        # Get query embedding
        query_embedding = self.get_embeddings([query])[0]
        
        # Apply filters if provided
        filtered_items = self.knowledge_base
        if filters:
            filtered_items = []
            for item in self.knowledge_base:
                metadata = item.get('metadata', {})
                match = True
                
                # Check each filter
                for key, value in filters.items():
                    if key in metadata:
                        if isinstance(value, list):
                            if metadata[key] not in value:
                                match = False
                                break
                        else:
                            if metadata[key] != value:
                                match = False
                                break
                    else:
                        match = False
                        break
                
                if match:
                    filtered_items.append(item)
        
        if not filtered_items:
            return []
        
        # Calculate similarities
        embeddings = [item['embedding'] for item in filtered_items]
        similarities = cosine_similarity([query_embedding], embeddings)[0]
        
        # Create results with similarity scores
        results = []
        for item, similarity in zip(filtered_items, similarities):
            results.append({
                'content': item['content'],
                'metadata': item['metadata'],
                'relevance': float(similarity),
                'id': item['id']
            })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:limit]
    
    def save_context(self, user_input: str, response: str, metadata: Dict = None):
        """Save conversation context to memory"""
        if not user_input or not response:
            return
        
        context_entry = {
            'id': str(uuid.uuid4()),
            'user_input': user_input,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.current_session_id
        }
        
        if metadata:
            context_entry.update(metadata)
        
        # Add to conversation history
        self.conversation_history.append(context_entry)
        
        # Create searchable context content
        context_content = f"User: {user_input}\nAssistant: {response}"
        
        # Get embedding for context
        try:
            embedding = self.get_embeddings([context_content])[0]
            context_entry['content'] = context_content
            context_entry['embedding'] = embedding
            
            # Add to context base
            self.context_base.append(context_entry)
            
            # Save to disk
            self.save_persisted_data()
        except Exception as e:
            print(f"⚠️  Error saving context embedding: {e}")
    
    def get_relevant_context(self, query: str, limit: int = 3) -> List[Dict]:
        """Retrieve relevant conversation context"""
        if not self.context_base:
            return []
        
        # Filter by current session
        session_contexts = [ctx for ctx in self.context_base 
                          if ctx.get("session_id") == self.current_session_id]
        
        if not session_contexts:
            return []
        
        # Get query embedding
        query_embedding = self.get_embeddings([query])[0]
        
        # Calculate similarities
        embeddings = [ctx['embedding'] for ctx in session_contexts if 'embedding' in ctx]
        valid_contexts = [ctx for ctx in session_contexts if 'embedding' in ctx]
        
        if not embeddings:
            return []
        
        similarities = cosine_similarity([query_embedding], embeddings)[0]
        
        # Create results
        results = []
        for ctx, similarity in zip(valid_contexts, similarities):
            results.append({
                "content": ctx.get("content", ""),
                "metadata": {k: v for k, v in ctx.items() if k not in ['content', 'embedding']},
                "relevance": float(similarity)
            })
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:limit]
    
    
    def _format_numbered_lists(self, text: str) -> str:
        """Format numbered lists to have proper line breaks between items"""
        # Pattern to match numbered lists (1. 2. 3. etc.)
        pattern = r'(\d+\.\s+[^1-9]*?)(?=\d+\.|$)'
        
        def replace_list(match):
            item = match.group(1).strip()
            return item + '\n'
        
        formatted_text = re.sub(pattern, replace_list, text)
        
        # Handle patterns like "1) text 2) text 3) text"
        pattern2 = r'(\d+\)\s+[^1-9]*?)(?=\d+\)|$)'
        formatted_text = re.sub(pattern2, replace_list, formatted_text)
        
        formatted_text = formatted_text.rstrip('\n')
        return formatted_text
    

    def generate_agentic_response(self, user_input: str, session_id: str = None, mode: str = None, category=None) -> str:
        """Enhanced response generation with consultation flow support"""
    
        if mode == 'Consultation':
            # For backward compatibility, handle simple text consultation
            result = consultation_engine.handle_message(user_input, session_id or self.current_session_id, 'text')
            return result.get('response', 'Error processing consultation')
            
        elif mode == 'FAQ':
            # Existing FAQ logic
            return self.generate_agentic_response_faq(user_input, category)
        else:
            # Handle initial mode selection
            return self.handle_initial_selection(user_input)

    def handle_initial_selection(self, user_input: str) -> str:
        """Handle when user hasn't selected a mode yet"""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ['consultation', 'assess', 'test', 'level', 'recommend']):
            return "I'll help you with a consultation! Please click the 'Consultation' button above to get started with our interactive assessment."
        elif any(word in user_lower for word in ['question', 'faq', 'info', 'about', 'price', 'teacher']):
            return "I'd be happy to answer your questions! Please click the 'FAQ' button above and select which topic you'd like to know about."
        else:
            return "I can help you with either:\n\n**Consultation** - Get personalized course recommendations through an interactive assessment\n\n**FAQ** - Answer questions about our programs, pricing, teachers, etc.\n\nPlease select one of the options above to get started!"

    """Generate context-aware response with agentic behavior"""
    def generate_agentic_response_faq(self, user_input: str, category=None) -> str:
        
        # Update selected attributes if provided
        if category is not None:
            self.selected_category = category

        print(f"🔍 Processing: {user_input}")
        print(f"📋 Context - Category: {self.selected_category}")
        
        # Get relevant context from conversation
        context_history = self.get_relevant_context(user_input, limit=3)
        
        # Build filters for knowledge search
        filters = {}
        if self.selected_category:
            filters['category'] = self.selected_category
        
        # Search knowledge base
        knowledge_items = self.search_knowledge_base(user_input, limit=5, filters=filters if filters else None)
        
        print(f'📚 Found {len(knowledge_items)} knowledge items')
        print(f'💬 Found {len(context_history)} context items')
        
         
        # Build prompt with context
        system_prompt = self._build_system_prompt(None)  # changed from context_history to None
        user_prompt = self._build_user_prompt(user_input, context_history, knowledge_items)
        
        # Generate response
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        assistant_response = response.choices[0].message.content
        
        # Format the response to improve numbered list formatting
        formatted_response = self._format_numbered_lists(assistant_response)
        
        # Save this interaction to context
        self.save_context(user_input, formatted_response, {
            "knowledge_items_used": len(knowledge_items),
            "context_items_used": len(context_history),
            "selected_category": self.selected_category,
        })
        
        return formatted_response
    
    """Build system prompt based on current context"""
    def _build_system_prompt(self, procedure_context: Optional[Dict]=None) -> str:
        
        '''
        # Build product context
        product_context = ""
        if self.selected_category or self.selected_product:
            product_context = f"\n\nPRODUCT CONTEXT:"
            if self.selected_category:
                product_context += f"\n- Category: {self.selected_category}"
            if self.selected_product:
                # Find product details
                if self.products_df is not None and not self.products_df.empty:
                    product_row = self.products_df[self.products_df['Product_ID'] == self.selected_product]
                    if not product_row.empty:
                        product_name = product_row.iloc[0]['Product_Name']
                        product_context += f"\n- Product: {product_name} (ID: {self.selected_product})"
        '''

        # Available categories for context
        categories_context = ""
        if self.categories:
            categories_list = self.get_categories()
            categories_context = f"\n\nAVAILABLE CATEGORIES: {categories_list}"
        
        base_prompt = f"""
            You are a friendly English education consultant helping Chinese parents find the right 
            online English courses for their children.

            Your role is to:
            - Guide parents through course selection and answer their questions
            - Conduct English proficiency assessments when needed
            - Recommend appropriate course packages
            - Help with enrollment and next steps
            - Remember previous conversation details to avoid repetition
            - Give detailed, accurate and valuable information for them to make an informed decision
            - Use specifics when possible and give concrete names, examples, and details
            - Include specific details and the names of our teachers, who have consented to share their information 

            **Communication Style:**
            - Use a warm, conversational tone (like talking to a friend, but professional)
            - Break up information with bullet points and short paragraphs
            - Use emojis sparingly for warmth (📚 ✨ 👍)
            - Speak in both Chinese and English as appropriate
            - **Use bold for important facts, prices, titles, and key benefits**
            - *Use italics for emphasis on special offers, deadlines, or notable details*
            - Use italics and bolding when there is something to be emphasized, like a discount or key fact
            - Keep responses scannable - avoid long walls of text

            **Formatting Examples:**
            - "**Level 4**: Intermediate"
            - "**Special offer**: *First month only ¥299* (regular price ¥399)"
            - "The assessment takes just **10 minutes** and gives you a *detailed proficiency report*"

            **Key Behaviors:**
            - Ask ONE clarifying question at a time
            - Summarize what you've learned before moving to next topics
            - Give specific examples when explaining courses or teaching methods
            - If parents seem hesitant, address concerns directly
            - Always end with a clear next step

            **When to escalate to human:**
            - Scheduling direct appointments 
            - Technical payment issues  
            - Concerns about specific individuals or childrens' specific needs
            - Any question you're uncertain about

            **Remember:** 
            - Don't re-ask for information already provided (child's name, age, etc.)
            - Focus on the child's learning goals and current level
            - Parents want confidence their investment will help their child succeed

            Ready to help parents find the perfect English learning path for their child! 
        """
        
        # Add context
        base_prompt += categories_context
        
        if procedure_context and isinstance(procedure_context, dict):
            base_prompt += f"""
                ACTIVE CONSULTATION CONTEXT:
                - Currently working on: {', '.join(procedure_context.get('active_procedures', []))}
                - Current step type: {procedure_context.get('current_step_type', 'unknown')}
                - Follow the user flow systematically
                - Ask context questions before proceeding with steps
                - Guide the user through each question ro concern
            """
                
        return base_prompt
    
    """Build user prompt with relevant context and knowledge"""
    def _build_user_prompt(self, user_input: str, context_history: List[Dict], knowledge_items: List[Dict]) -> str:
        
        prompt_parts = []
        
        # Add conversation context
        if context_history:
            prompt_parts.append("RECENT CONVERSATION CONTEXT:")
            for ctx in context_history[-3:]:  # Last 3 relevant exchanges
                prompt_parts.append(f"- {ctx['content'][:200]}...")
            prompt_parts.append("")
        
        # Add relevant knowledge
        if knowledge_items:
            prompt_parts.append("RELEVANT KNOWLEDGE:")
            for item in knowledge_items:
                item_type = item['metadata'].get('type', 'unknown')
                content = item['content'][:300]
                prompt_parts.append(f"[{item_type.upper()}] {content}")
            prompt_parts.append("")
        
        # Add current user input
        prompt_parts.append(f"CURRENT USER INPUT: {user_input}")
        prompt_parts.append("")
        prompt_parts.append("Please provide a helpful, context-aware response:")
        
        return "\n".join(prompt_parts)
    
    """Get current system status"""
    def get_system_status(self):
        print(f"📊 System Status:")
        print(f"  Knowledge items: {len(self.knowledge_base)}")
        print(f"  Context entries: {len(self.context_base)}")
        print(f"  Current session: {self.current_session_id}")
        print(f"  Conversation turns: {len(self.conversation_history)}")
        print(f"  Categories loaded: {len(self.categories)}")
        print(f"  Selected category: {self.selected_category}")
    
    """Clear all knowledge base items"""
    def clear_knowledge_base(self):
        self.knowledge_base = []
        self.save_persisted_data()
        print("✅ Knowledge base cleared")
    
    """Clear conversation context"""
    def clear_context(self):
        self.context_base = []
        self.conversation_history = []
        self.save_persisted_data()
        print("✅ Context cleared")
