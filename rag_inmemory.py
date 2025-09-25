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


class ConsultationManager:
    """Simple consultation manager to track per-session consultation state.

    This is intentionally lightweight. It tracks basic info collection, the
    current stage, and stores answers to assessment questions.
    """
    def __init__(self):
        # consultations keyed by session_id
        self._consultations: Dict[str, Dict] = {}

    def start_consultation(self, session_id: str) -> Dict:
        consultation = {
            'session_id': session_id,
            'stage': 'basic_info',  # basic_info -> assessment_active -> recommendation -> completed
            'data': {},
            'assessment_index': 0,
            'assessment_answers': [],
            'created_at': datetime.now().isoformat()
        }
        self._consultations[session_id] = consultation
        return consultation

    def get_consultation(self, session_id: str) -> Optional[Dict]:
        return self._consultations.get(session_id)

    def process_basic_info(self, session_id: str, text: str) -> Tuple[str, bool]:
        """Try to extract a name/age/level/goal from free-text and advance stage.

        Returns a tuple (response_text, stage_complete_bool).
        """
        consultation = self._consultations.get(session_id)
        if not consultation:
            consultation = self.start_consultation(session_id)

        data = consultation['data']

        # Very simple extraction heuristics
        text_lower = text.lower()
        if 'name is' in text_lower or 'i am' in text_lower or 'my name' in text_lower:
            # crude name extraction
            parts = text.split()
            if len(parts) >= 2:
                data['name'] = parts[1].strip('.,')

        # age
        age_match = re.search(r"(\d{1,2})\s*(?:years|yrs|y/o|yo|old)", text_lower)
        if age_match:
            data['age'] = int(age_match.group(1))

        # level keywords
        for level in ['beginner', 'intermediate', 'advanced']:
            if level in text_lower:
                data['level'] = level

        # goal
        if 'improve' in text_lower or 'learn' in text_lower or 'practice' in text_lower:
            data.setdefault('goals', []).append(text.strip())

        # If user explicitly asks to start assessment or we have a level, move on
        if 'start assessment' in text_lower or 'assessment' in text_lower or data.get('level'):
            consultation['stage'] = 'assessment_active'
            consultation['assessment_index'] = 0
            self.assessment_engine.handle_assessment_question(user_input, session_id)
            return ("Great — we'll begin a short language assessment now.", True)

        # Otherwise ask a basic follow-up
        prompt = "Thanks ${name} — could you tell me your (or your child's) current English level (beginner/intermediate/advanced) and a brief goal?"
        return (prompt, False)


class AssessmentEngine:
    """Lightweight assessment engine that serves a fixed set of questions and scores them.

    The real implementation would use validated assessment items. This placeholder
    uses simple multiple-choice scoring to generate a level estimate.
    """
    def __init__(self):
        # static question set
        self.questions = [
            { 'id': 'q1', 'question': 'Choose the sentence that is correct:\n1) He go to school.\n2) He goes to school.\n3) He going to school.', 'choices': [1,2,3] },
            { 'id': 'q2', 'question': 'Select the best response: "How are you?"\n1) I am fine, thanks.\n2) Fine is me.\n3) Me fine.', 'choices': [1,2,3] },
            { 'id': 'q3', 'question': 'Choose the correct past tense:\n1) I eat yesterday.\n2) I ate yesterday.\n3) I eated yesterday.', 'choices': [1,2,3] }
        ]

    def get_next_question(self, session_id: str, consultation: Dict) -> Optional[Dict]:
        idx = consultation.get('assessment_index', 0)
        if idx >= len(self.questions):
            return None
        q = self.questions[idx]
        return { 'index': idx, 'question': q['question'], 'choices': q.get('choices') }

    def process_answer(self, session_id: str, consultation: Dict, answer) -> Dict:
        """Record answer and return next question or final result.

        `answer` can be an integer index (1-based) or free text containing a number.
        """
        idx = consultation.get('assessment_index', 0)
        if idx >= len(self.questions):
            return { 'finished': True, 'result': self._compute_result(consultation) }

        # Normalize answer
        try:
            if isinstance(answer, int):
                selected = int(answer)
            else:
                # try to extract a number from text
                m = re.search(r"(\d+)", str(answer))
                selected = int(m.group(1)) if m else None
        except Exception:
            selected = None

        consultation.setdefault('assessment_answers', []).append({ 'index': idx, 'answer': selected })
        consultation['assessment_index'] = idx + 1

        if consultation['assessment_index'] >= len(self.questions):
            # finished
            result = self._compute_result(consultation)
            consultation['stage'] = 'recommendation'
            return { 'finished': True, 'result': result }

        # return next question
        next_q = self.get_next_question(session_id, consultation)
        return { 'finished': False, 'next_question': next_q }

    def _compute_result(self, consultation: Dict) -> Dict:
        """Very simple scoring: count correct answers (we treat choice '2' as correct in our sample set)."""
        answers = consultation.get('assessment_answers', [])
        score = 0
        for a in answers:
            if a.get('answer') == 2:
                score += 1

        # Map to proficiency
        if score <= 1:
            level = 'beginner'
        elif score == 2:
            level = 'intermediate'
        else:
            level = 'advanced'

        consultation['assessment_result'] = { 'score': score, 'level': level }
        return consultation['assessment_result']
    
    def handle_assessment_question(self, user_input: str, session_id: str) -> str:
        """Process user input as an answer to the current assessment question."""
        consultation = rag.consultation_manager.get_consultation(session_id)
        if not consultation or consultation['stage'] != 'assessment_active':
            return "No active assessment found. Please start a new consultation."

        return "Next question placeholder"

        result = self.process_answer(session_id, consultation, user_input)
        if result['finished']:
            res = result['result']
            return f"Assessment complete! Your estimated level is '{res['level']}' with a score of {res['score']}. I'll now provide course recommendations."
        else:
            next_q = result['next_question']
            return f"Next question:\n{next_q['question']}"


