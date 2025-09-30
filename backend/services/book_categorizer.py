#!/usr/bin/env python3
"""
Book Categorization Service using OpenAI API
This service categorizes books into genres using OpenAI's text analysis capabilities.
"""

import openai
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
current_dir = Path(__file__).parent.parent.parent
env_path = current_dir / ".env"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BookCategorizer:
    def __init__(self, openai_api_key: str):
        """
        Initialize the BookCategorizer with OpenAI API key.
        
        Args:
            openai_api_key (str): OpenAI API key
        """
        try:
            # Check for proxy environment
            http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
            https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
            
            # Create httpx client with minimal configuration to avoid proxy issues
            import httpx
            http_client = httpx.Client(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            # Create OpenAI client with the custom httpx client
            self.openai_client = openai.OpenAI(api_key=openai_api_key, http_client=http_client)
            logger.info("✅ BookCategorizer initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize BookCategorizer: {e}")
            self.openai_client = None
        
        # Predefined genre list that matches the frontend
        self.predefined_genres = [
            "Fiction", "Non-Fiction", "Mystery", "Science Fiction", 
            "Fantasy", "Romance", "Thriller", "Biography", "History", 
            "Self-Help", "Business", "Technology", "Art", "Poetry", "Drama"
        ]
        
        # Genre mapping from OpenAI categories to predefined genres
        self.genre_mapping = {
            # Fiction subcategories
            "literary fiction": "Fiction",
            "contemporary fiction": "Fiction",
            "classic fiction": "Fiction",
            "general fiction": "Fiction",
            "fiction": "Fiction",
            
            # Mystery/Thriller
            "mystery": "Mystery",
            "detective": "Mystery",
            "crime": "Mystery",
            "thriller": "Thriller",
            "suspense": "Thriller",
            "psychological thriller": "Thriller",
            
            # Science Fiction/Fantasy
            "science fiction": "Science Fiction",
            "sci-fi": "Science Fiction",
            "speculative fiction": "Science Fiction",
            "fantasy": "Fantasy",
            "urban fantasy": "Fantasy",
            "epic fantasy": "Fantasy",
            "high fantasy": "Fantasy",
            
            # Romance
            "romance": "Romance",
            "romantic fiction": "Romance",
            "contemporary romance": "Romance",
            "historical romance": "Romance",
            
            # Non-Fiction
            "non-fiction": "Non-Fiction",
            "nonfiction": "Non-Fiction",
            "biography": "Biography",
            "autobiography": "Biography",
            "memoir": "Biography",
            "history": "History",
            "historical": "History",
            "self-help": "Self-Help",
            "self help": "Self-Help",
            "personal development": "Self-Help",
            "business": "Business",
            "entrepreneurship": "Business",
            "management": "Business",
            "technology": "Technology",
            "programming": "Technology",
            "computer science": "Technology",
            "art": "Art",
            "art history": "Art",
            "design": "Art",
            "poetry": "Poetry",
            "poems": "Poetry",
            "verse": "Poetry",
            "drama": "Drama",
            "plays": "Drama",
            "theater": "Drama",
            "theatre": "Drama"
        }

    def categorize_books(self, books: List[Dict]) -> List[Dict]:
        """
        Categorize a list of books using OpenAI API.
        
        Args:
            books (List[Dict]): List of book dictionaries with title and author
            
        Returns:
            List[Dict]: List of books with added genre information
        """
        if not self.openai_client:
            logger.error("OpenAI client not initialized")
            return self._add_default_genres(books)
        
        categorized_books = []
        
        for book in books:
            try:
                genre = self._categorize_single_book(book)
                book_with_genre = book.copy()
                book_with_genre['genre'] = genre
                book_with_genre['genre_confidence'] = 'high'  # Could be enhanced with confidence scoring
                categorized_books.append(book_with_genre)
            except Exception as e:
                logger.error(f"Error categorizing book {book.get('title', 'Unknown')}: {e}")
                # Add default genre on error
                book_with_genre = book.copy()
                book_with_genre['genre'] = 'Fiction'  # Default fallback
                book_with_genre['genre_confidence'] = 'low'
                book_with_genre['genre_error'] = str(e)
                categorized_books.append(book_with_genre)
        
        return categorized_books

    def _categorize_single_book(self, book: Dict) -> str:
        """
        Categorize a single book using OpenAI API.
        
        Args:
            book (Dict): Book dictionary with title and author
            
        Returns:
            str: Categorized genre
        """
        title = book.get('title', '')
        author = book.get('author', '')
        
        if not title:
            return 'Fiction'  # Default fallback
        
        # Create prompt for genre categorization
        prompt = f"""Analyze the following book and determine its most appropriate genre from the predefined list.

Book Title: "{title}"
Author: "{author}"

Please categorize this book into ONE of the following genres:
{', '.join(self.predefined_genres)}

Consider the following factors:
1. The book's title and any genre indicators
2. The author's known works and typical genres
3. Common genre patterns in book titles
4. The most likely primary genre for this book

Respond with ONLY the genre name from the list above, nothing else."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a book categorization expert. Analyze books and assign them to the most appropriate genre from a predefined list. Always respond with only the genre name."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.1,
                timeout=30  # 30 second timeout
            )
            
            # Extract genre from response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message'):
                    genre_response = response.choices[0].message.content.strip()
                else:
                    genre_response = response.choices[0].text.strip()
            else:
                logger.error("Unexpected response format from OpenAI")
                return 'Fiction'
            
            # Validate and map the response
            genre = self._validate_and_map_genre(genre_response)
            logger.info(f"Categorized '{title}' as '{genre}'")
            return genre
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"OpenAI API error for book '{title}': {error_type} - {e}")
            
            # Handle specific error types
            if "timeout" in str(e).lower():
                logger.warning(f"OpenAI API timeout for book '{title}', using fallback categorization")
            elif "rate_limit" in str(e).lower():
                logger.warning(f"OpenAI API rate limit for book '{title}', using fallback categorization")
            elif "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.error(f"OpenAI API authentication error for book '{title}', using fallback categorization")
            elif "quota" in str(e).lower():
                logger.error(f"OpenAI API quota exceeded for book '{title}', using fallback categorization")
            else:
                logger.error(f"Unknown OpenAI API error for book '{title}': {e}")
            
            # Fallback to title-based categorization
            return self._fallback_categorization(title, author)

    def _validate_and_map_genre(self, genre_response: str) -> str:
        """
        Validate and map the OpenAI response to a predefined genre.
        
        Args:
            genre_response (str): Raw response from OpenAI
            
        Returns:
            str: Validated and mapped genre
        """
        # Clean the response
        genre_clean = genre_response.lower().strip()
        
        # Check if it's already in our predefined list
        for predefined_genre in self.predefined_genres:
            if predefined_genre.lower() == genre_clean:
                return predefined_genre
        
        # Check if it matches any of our mapping keys
        for openai_genre, mapped_genre in self.genre_mapping.items():
            if openai_genre in genre_clean:
                return mapped_genre
        
        # If no match found, return default
        logger.warning(f"Could not map genre response '{genre_response}' to predefined genres")
        return 'Fiction'

    def _fallback_categorization(self, title: str, author: str) -> str:
        """
        Fallback categorization based on title keywords when OpenAI API fails.
        
        Args:
            title (str): Book title
            author (str): Book author
            
        Returns:
            str: Fallback genre
        """
        title_lower = title.lower()
        
        # Keyword-based categorization
        if any(word in title_lower for word in ['mystery', 'murder', 'detective', 'crime']):
            return 'Mystery'
        elif any(word in title_lower for word in ['love', 'romance', 'heart']):
            return 'Romance'
        elif any(word in title_lower for word in ['space', 'future', 'robot', 'alien', 'sci-fi']):
            return 'Science Fiction'
        elif any(word in title_lower for word in ['magic', 'dragon', 'fantasy', 'wizard']):
            return 'Fantasy'
        elif any(word in title_lower for word in ['history', 'historical', 'war', 'battle']):
            return 'History'
        elif any(word in title_lower for word in ['business', 'management', 'entrepreneur']):
            return 'Business'
        elif any(word in title_lower for word in ['programming', 'code', 'software', 'tech']):
            return 'Technology'
        elif any(word in title_lower for word in ['self-help', 'success', 'motivation', 'habits']):
            return 'Self-Help'
        elif any(word in title_lower for word in ['biography', 'life of', 'memoir']):
            return 'Biography'
        elif any(word in title_lower for word in ['poetry', 'poems', 'verse']):
            return 'Poetry'
        elif any(word in title_lower for word in ['art', 'painting', 'design']):
            return 'Art'
        elif any(word in title_lower for word in ['drama', 'play', 'theater']):
            return 'Drama'
        else:
            return 'Fiction'  # Default fallback

    def _add_default_genres(self, books: List[Dict]) -> List[Dict]:
        """
        Add default genres when OpenAI API is not available.
        
        Args:
            books (List[Dict]): List of books
            
        Returns:
            List[Dict]: Books with default genres
        """
        for book in books:
            book['genre'] = 'Fiction'
            book['genre_confidence'] = 'low'
            book['genre_error'] = 'OpenAI API not available'
        
        return books

    def get_genre_statistics(self, books: List[Dict]) -> Dict[str, int]:
        """
        Get statistics about genre distribution in the book list.
        
        Args:
            books (List[Dict]): List of categorized books
            
        Returns:
            Dict[str, int]: Genre statistics
        """
        stats = {}
        
        for book in books:
            genre = book.get('genre', 'Unknown')
            stats[genre] = stats.get(genre, 0) + 1
        
        return stats

    def get_available_genres(self) -> List[str]:
        """
        Get the list of available predefined genres.
        
        Returns:
            List[str]: List of available genres
        """
        return self.predefined_genres.copy()
