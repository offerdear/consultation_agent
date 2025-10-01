import os
import uuid
from rag_inmemory import InMemoryRAG


def test_consultation_happy_path():
    # Create a RAG instance but avoid requiring OpenAI key during tests by
    # setting an env var and monkeypatching the embeddings/chat methods if needed.
    os.environ.setdefault('OPENAI_API_KEY', 'test_key')
    rag = InMemoryRAG(persist_directory='./vector_cache_test')

    session_id = str(uuid.uuid4())

    # Start consultation
    consultation = rag.consultation_manager.start_consultation(session_id)
    assert consultation['stage'] == 'basic_info'

    # Provide basic info and request assessment
    response, _ = rag.consultation_manager.process_basic_info(session_id, 'My name is Alex. I am 10 years old and I am a beginner. Start assessment please')
    assert 'assessment' in response.lower() or 'begin' in response.lower()

    # Simulate answering assessment questions (always pick choice 2 which our simple engine treats as correct)
    for i in range(len(rag.assessment_engine.questions)):
        next_q = rag.assessment_engine.get_next_question(session_id, consultation)
        assert next_q is not None
        res = rag.assessment_engine.process_answer(session_id, consultation, 2)

    # After finishing, we should have an assessment_result and recommendation
    assert 'assessment_result' in consultation

    rec = rag.recommendation_engine.recommend(consultation)
    assert 'recommended_courses' in rec


if __name__ == '__main__':
    test_consultation_happy_path()
    print('Test passed')
