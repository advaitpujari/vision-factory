import pytest
import json
from vision_factory.extraction.parser import JSONParser
from vision_factory.output.models import PageOutput

def test_clean_markdown():
    parser = JSONParser()
    raw = "```json\n{\"id\": \"1\"}\n```"
    cleaned = parser._clean_markdown(raw)
    assert cleaned == "{\"id\": \"1\"}"

def test_parse_valid_json():
    parser = JSONParser()
    raw = '{"meta": {"page_number": 1, "total_questions": 1}, "questions": []}'
    result = parser.parse(raw)
    assert isinstance(result, PageOutput)
    assert result.meta.page_number == 1

def test_parse_invalid_json():
    parser = JSONParser()
    raw = "Not JSON"
    with pytest.raises(ValueError):
        parser.parse(raw)
