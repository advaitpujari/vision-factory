
from typing import Optional, List
from vision_factory.output.models import Question, PageOutput

class StateManager:
    def __init__(self):
        self.pending_question: Optional[Question] = None
        self.pending_text_fragment: str = ""

    def process_page_output(self, page_output: PageOutput) -> List[Question]:
        """
        Processes a page's output, handling continuation from previous pages.
        Returns the list of COMPLETE questions from this page (and potentially the finished previous one).
        """
        final_questions = []
        
        raw_questions = page_output.questions
        
        if not raw_questions:
            return []

        # 1. Handle Continuation
        first_q = raw_questions[0]
        
        # Heuristic: If we have a pending question and the first question of this page 
        # looks like a continuation (e.g. starts with options, or small text), merge them.
        # This logic can be complex. For now, rely on strict "INCOMPLETE" flag from LLM 
        # or if the first question has no ID or seems to be just options.
        
        if self.pending_question:
            # Check if first item is a continuation
            # Logic: If ID matches previous partial ID, or if it's explicitly marked as continuation
            # For this MVP, we assume the LLM might output a question with the SAME ID if instructed,
            # or we validly merge if the first question text starts with lowercase or looks like options.
            
            # Simple Merge Logic:
            self.pending_question.question_text += " " + first_q.question_text
            self.pending_question.options.extend(first_q.options)
            
            # If the merged question now looks complete, add it
            # How to know if complete? We assume it is unless flagged again.
            final_questions.append(self.pending_question)
            self.pending_question = None
            
            # Skip the first raw question as it was merged
            raw_questions = raw_questions[1:]

        # 2. Process Remaining Questions
        for q in raw_questions:
            # specific logic to detect if q is incomplete
            # For now, we pass them through. 
            # Ideally, the prompt should flag "status": "INCOMPLETE"
            
            # If valid/complete:
            final_questions.append(q)

        # 3. Update State for LAST question if needed
        # (This would require the LLM to explicitly flag "incomplete" which we added to prompt instructions)
        
        return final_questions
