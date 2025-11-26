from docx import Document
from typing import List, Dict, Tuple
import re

"""
Parse Quizbowl questions from Word documents (.docx)
"""

class QuizbowlDocxParser:
    """Parse Quizbowl tournament documents in DOCX format"""
    
    def __init__(self):
        self.questions = []
    
    def parse_document(self, docx_path: str) -> List[Dict]:
        """
        Parse a .docx file containing Quizbowl questions
        
        Args:
            docx_path: Path to the .docx file
            
        Returns:
            List of question dictionaries with raw text
        """
        doc = Document(docx_path)
        questions = []
        current_question = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            if not text:
                continue
            
            # Check if this is a question start (usually numbered or starts with question marker)
            if self._is_question_start(text):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    'raw_text': text,
                    'lines': [text]
                }
            elif current_question:
                current_question['lines'].append(text)
                current_question['raw_text'] += ' ' + text
       
        if current_question:
            questions.append(current_question)
        
        return questions
    
    @staticmethod
    def _is_question_start(text: str) -> bool:
        """Check if text appears to be the start of a new question"""
        # Looking for patterns like "1.", "1)", question numbers at start
        if re.match(r'^\d+[.)]\s', text):
            return True
        # Looking for bonus/tossup markers
        if text.lower().startswith(('bonus', 'tossup', 'tossups', 'bonuses')):
            return True
        return False
    
    @staticmethod
    def extract_question_type(text: str) -> str:
        """Extract question type (tossup, bonus, etc)"""
        text_lower = text.lower()
        if 'bonus' in text_lower:
            return 'bonus'
        elif 'tossup' in text_lower:
            return 'tossup'
        else:
            return 'unknown'
