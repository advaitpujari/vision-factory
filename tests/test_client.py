import pytest
from unittest.mock import patch, MagicMock
from vision_factory.extraction.client import DeepInfraClient

@pytest.fixture
def mock_image():
    image = MagicMock()
    # Mock save to bytes
    return image

def test_extract_page_success(mock_image):
    client = DeepInfraClient()
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": '{"meta": {"page_number": 1}}'}}
        ]
    }
    
    with patch('src.extraction.client.requests.post', return_value=mock_response) as mock_post:
        result = client.extract_page(mock_image, page_num=1)
        
        assert result == '{"meta": {"page_number": 1}}'
        
        # Verify call arguments structure (System prompt + User prompt)
        args, kwargs = mock_post.call_args
        json_body = kwargs['json']
        messages = json_body['messages']
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert "Analyze Page 1" in messages[1]['content'][1]['text']

def test_extract_page_failure(mock_image):
    client = DeepInfraClient()
    
    with patch('src.extraction.client.requests.post', side_effect=Exception("API Error")):
        with pytest.raises(Exception):
            client.extract_page(mock_image, page_num=1)
