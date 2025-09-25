# consultation_engine.py - New dedicated file
class ConsultationEngine:
    """Interactive consultation engine that returns structured UI data"""
    
    def __init__(self, rag_system):
        self.rag = rag_system
        self.sessions = {}

    def handle_message(self, user_input: str, session_id: str, action_type: str = "text") -> dict:
        """
        Handle consultation messages and return structured response
        
        Args:
            user_input: User's text input or action data
            session_id: Session identifier
            action_type: "text", "button_click", "form_submit", etc.
            
        Returns:
            dict with response text, UI elements, and next actions
        """
        session = self.get_or_create_session(session_id)
        
        # Route based on current stage
        if session.stage == 'welcome':
            return self._handle_welcome(user_input, session, action_type)
        elif session.stage == 'basic_info':
            return self._handle_basic_info(user_input, session, action_type)
        elif session.stage == 'assessment_intro':
            return self._handle_assessment_intro(user_input, session, action_type)
        elif session.stage == 'assessment_active':
            return self._handle_assessment_question(user_input, session, action_type)
        elif session.stage == 'recommendations':
            return self._handle_recommendations(user_input, session, action_type)
        else:
            return self._create_error_response("Invalid session state")

    def get_or_create_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = ConsultationSession(session_id)
        return self.sessions[session_id]

    """Handle initial welcome and name collection"""
    def _handle_welcome(self, user_input: str, session: 'ConsultationSession', action_type: str) -> dict:
        
        if action_type == "form_submit":
            # Handle form data submission
            import json
            try:
                form_data = json.loads(user_input) if isinstance(user_input, str) else user_input
                if 'name' in form_data and form_data['name'].strip():
                    session.data['name'] = form_data['name'].strip()
                    session.stage = 'basic_info'
                    return self._create_basic_info_response(session)
            except:
                pass  # Fall through to show form again
        
        elif action_type == "text":
            # Try to extract name from natural input
            extracted = self._extract_name(user_input)
            if extracted:
                session.data['name'] = extracted
                session.stage = 'basic_info'
                return self._create_basic_info_response(session)
    
        # Show name input form if no name detected or form_submit failed
        return {
            'response': "I'd love to help you find the perfect English program! Let's start with some basic information.",
            'ui_elements': {
                'type': 'form',
                'fields': [
                    {
                        'id': 'name',
                        'type': 'text',
                        'label': "What's your name (or your child's name)?",
                        'placeholder': 'Enter name here...',
                        'required': True
                    }
                ],
                'submit_button': 'Continue',
                'action': 'submit_name'
            },
            'stage': 'welcome',
            'allow_text_input': True,
            'text_fallback': "You can also just type your name if you prefer."
        }
        

    def _handle_basic_info(self, user_input: str, session: 'ConsultationSession', action_type: str) -> dict:
        """Handle age and level collection with smart buttons"""
        
        if action_type == "form_submit":
            # Handle form data (age, level)
            import json
            try:
                form_data = json.loads(user_input) if isinstance(user_input, str) else user_input
                session.data.update(form_data)
                session.stage = 'assessment_intro'
                return self._create_assessment_intro_response(session)
            except:
                return self._create_error_response("Invalid form data")
        
        if action_type == "button_click":
            # Handle individual button clicks (age ranges, levels)
            if user_input.startswith("age_"):
                age_range = user_input.replace("age_", "")
                session.data['age_range'] = age_range
            elif user_input.startswith("level_"):
                level = user_input.replace("level_", "")
                session.data['level'] = level
            
            # Check if we have enough info to proceed
            if 'age_range' in session.data and 'level' in session.data:
                session.stage = 'assessment_intro'
                return self._create_assessment_intro_response(session)
        
        # Show basic info collection interface
        return self._create_basic_info_response(session)

    def _create_basic_info_response(self, session: 'ConsultationSession') -> dict:
        """Create interactive basic info collection interface"""
        name = session.data.get('name', 'there')
        
        # Determine what we still need
        needs_age = 'age_range' not in session.data
        needs_level = 'level' not in session.data
        
        if needs_age and needs_level:
            response = f"Thanks {name}! Now I need to know a bit more to give you the best recommendations."
        elif needs_age:
            response = f"Great! Just need to know the age range."
        elif needs_level:
            response = f"Perfect! Last question - what's the current English level?"
        else:
            # Shouldn't happen, but fallback
            session.stage = 'assessment_intro'
            return self._create_assessment_intro_response(session)

        ui_elements = {'type': 'multi_section', 'sections': []}
        
        if needs_age:
            ui_elements['sections'].append({
                'title': 'Age Range',
                'type': 'button_grid',
                'buttons': [
                    {'id': 'age_3-6', 'text': '3-6 years', 'action': 'button_click'},
                    {'id': 'age_7-10', 'text': '7-10 years', 'action': 'button_click'},
                    {'id': 'age_11-14', 'text': '11-14 years', 'action': 'button_click'},
                    {'id': 'age_15-18', 'text': '15-18 years', 'action': 'button_click'}
                ]
            })
        
        if needs_level:
            ui_elements['sections'].append({
                'title': 'Current English Level',
                'type': 'button_grid', 
                'buttons': [
                    {'id': 'level_beginner', 'text': 'Beginner', 'subtitle': 'Just starting out', 'action': 'button_click'},
                    {'id': 'level_intermediate', 'text': 'Intermediate', 'subtitle': 'Can have basic conversations', 'action': 'button_click'},
                    {'id': 'level_advanced', 'text': 'Advanced', 'subtitle': 'Comfortable with most topics', 'action': 'button_click'},
                    {'id': 'level_unsure', 'text': 'Not Sure', 'subtitle': "Let's find out with the assessment!", 'action': 'button_click'}
                ]
            })

        return {
            'response': response,
            'ui_elements': ui_elements,
            'stage': 'basic_info',
            'allow_text_input': True,
            'text_fallback': "You can also type your answer if you prefer."
        }

    def _create_assessment_intro_response(self, session: 'ConsultationSession') -> dict:
        """Create assessment introduction with start button"""
        name = session.data.get('name', 'there')
        level = session.data.get('level', 'unknown')
        
        if level == 'unsure':
            response = f"Perfect {name}! Let's do a quick 5-question assessment to determine the best level. It will only take about 2 minutes."
        else:
            response = f"Great {name}! Even though you mentioned {level} level, I'd recommend doing a quick assessment to ensure we get you the perfect match. It's just 5 questions and takes about 2 minutes."

        return {
            'response': response,
            'ui_elements': {
                'type': 'action_buttons',
                'buttons': [
                    {
                        'id': 'start_assessment',
                        'text': 'Start Assessment',
                        'style': 'primary',
                        'action': 'button_click'
                    },
                    {
                        'id': 'skip_assessment', 
                        'text': 'Skip Assessment',
                        'style': 'secondary',
                        'action': 'button_click'
                    }
                ]
            },
            'stage': 'assessment_intro',
            'allow_text_input': False
        }

    def _handle_assessment_intro(self, user_input: str, session: 'ConsultationSession', action_type: str) -> dict:
        """Handle assessment start/skip decision"""
        if action_type == "button_click":
            if user_input == "start_assessment":
                session.stage = 'assessment_active'
                session.current_question = 0
                return self._get_assessment_question(session)
            elif user_input == "skip_assessment":
                session.stage = 'recommendations'
                session.assessed_level = session.data.get('level', 'intermediate')
                return self._create_recommendations_response(session)
        
        # Fallback for text input
        if any(word in user_input.lower() for word in ['start', 'begin', 'yes', 'ready']):
            session.stage = 'assessment_active'
            session.current_question = 0
            return self._get_assessment_question(session)
        elif any(word in user_input.lower() for word in ['skip', 'no', 'later']):
            session.stage = 'recommendations'
            session.assessed_level = session.data.get('level', 'intermediate')
            return self._create_recommendations_response(session)
        
        return self._create_assessment_intro_response(session)

    def _handle_assessment_question(self, user_input: str, session: 'ConsultationSession', action_type: str) -> dict:
        """Handle assessment question responses"""
        
        if action_type == "button_click":
            # Handle answer button click
            if user_input.startswith("answer_"):
                choice = int(user_input.replace("answer_", ""))
                return self._process_assessment_answer(choice, session)
        
        # Handle text input - try to extract choice
        choice = self._extract_choice_from_text(user_input)
        if choice:
            return self._process_assessment_answer(choice, session)
        
        # Invalid input - show current question again
        return self._get_assessment_question(session, "Please select one of the options above or type 1, 2, or 3.")

    def _get_assessment_question(self, session: 'ConsultationSession', error_message: str = None) -> dict:
        """Get current assessment question with interactive buttons"""
        
        if session.current_question >= len(ASSESSMENT_QUESTIONS):
            # Assessment complete
            return self._complete_assessment(session)
        
        question = ASSESSMENT_QUESTIONS[session.current_question]
        question_num = session.current_question + 1
        total_questions = len(ASSESSMENT_QUESTIONS)
        
        response = f"Question {question_num} of {total_questions}:\n\n{question['question']}"
        if error_message:
            response = f"{error_message}\n\n{response}"

        # Create answer buttons
        answer_buttons = []
        for i, option in enumerate(question['options'], 1):
            answer_buttons.append({
                'id': f'answer_{i}',
                'text': f"{i}. {option}",
                'action': 'button_click',
                'style': 'answer_option'
            })

        return {
            'response': response,
            'ui_elements': {
                'type': 'question_interface',
                'progress': {
                    'current': question_num,
                    'total': total_questions,
                    'percentage': int((question_num / total_questions) * 100)
                },
                'answers': answer_buttons
            },
            'stage': 'assessment_active',
            'allow_text_input': True,
            'text_fallback': "You can also type 1, 2, or 3 for your answer."
        }

    def _process_assessment_answer(self, choice: int, session: 'ConsultationSession') -> dict:
        """Process assessment answer and move to next question"""
        # Record the answer
        question = ASSESSMENT_QUESTIONS[session.current_question]
        is_correct = choice == question['correct_answer']
        
        session.assessment_answers.append({
            'question': session.current_question,
            'choice': choice,
            'correct': is_correct
        })
        
        session.current_question += 1
        
        # Move to next question or complete assessment
        return self._get_assessment_question(session)

    def _complete_assessment(self, session: 'ConsultationSession') -> dict:
        """Complete assessment and calculate results"""
        correct_count = sum(1 for answer in session.assessment_answers if answer['correct'])
        total_questions = len(session.assessment_answers)
        percentage = int((correct_count / total_questions) * 100) if total_questions > 0 else 0
        
        # Determine level
        if percentage >= 80:
            level = 'advanced'
        elif percentage >= 60:
            level = 'intermediate'
        else:
            level = 'beginner'
        
        session.assessed_level = level
        session.assessment_results = {
            'correct': correct_count,
            'total': total_questions,
            'percentage': percentage,
            'level': level
        }
        
        session.stage = 'recommendations'
        
        # Show results with transition to recommendations
        response = f"Assessment Complete! 🎉\n\nYou scored {correct_count}/{total_questions} ({percentage}%)\nRecommended level: {level.title()}"
        
        return {
            'response': response,
            'ui_elements': {
                'type': 'results_display',
                'score': {
                    'correct': correct_count,
                    'total': total_questions,
                    'percentage': percentage,
                    'level': level
                },
                'next_button': {
                    'id': 'see_recommendations',
                    'text': 'See My Recommendations',
                    'style': 'primary',
                    'action': 'button_click'
                }
            },
            'stage': 'assessment_complete',
            'allow_text_input': False
        }

    def _handle_recommendations(self, user_input: str, session: 'ConsultationSession', action_type: str) -> dict:
        """Handle recommendations display and actions"""
        return self._create_recommendations_response(session)

    def _create_recommendations_response(self, session: 'ConsultationSession') -> dict:
        """Create interactive recommendations interface"""
        name = session.data.get('name', 'there')
        level = session.assessed_level or session.data.get('level', 'intermediate')
        
        # Generate course recommendations
        recommendations = self._generate_course_recommendations(session)
        
        response = f"Based on your assessment, {name}, here are my personalized course recommendations for {level} level:"

        # Create interactive course cards
        course_buttons = []
        for course in recommendations:
            course_buttons.append({
                'id': f"course_{course['id']}",
                'text': course['name'],
                'subtitle': f"{course['duration']} • {course['schedule']}",
                'description': course['description'],
                'action': 'view_course_details',
                'style': 'course_card'
            })

        return {
            'response': response,
            'ui_elements': {
                'type': 'course_recommendations',
                'courses': course_buttons,
                'action_buttons': [
                    {
                        'id': 'contact_advisor',
                        'text': 'Speak with an Advisor',
                        'style': 'primary',
                        'action': 'button_click'
                    },
                    {
                        'id': 'start_new_consultation',
                        'text': 'Start New Consultation',
                        'style': 'secondary', 
                        'action': 'button_click'
                    }
                ]
            },
            'stage': 'recommendations',
            'allow_text_input': True
        }

    def _generate_course_recommendations(self, session: 'ConsultationSession') -> list:
        """Generate course recommendations based on session data"""
        level = session.assessed_level or session.data.get('level', 'intermediate')
        age_range = session.data.get('age_range', '7-10')
        
        # Mock course data - replace with real course catalog
        course_catalog = {
            'beginner': [
                {
                    'id': 'beg001',
                    'name': 'English Foundations',
                    'duration': '8 weeks',
                    'schedule': 'Tue/Thu 4-5pm',
                    'description': 'Perfect for building basic English skills with fun activities and games.'
                },
                {
                    'id': 'beg002', 
                    'name': 'Speaking & Listening Starter',
                    'duration': '6 weeks',
                    'schedule': 'Mon/Wed 4-5pm',
                    'description': 'Focus on conversation skills and pronunciation for beginners.'
                }
            ],
            'intermediate': [
                {
                    'id': 'int001',
                    'name': 'Grammar & Conversation',
                    'duration': '10 weeks', 
                    'schedule': 'Tue/Thu 5-6pm',
                    'description': 'Strengthen grammar while practicing real-world conversations.'
                },
                {
                    'id': 'int002',
                    'name': 'Reading & Writing Plus',
                    'duration': '8 weeks',
                    'schedule': 'Mon/Wed 5-6pm', 
                    'description': 'Improve reading comprehension and writing skills.'
                }
            ],
            'advanced': [
                {
                    'id': 'adv001',
                    'name': 'Advanced Communication',
                    'duration': '12 weeks',
                    'schedule': 'Tue/Thu 6-7pm',
                    'description': 'Master complex topics and advanced grammar structures.'
                }
            ]
        }
        
        return course_catalog.get(level, course_catalog['intermediate'])

    def _extract_name(self, text: str) -> str:
        """Extract name from natural language input"""
        import re
        patterns = [
            r"(?:my name is|i am|i'm|call me)\s+(\w+)",
            r"(?:name is|name:)\s*(\w+)",
            r"^(\w+)$"  # Single word responses
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).title()
        return None

    def _extract_choice_from_text(self, text: str) -> int:
        """Extract choice number from text"""
        import re
        match = re.search(r'[123]', text)
        return int(match.group()) if match else None

    def _create_error_response(self, message: str) -> dict:
        """Create error response"""
        return {
            'response': f"I'm sorry, {message}. Let's start over.",
            'ui_elements': {
                'type': 'action_buttons',
                'buttons': [
                    {
                        'id': 'restart_consultation',
                        'text': 'Start New Consultation',
                        'style': 'primary',
                        'action': 'button_click'
                    }
                ]
            },
            'stage': 'error',
            'allow_text_input': False
        }


