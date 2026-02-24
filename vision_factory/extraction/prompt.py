
# 1. Vision Prompt (Image -> Markdown)
VISION_MARKDOWN_PROMPT = """
You are an expert Educational Content Digitizer. 
Your goal is to extract ALL content from this exam page into structured Markdown.

### INSTRUCTIONS:
1.  **Text Extraction**: Extract all text exactly as it appears. Use LaTeX for math (e.g., $x^2$).
2.  **Structure**: Preserve the logical structure (Questions, Options).
3.  **Diagram Detection**: 
    - If a question or option has a diagram/figure, you MUST detect its bounding box.
    - Output the bounding box EXPLICITLY using this format: `[[DIAGRAM_BBOX: ymin, xmin, ymax, xmax]]` (0-1000 scale).
    - Place this tag exactly where the diagram appears in the flow (e.g., before the question text if it's a main diagram, or inside the option).

### OUTPUT FORMAT (Markdown):
**Question 1**
[Determine the value of...]
[[DIAGRAM_BBOX: 150, 200, 350, 600]]

(A) Option A text
(B) Option B text
[[DIAGRAM_BBOX: 400, 100, 500, 200]]
...
"""

# 2. Text Prompt (Markdown -> JSON)
MARKDOWN_TO_JSON_PROMPT = """
You are a Data Structuring Expert.
Convert the following Markdown exam content into a strict JSON object following the specific schema below.

### SCHEMA:
{
  "test_metadata": {
    "title": "string or null (Extract if visible on page)",
    "subject": "string or null (Extract if visible)",
    "chapter": "string or null (Extract if visible)",
    "estimated_duration_mins": null,
    "total_marks": null
  },
  "questions": [
    {
      "id": "string",
      "type": "MCQ",
      "text": "string (LaTeX supported, include full question text)",
      "options": {
        "A": {
          "text": "string or null",
          "is_image": boolean,
          "image_path": null,
          "bbox": [ymin, xmin, ymax, xmax] or null
        },
        "B": { "text": "...", "is_image": false, "image_path": null, "bbox": null }
      },
      "correct_option": "string (A/B/C/D) or null",
      "explanation": "string or null",
      "metadata": {
        "source": "string or null (Extract if visible like 'JEE 2019')",
        "bbox": [ymin, xmin, ymax, xmax] or null
      },
      "has_latex": null,
      "is_trap": null,
      "difficulty": null,
      "ideal_time_seconds": null,
      "subject_tag": null,
      "topic_tags": []
    }
  ]
}

### INSTRUCTIONS:
1.  **Extraction Only**: Do NOT estimate or compute fields like `correct_option`, `explanation`, `metadata`, `has_latex`, `difficulty`, `ideal_time`, `is_trap`, `subject_tag`, etc. Set them to `null` or empty list.
2.  **Metadata**: Extract `bbox` for the question diagram from `[[DIAGRAM_BBOX: ...]]` tags in the markdown.
3.  **Options**: 
    - Convert option list to a Dictionary `{"A": {...}, "B": {...}}`.
    - If an option has a `[[DIAGRAM_BBOX]]` tag, extract it into the `bbox` field and set `is_image` to true.
4.  **Output VALID JSON only**. No markdown formatting.
"""
