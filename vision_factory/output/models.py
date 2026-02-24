from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal, Union, Dict, Any
from datetime import datetime

class Option(BaseModel):
    model_config = {"extra": "allow"}
    text: Optional[str] = Field(None, description="Text content of the option, including LaTeX")
    image_path: Optional[str] = Field(None, description="S3 URL if option is an image")
    is_image: bool = Field(False, description="True if option is purely visual")
    bbox: Optional[List[int]] = Field(None, description="Bounding box [ymin, xmin, ymax, xmax]")
    # validation to ensure at least one of text or image_path is present could be added, but optional for now

class QuestionMetadata(BaseModel):
    source: Optional[str] = Field(None, description="Source of the question (e.g. JEE Main 2019)")
    bbox: Optional[List[int]] = Field(None, description="Bounding box [ymin, xmin, ymax, xmax]")

class Question(BaseModel):
    model_config = {"extra": "allow"}
    id: str = Field(..., description="Unique question ID")
    type: Literal["MCQ", "Numerical", "Subjective"] = Field("MCQ", description="Type of question")
    text: str = Field(..., description="Main question text with LaTeX")
    has_latex: Optional[bool] = Field(None, description="True if text contains LaTeX")
    is_trap: Optional[bool] = Field(None, description="True if question is designed to be a trap")
    difficulty: Optional[str] = Field(None, description="Estimated difficulty level")
    ideal_time_seconds: Optional[int] = Field(None, description="Ideal time to solve in seconds")
    subject_tag: Optional[str] = Field(None, description="Broad subject tag")
    topic_tags: List[str] = Field(default_factory=list, description="Specific topic tags")
    image_path: Optional[str] = Field(None, description="S3 URL for associated diagram")
    options: Dict[str, Option] = Field(default_factory=dict, description="Dictionary of options (A, B, C, D) mapping to Option objects")
    correct_option: Optional[str] = Field(None, description="Correct option ID if available")
    explanation: Optional[str] = Field(None, description="Explanation for the answer")
    metadata: QuestionMetadata = Field(default_factory=QuestionMetadata, description="Additional metadata")

    # Legacy fields support or alias if needed, but we are rewriting.
    # We might need a validator to populate 'has_latex' automatically if not provided provided by LLM?
    # The plan said "Programmatically derived", so we can use a validator here.

    def model_post_init(self, __context: Any) -> None:
        if "$" in self.text or "\\[" in self.text:
            self.has_latex = True

class TestMetadata(BaseModel):
    title: Optional[str] = Field(None, description="Title of the test/paper")
    subject: Optional[str] = Field(None, description="Subject (Physics, Chemistry, Maths)")
    chapter: Optional[str] = Field(None, description="Chapter name if applicable")
    estimated_duration_mins: Optional[int] = Field(None, description="Total duration")
    total_marks: Optional[int] = Field(None, description="Total marks")
    processed_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_questions: int = Field(0, description="Count of questions extracted")

class PageOutput(BaseModel):
    test_metadata: TestMetadata = Field(default_factory=TestMetadata)
    questions: List[Question]