class ConsultationSession:
    """Individual consultation session state"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.stage = 'welcome'
        self.data = {}
        self.current_question = 0
        self.assessment_answers = []
        self.assessment_results = {}
        self.assessed_level = None



# Assessment questions configuration
ASSESSMENT_QUESTIONS = [
    {
        'id': 'q1',
        'question': 'Choose the correct sentence:',
        'options': [
            'He go to school every day',
            'He goes to school every day', 
            'He going to school every day'
        ],
        'correct_answer': 2
    },
    {
        'id': 'q2',
        'question': 'Select the best response to "How are you?":',
        'options': [
            'I am fine, thank you',
            'Fine is me',
            'Me fine today'
        ],
        'correct_answer': 1
    },
    {
        'id': 'q3', 
        'question': 'Choose the correct past tense:',
        'options': [
            'I eat pizza yesterday',
            'I ate pizza yesterday',
            'I eated pizza yesterday'
        ],
        'correct_answer': 2
    },
    {
        'id': 'q4',
        'question': 'Which sentence uses "can" correctly?',
        'options': [
            'I can to swim',
            'I can swim', 
            'I can swimming'
        ],
        'correct_answer': 2
    },
    {
        'id': 'q5',
        'question': 'Complete: "She _____ her homework every night."',
        'options': [
            'do',
            'does',
            'doing'
        ],
        'correct_answer': 2
    }
]