class CourseRecommendationEngine:
    """Simple rule-based recommendation engine.

    Uses consultation data and assessment results to suggest courses.
    """
    def __init__(self):
        # Example course catalog (would normally come from a DB)
        self.catalog = {
            'beginner': [
                { 'id': 'beg-101', 'title': 'English Foundations', 'length_weeks': 8 },
                { 'id': 'beg-201', 'title': 'Everyday English', 'length_weeks': 6 }
            ],
            'intermediate': [
                { 'id': 'int-101', 'title': 'Grammar & Conversation', 'length_weeks': 10 },
            ],
            'advanced': [
                { 'id': 'adv-101', 'title': 'Advanced Communication', 'length_weeks': 12 }
            ]
        }

    def recommend(self, consultation: Dict) -> Dict:
        result = consultation.get('assessment_result', {})
        level = result.get('level') or consultation.get('data', {}).get('level') or 'beginner'

        # pick top 2 courses for the level
        courses = self.catalog.get(level, [])[:2]

        recommendation = {
            'level': level,
            'recommended_courses': courses,
            'reason': f"Recommended based on assessment level '{level}' and stated goals."
        }
        consultation['recommendation'] = recommendation
        consultation['stage'] = 'recommendation'
        return recommendation


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
        
        # Load persisted data if available
        self.load_persisted_data()

        # Add consultation components
        self.consultation_manager = ConsultationManager()
        self.assessment_engine = AssessmentEngine()
        self.recommendation_engine = CourseRecommendationEngine()
    
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


    def handle_consultation_flow(self, user_input: str, session_id: str):
        """Handle structured consultation conversation"""
        consultation = self.consultation_manager.get_consultation(session_id)
        
        if not consultation:
            consultation = self.consultation_manager.start_consultation(session_id)
        
        stage = consultation['stage']
        
        while (stage != 'complete'):
            if stage == 'basic_info':
                response, stage_complete = self.consultation_manager.process_basic_info(session_id, user_input)
            
            elif stage == 'assessment_active':
                self.assessment_engine.handle_assessment_question(user_input, session_id)
            
            elif stage == 'recommendation':
                self.recommendation_engine.handle_course_recommendation(session_id)
                stage = 'complete'
            else:
                continue
        return "Consultation complete."      

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
        
        # Determine if this is part of a diagnostic procedure
        procedure_context = self._analyze_procedure_state(user_input, knowledge_items)
        
        # Build prompt with context
        system_prompt = self._build_system_prompt(procedure_context)
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
            "procedure_active": bool(procedure_context),
            "selected_category": self.selected_category,
        })
        
        return formatted_response
    

    """Analyze if user is in the middle of a diagnostic procedure"""
    """??????"""
    def _analyze_procedure_state(self, user_input: str, knowledge_items: List[Dict]) -> Optional[Dict]:
        
        # Look for diagnostic-related keywords in knowledge items
        diagnostic_items = [item for item in knowledge_items
                          if item['metadata'].get('type') in ['diagnostic_step', 'context_question', 'symptom']]
        
        if diagnostic_items:
            # Check if there's an active procedure
            procedures = set(item['metadata'].get('procedure') for item in diagnostic_items)
            if procedures:
                return {
                    'active_procedures': list(procedures),
                    'current_step_type': diagnostic_items[0]['metadata'].get('type'),
                    'diagnostic_items': diagnostic_items
                }
        
        return None
    
    """Build system prompt based on current context"""
    def _build_system_prompt(self, procedure_context: Optional[Dict]) -> str:
        
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
            - Complex scheduling conflicts
            - Specific teacher requests
            - Technical payment issues  
            - Concerns about teaching quality
            - Any question you're uncertain about

            **Remember:** 
            - Don't re-ask for information already provided (child's name, age, etc.)
            - Focus on the child's learning goals and current level
            - Parents want confidence their investment will help their child succeed

            Ready to help parents find the perfect English learning path for their child! 
        """
        
        # Add context
        base_prompt += categories_context
        
        if procedure_context:
            base_prompt += f"""
                ACTIVE DIAGNOSTIC CONTEXT:
                - Currently working on: {', '.join(procedure_context['active_procedures'])}
                - Current step type: {procedure_context['current_step_type']}
                - Follow the diagnostic flow systematically
                - Ask context questions before proceeding with steps
                - Guide the user through each verification step
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