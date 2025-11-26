import re
from typing import Dict, Optional, Tuple
import urllib.parse
import urllib.request
import json

"""
Map Quizbowl answers to canonical forms (Wikipedia articles, etc.)
"""


class AnswerMapper:
    """Maps Quizbowl answers to canonical Wikipedia pages or other sources"""
    
    def __init__(self, cache_file: Optional[str] = None):
        self.cache = {}
        self.cache_file = cache_file
        if cache_file:
            self._load_cache()
    
    def map_answer(self, raw_answer: str) -> Dict[str, str]:
        """
        Map a raw Quizbowl answer to canonical form
        
        Args:
            raw_answer: Raw answer from question (may include parentheticals)
            
        Returns:
            Dict with 'canonical_answer', 'wikipedia_page', 'category', etc.
        """
        # Clean parenthetical info
        canonical_answer = self._clean_answer(raw_answer)
        
        if canonical_answer in self.cache:
            return self.cache[canonical_answer]
        
        # Try to find Wikipedia page
        wiki_page = self._find_wikipedia_page(canonical_answer)
        
        result = {
            'canonical_answer': canonical_answer,
            'raw_answer': raw_answer,
            'wikipedia_page': wiki_page,
            'source': 'wikipedia' if wiki_page else 'manual',
            'category': self._infer_category(canonical_answer, wiki_page)
        }
        
        self.cache[canonical_answer] = result
        return result
    
    @staticmethod
    def _clean_answer(answer: str) -> str:
        """
        Clean answer by removing parenthetical info
        """
        # Remove common parenthetical additions but keep significant ones
        # Remove things in parentheses that are just clarifications
        answer = re.sub(r'\s*\((?:also known as|AKA|a\.k\.a\.)[^)]*\)', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\s*\((?:spelled|or)[^)]*\)', '', answer, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        answer = ' '.join(answer.split())
        
        return answer.strip()
    
    @staticmethod
    def _find_wikipedia_page(answer: str) -> Optional[str]:
        """
        Attempt to find matching Wikipedia article
        
        Args:
            answer: The canonical answer
            
        Returns:
            Wikipedia page title if found, else None
        """
        try:
            # Use Wikipedia API to search
            search_query = urllib.parse.quote(answer)
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_query}&format=json"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            if data['query']['search']:
                # Return the title of the first result
                return data['query']['search'][0]['title']
            
        except Exception as e:
            print(f"Warning: Could not search Wikipedia for '{answer}': {e}")
        
        return None
    
    @staticmethod
    def _infer_category(answer: str, wiki_page: Optional[str]) -> str:
        """
        Infer category based on answer text or Wikipedia page
        
        Args:
            answer: The canonical answer
            wiki_page: The Wikipedia page (if found)
            
        Returns:
            Inferred category
        """
        answer_lower = answer.lower()
        
        # Try to infer from keywords in answer
        if any(word in answer_lower for word in ['war', 'battle', 'treaty', 'king', 'emperor', 'general']):
            return 'History'
        elif any(word in answer_lower for word in ['element', 'compound', 'reaction', 'molecule', 'acid']):
            return 'Science:Chemistry'
        elif any(word in answer_lower for word in ['physics', 'quantum', 'relativity', 'force', 'energy']):
            return 'Science:Physics'
        elif any(word in answer_lower for word in ['planet', 'star', 'galaxy', 'cosmos', 'space']):
            return 'Science:Astronomy'
        elif any(word in answer_lower for word in ['novel', 'poem', 'author', 'playwright', 'literature']):
            return 'Fine_Arts:Literature'
        elif any(word in answer_lower for word in ['composer', 'symphony', 'concerto', 'opera', 'musician']):
            return 'Fine_Arts:Music'
        elif any(word in answer_lower for word in ['painting', 'sculpture', 'artist', 'gallery']):
            return 'Fine_Arts:Art'
        elif any(word in answer_lower for word in ['country', 'city', 'mountain', 'river', 'geography']):
            return 'Geography'
        else:
            return 'Misc'
    
    def _load_cache(self):
        """Load cache from file"""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            self.cache = {}
    
    def save_cache(self):
        """Save cache to file"""
        if self.cache_file:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
