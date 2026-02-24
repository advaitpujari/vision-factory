import pytest
import os
import sys

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def sample_json_response():
    return {
        "meta": {"page_number": 1, "total_questions": 2},
        "questions": [
            {
                "id": "Q1",
                "type": "MCQ",
                "question_text": "What is 2+2?",
                "options": [
                    {"id": "A", "text": "3", "is_image": false},
                    {"id": "B", "text": "4", "is_image": false}
                ],
                "correct_option": "B"
            }
        ]
    }
