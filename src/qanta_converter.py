import csv
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

"""
Main converter: Transform parsed questions into QANTA format
"""

class QantaConverter:
    """Convert parsed Quizbowl questions to QANTA format"""
    
    def __init__(self, answer_mapper, sentence_splitter):
        self.answer_mapper = answer_mapper
        self.sentence_splitter = sentence_splitter
    
    def convert_question(self, raw_question: Dict, packet_id: str, question_num: int) -> Dict:
        """
        Convert a raw question to QANTA format
        
        Args:
            raw_question: Parsed question dict from docx_parser
            packet_id: Identifier for the packet (e.g., "2025_PACE_NSC_R01")
            question_num: Question number within packet
            
        Returns:
            Question in QANTA format
        """
        text = raw_question.get('raw_text', '')
        
        # Extract answer and remove from text
        answer_section = self._extract_answer(text)
        clean_text = self._remove_answer_line(text)
        
        # Split into sentences
        sentences = self.sentence_splitter.split(clean_text)
        
        # Map answer to canonical form
        answer_mapping = self.answer_mapper.map_answer(answer_section)
        
        # Generate unique ID
        question_id = f"{packet_id}_Q{question_num:02d}"
        
        qanta_question = {
            'qid': question_id,
            'question_num': question_num,
            'packet': packet_id,
            'raw_text': text,
            'answer': answer_mapping['canonical_answer'],
            'answer_raw': answer_mapping['raw_answer'],
            'sentences': sentences,
            'category': answer_mapping['category'],
            'wikipedia_page': answer_mapping['wikipedia_page'],
            'tournament': self._extract_tournament(packet_id),
            'year': self._extract_year(packet_id),
            'fold': 'test',  # Default to test; user can reassign
            'date_added': datetime.now().isoformat(),
        }
        
        return qanta_question
    
    def convert_batch(self, questions: List[Dict], packet_id: str) -> List[Dict]:
        """Convert multiple questions from same packet"""
        converted = []
        for i, q in enumerate(questions, 1):
            converted.append(self.convert_question(q, packet_id, i))
        return converted
    
    def export_to_csv(self, questions: List[Dict], output_path: str):
        """
        Export questions to QANTA CSV format
        
        CSV format: Question ID, Fold, Answer, Category, Text
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['Question_ID', 'Fold', 'Answer', 'Category', 'Text']
            )
            writer.writeheader()
            
            for q in questions:
                # Join sentences with ||| as per QANTA format
                text_with_sentences = ' ||| '.join(q['sentences'])
                
                writer.writerow({
                    'Question_ID': q['qid'],
                    'Fold': q['fold'],
                    'Answer': q['answer'],
                    'Category': q['category'],
                    'Text': text_with_sentences
                })
    
    def export_to_json(self, questions: List[Dict], output_path: str):
        """
        Export questions to JSON format with full metadata
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
    
    def export_to_jsonl(self, questions: List[Dict], output_path: str):
        """
        Export questions to JSONL format (one JSON object per line)
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for q in questions:
                f.write(json.dumps(q, ensure_ascii=False) + '\n')
    
    @staticmethod
    def _extract_answer(text: str) -> str:
        """Extract answer from question text"""
        # Look for patterns like "name this ...", "answer: ...", "Who/What/etc is ..."
        # For now, return last line as a placeholder
        # This should be manually reviewed
        return "[ANSWER_NEEDS_MANUAL_REVIEW]"
    
    @staticmethod
    def _remove_answer_line(text: str) -> str:
        """Remove the FTP/answer prompt line"""
        import re
        # Remove "For X points, ..." or "FTP, ..." at end
        text = re.sub(r'\s*(?:For\s+\d+\s+points|FTP)[,.]?\s+(?:name\s+)?[^.!?]*[.!?]?\s*$', '', text)
        return text.strip()
    
    @staticmethod
    def _extract_tournament(packet_id: str) -> str:
        """Extract tournament name from packet ID"""
        if 'PACE' in packet_id:
            return 'PACE NSC'
        elif 'ACF' in packet_id:
            return 'ACF'
        elif 'NAQT' in packet_id:
            return 'NAQT'
        else:
            return 'Unknown'
    
    @staticmethod
    def _extract_year(packet_id: str) -> Optional[int]:
        """Extract year from packet ID"""
        import re
        match = re.search(r'20\d{2}', packet_id)
        if match:
            return int(match.group(0))
        return None
