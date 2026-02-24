# Project Specification: Vision-to-JSON Factory

This document outlines the technical specification for the "Vision-to-JSON" pipeline. The goal is to convert raw PDF pages (e.g., JEE exam papers) into structured "Intelligent Vision Data" without losing layout context, mathematical precision, or diagrammatic fidelity.

## Table of Contents
1. [Core Philosophy](#core-philosophy)
2. [Module 1: Ingestion & Vision Layer](#module-1-the-ingestion--vision-layer)
3. [Module 2: Smart Extraction Layer (Prompt Engineering)](#module-2-the-smart-extraction-layer-prompt-engineering)
4. [Module 3: Asset Processing (The "Cropper")](#module-3-asset-processing-the-cropper)
5. [Module 4: The Logger (The "Black Box")](#module-4-the-logger-the-black-box)
6. [Module 5: Master JSON Structure](#module-5-the-master-json-structure)

---

## Core Philosophy
This is a sophisticated engineering challenge designed as a manufacturing assembly line, not a simple script. The pipeline interprets complex layouts, handles multi-column text, and intelligently distinguishes between text, LaTeX equations, and visual diagrams.

---

## Module 1: The Ingestion & Vision Layer

**Goal:** Convert raw PDF pages into "Intelligent Vision Data" without losing layout context.

### Rules & Logic

1.  **High-Fidelity Rendering:**
    *   Every PDF page must be converted to an image at **300 DPI (minimum)**.
    *   *Why:* Lower DPI causes the AI to misread subscripts (e.g., $H_2O$ becomes $H2O$) or tiny bounding boxes.

2.  **Layout Handling (Multi-Column Support):**
    *   **Rule:** Do not crop the page manually before sending to AI. Send the *full page image*.
    *   **Prompt Instruction:** "Analyze this page reading naturally from top-left to bottom-right. If the page is two-column, finish the left column completely before moving to the right column."

3.  **Cross-Page Continuity (The "Partial Question" Problem):**
    *   **Rule:** The system must maintain a "buffer" of the last processed question.
    *   **Logic:** If a question ends without options or with an incomplete sentence (e.g., "Find the velocity of..."), flag it as `STATUS: INCOMPLETE`.
    *   **Next Page Action:** When processing Page $N$, check if `STATUS == INCOMPLETE`. If yes, prepend the new text to the previous question's ID before creating a new entry.

---

## Module 2: The "Smart Extraction" Layer (Prompt Engineering)

**Goal:** The AI must distinguish between text, math, and diagrams with strict rules.

### Rules for Diagram vs. Text

1.  **The "Chemical Reaction" Rule:**
    *   **If** a chemical reaction is simple text (e.g., $A + B \rightarrow C$), it **MUST** be converted to LaTeX.
    *   **If** it involves Benzene rings, complex organic structures, or mechanism arrows that standard LaTeX cannot render perfectly, it **MUST** be treated as a `<<DIAGRAM>>`.

2.  **Bounding Box Strategy:**
    *   **Margin Rule:** "When identifying a diagram, identify the tightest bounding box, then **expand by 20 pixels** on all sides to ensure axis labels and captions are not cut off."

3.  **Grouped Instructions (Comprehension/Linked Questions):**
    *   **Logic:** If the AI detects a header like "Passage for Q10-12", it must extract the passage *once* and link it to Q10, Q11, and Q12 in the JSON structure as a `parent_context` field.

---

## Module 3: Asset Processing (The "Cropper")

**Goal:** Physically generate the image files and host them.

### Process Flow

1.  **Receive Coordinates:** Get `[ymin, xmin, ymax, xmax]` from the AI response.
2.  **Crop & Optimize:**
    *   Crop the original 300 DPI image.
    *   *Optimization:* Convert the crop to **WebP format** (smaller size, high quality) before uploading.
3.  **S3 Folder Structure:**
    *   Bucket organization is critical for debugging.
    *   **Structure:**
        ```text
        s3://your-bucket/
        ├── raw_pdfs/                  # Original PDFs
        ├── processed_json/            # Final JSONs (one per PDF)
        └── assets/
            └── {pdf_id}/              # Folder for THIS specific PDF
                ├── q1_diagram.webp
                ├── q5_option_a.webp   # If option is an image
                └── q12_passage.webp
        ```
4.  **Injection:** The S3 URL (e.g., `https://s3.region.amazonaws.com/.../jee_p1/q1_diagram.webp`) is immediately injected into the JSON to replace the `<<DIAGRAM_REF>>` placeholder.

---

## Module 4: The Logger (The "Black Box")

**Goal:** You need to know exactly why a PDF failed without opening it.

**File:** `processing_log_{date}.jsonl` (JSON Lines format)

### Log Structure Rules

*   **Success:** "Page 5 processed. Extracted 4 questions."
*   **Warning (Omission):** "Skipped Q14. Reason: Question text was detected as 'blurry' or 'unreadable'."
*   **Critical Fail:** "PDF Corrupt" or "API Timeout."
*   **Token Usage:** Log the input/output tokens per page to track costs.

### Example Log Entry

```json
{
  "pdf_id": "JEE_Mains_2024_Phy",
  "page": 4,
  "status": "PARTIAL_SUCCESS",
  "questions_extracted": 3,
  "omitted": 1,
  "omission_reason": "Q15 marked as 'handwritten' text which violates quality rules.",
  "timestamp": "2026-02-18T10:00:00Z"
}
```

---

## Module 5: The Master JSON Structure

This is the final output schema for the database.

```json
{
  "meta": {
    "pdf_name": "JEE_Advanced_Paper_1.pdf",
    "processed_date": "2026-02-18",
    "total_questions": 18
  },
  "questions": [
    {
      "id": "q_001",
      "type": "MCQ",
      "instruction_text": null,  // For grouped questions
      "question_text": "A block of mass $M$ is attached to a spring...",
      "diagram_url": "https://s3.../assets/jee_p1/q1_fig.webp", 
      "options": [
        { "id": "A", "text": "$2mg$", "is_image": false },
        { "id": "B", "text": "$4mg$", "is_image": false },
        { "id": "C", "url": "https://s3.../assets/jee_p1/q1_opt_c.webp", "is_image": true },
        { "id": "D", "text": "$mg/2$", "is_image": false }
      ],
      "correct_option": "B",
      "topic_tags": ["Mechanics", "SHM"],
      "difficulty": "Medium"
    }
  ]
}
```
