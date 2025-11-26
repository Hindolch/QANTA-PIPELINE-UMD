import re
from typing import List, Tuple

"""
Split Quizbowl question text into sentences
"""

class SentenceSplitter:
    """Split Quizbowl questions into sentences"""
    
    # Common abbreviations that shouldn't trigger sentence splits
    ABBREVIATIONS = {
        'mr', 'mrs', 'ms', 'dr', 'prof', 'st', 'jr', 'sr',
        'ph.d', 'b.a', 'm.a', 'b.s', 'm.s',
        'inc', 'ltd', 'co', 'corp', 'assoc',
        'et al', 'etc', 'e.g', 'i.e', 'vs', 'v.s',
        'no', 'vol', 'ed', 'eds',
        'a.m', 'p.m', 'a.d', 'b.c',
    }
    
    @classmethod
    def split(cls, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: The text to split
            
        Returns:
            List of sentences
        """
        # Handle Quizbowl-specific separators first
        # Replace "|||" with period for splitting
        text = text.replace(' ||| ', '. ')
        
        # Standard sentence splitting
        sentences = cls._split_on_punctuation(text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    @classmethod
    def _split_on_punctuation(cls, text: str) -> List[str]:
        """Split text on sentence-ending punctuation"""
        # Replace common line breaks with spaces
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        
        # Split on periods, question marks, exclamation marks
        
        protected_text = text
        for abbr in cls.ABBREVIATIONS:
            protected_text = protected_text.replace(
                f' {abbr}.',
                f' {abbr}__ABBR_DOT__'
            )
        
        pattern = r'(?<=[.!?])\s+(?=[A-Z"])|(?<=[.!?])$'
        sentences = re.split(pattern, protected_text)
        
        # Restore abbreviations
        sentences = [s.replace('__ABBR_DOT__', '.') for s in sentences]
        
        # Handle ellipses - don't split on them
        sentences = [s.replace('...', '__ELLIPSIS__') for s in sentences]
        sentences = [s.replace('__ELLIPSIS__', '...') for s in sentences]
        
        return sentences
    
    @staticmethod
    def remove_answer_line(text: str) -> Tuple[str, str]:
        """
        Remove the "FTP/FTP name this" line from text
        
        Returns:
            (text_without_answer_line, answer_line)
        """
        # Match patterns like "For 10 points, name this..." or "FTP, name this.."
        answer_pattern = r'(?:For\s+\d+\s+points|FTP)[,.]?\s+(?:name\s+)?[^.!?]*[.!?]'
        
        match = re.search(answer_pattern, text, re.IGNORECASE)
        if match:
            answer_line = match.group(0)
            remaining = text[:match.start()] + text[match.end():]
            return remaining.strip(), answer_line
        
        return text, ""
