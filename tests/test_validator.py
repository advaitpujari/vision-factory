
import unittest
from vision_factory.output.validator import JSONValidator

class TestJSONValidator(unittest.TestCase):
    def setUp(self):
        self.validator = JSONValidator()
        self.valid_data = {
            "test_metadata": {"title": "Test"},
            "questions": [
                {
                    "id": "1",
                    "text": "Valid question text with enough length.",
                    "type": "MCQ",
                    "options": {"A": {"text": "Opt A"}, "B": {"text": "Opt B"}},
                    "correct_option": "A",
                    "metadata": {"bbox": [10, 10, 100, 100]}
                }
            ]
        }

    def test_valid_structure(self):
        data, issues = self.validator.validate(self.valid_data)
        self.assertEqual(len(issues), 0)
        self.assertEqual(len(data["questions"]), 1)

    def test_missing_root_keys(self):
        data = {"questions": []}
        _, issues = self.validator.validate(data)
        self.assertTrue(any(i['message'].startswith("Missing root key") for i in issues))

    def test_short_text_removal(self):
        data = self.valid_data.copy()
        data["questions"] = [
            {"id": "2", "text": "Hi", "type": "MCQ", "options": {}}
        ]
        cleansed, issues = self.validator.validate(data)
        self.assertEqual(len(cleansed["questions"]), 0)
        self.assertTrue(any("too short" in i['message'] for i in issues))

    def test_trash_filtering(self):
        data = self.valid_data.copy()
        data["questions"] = [
            {"id": "3", "text": "- 12 -", "type": "MCQ", "options": {}}
        ]
        cleansed, issues = self.validator.validate(data)
        self.assertEqual(len(cleansed["questions"]), 0)
        self.assertTrue(any("trash content" in i['message'] for i in issues))

    def test_duplicate_ids(self):
        data = self.valid_data.copy()
        q1 = self.valid_data["questions"][0]
        data["questions"] = [q1, q1] # Duplicate
        cleansed, issues = self.validator.validate(data)
        self.assertEqual(len(cleansed["questions"]), 1)
        self.assertTrue(any("Duplicate Question ID" in i['message'] for i in issues))

    def test_invalid_logic_correct_option(self):
        data = self.valid_data.copy()
        data["questions"][0]["correct_option"] = "Z" # Invalid
        cleansed, issues = self.validator.validate(data)
        self.assertIsNone(cleansed["questions"][0]["correct_option"])
        self.assertTrue(any("not found in options" in i['message'] for i in issues))

if __name__ == '__main__':
    unittest.main()
