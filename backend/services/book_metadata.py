#!/usr/bin/env python3
"""
Book Metadata Service
Fetches book covers, ratings, and additional metadata from various APIs
"""

import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from urllib.parse import quote
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BookMetadataService:
    def __init__(self):
        """Initialize the Book Metadata Service"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # API endpoints
        self.google_books_api = "https://www.googleapis.com/books/v1/volumes"
        self.open_library_api = "https://openlibrary.org/search.json"
        self.open_library_covers = "https://covers.openlibrary.org/b"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _rate_limit(self):
        """Implement rate limiting to be respectful to APIs"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def search_google_books(self, title: str, author: str = None) -> Optional[Dict]:
        """Search Google Books API for book metadata"""
        try:
            self._rate_limit()
            
            # Construct search query
            query_parts = [title]
            if author:
                query_parts.append(f"inauthor:{author}")
            
            query = "+".join(query_parts)
            params = {
                'q': query,
                'maxResults': 5,
                'printType': 'books'
            }
            
            response = self.session.get(self.google_books_api, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('totalItems', 0) > 0:
                # Return the first (most relevant) result
                book = data['items'][0]['volumeInfo']
                
                # Extract relevant information
                result = {
                    'title': book.get('title', title),
                    'authors': book.get('authors', [author] if author else []),
                    'published_date': book.get('publishedDate', ''),
                    'description': book.get('description', ''),
                    'page_count': book.get('pageCount', 0),
                    'categories': book.get('categories', []),
                    'language': book.get('language', 'en'),
                    'isbn_10': None,
                    'isbn_13': None,
                    'google_books_id': data['items'][0]['id']
                }
                
                # Extract ISBNs
                for identifier in book.get('industryIdentifiers', []):
                    if identifier['type'] == 'ISBN_10':
                        result['isbn_10'] = identifier['identifier']
                    elif identifier['type'] == 'ISBN_13':
                        result['isbn_13'] = identifier['identifier']
                
                # Get cover image
                image_links = book.get('imageLinks', {})
                if image_links:
                    # Try to get the largest available cover
                    cover_url = (image_links.get('large') or 
                               image_links.get('medium') or 
                               image_links.get('small') or 
                               image_links.get('thumbnail'))
                    if cover_url:
                        result['cover_url'] = cover_url
                
                # Get average rating
                if 'averageRating' in book:
                    result['average_rating'] = book['averageRating']
                    result['ratings_count'] = book.get('ratingsCount', 0)
                
                logger.info(f"✅ Found Google Books data for: {title}")
                return result
                
        except Exception as e:
            logger.warning(f"⚠️ Google Books API error for '{title}': {e}")
        
        return None
    
    def search_open_library(self, title: str, author: str = None) -> Optional[Dict]:
        """Search Open Library API for book metadata"""
        try:
            self._rate_limit()
            
            # Construct search query
            query_parts = [title]
            if author:
                query_parts.append(author)
            
            query = " ".join(query_parts)
            params = {
                'title': title,
                'author': author or '',
                'limit': 5,
                'fields': 'title,author_name,first_publish_year,isbn,cover_i,ratings_average,ratings_count,subject'
            }
            
            response = self.session.get(self.open_library_api, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('numFound', 0) > 0:
                # Return the first result
                book = data['docs'][0]
                
                result = {
                    'title': book.get('title', title),
                    'authors': book.get('author_name', [author] if author else []),
                    'published_date': str(book.get('first_publish_year', '')),
                    'isbn_10': None,
                    'isbn_13': None,
                    'open_library_id': book.get('cover_i'),
                    'subjects': book.get('subject', [])[:5]  # Limit to 5 subjects
                }
                
                # Extract ISBNs
                isbns = book.get('isbn', [])
                for isbn in isbns:
                    if len(isbn) == 10:
                        result['isbn_10'] = isbn
                    elif len(isbn) == 13:
                        result['isbn_13'] = isbn
                
                # Get cover image
                cover_id = book.get('cover_i')
                if cover_id:
                    result['cover_url'] = f"{self.open_library_covers}/id/{cover_id}-L.jpg"
                
                # Get ratings
                if 'ratings_average' in book:
                    result['average_rating'] = book['ratings_average']
                    result['ratings_count'] = book.get('ratings_count', 0)
                
                logger.info(f"✅ Found Open Library data for: {title}")
                return result
                
        except Exception as e:
            logger.warning(f"⚠️ Open Library API error for '{title}': {e}")
        
        return None
    
    def get_book_metadata(self, title: str, author: str = None) -> Dict:
        """
        Get comprehensive book metadata from multiple sources
        
        Args:
            title (str): Book title
            author (str, optional): Book author
            
        Returns:
            Dict: Combined metadata from all sources
        """
        logger.info(f"🔍 Fetching metadata for: {title} by {author or 'Unknown'}")
        
        # Start with basic info
        metadata = {
            'title': title,
            'author': author or 'Unknown',
            'cover_url': None,
            'average_rating': None,
            'ratings_count': 0,
            'description': '',
            'published_date': '',
            'page_count': 0,
            'isbn_10': None,
            'isbn_13': None,
            'categories': [],
            'subjects': [],
            'language': 'en',
            'source': 'unknown'
        }
        
        # Try Google Books first (usually better quality)
        google_data = self.search_google_books(title, author)
        if google_data:
            metadata.update(google_data)
            metadata['source'] = 'google_books'
        
        # Try Open Library as backup/supplement
        openlib_data = self.search_open_library(title, author)
        if openlib_data:
            # Merge data, preferring Google Books for conflicts
            for key, value in openlib_data.items():
                if key not in metadata or not metadata[key]:
                    metadata[key] = value
            
            # Always try to get cover from Open Library if Google Books doesn't have one
            if not metadata.get('cover_url') and openlib_data.get('cover_url'):
                metadata['cover_url'] = openlib_data['cover_url']
                metadata['source'] = 'open_library'
        
        # Clean up and format the data
        if isinstance(metadata.get('authors'), list):
            metadata['author'] = ', '.join(metadata['authors'][:3])  # Max 3 authors
        
        if isinstance(metadata.get('categories'), list):
            metadata['categories'] = metadata['categories'][:5]  # Max 5 categories
        
        if isinstance(metadata.get('subjects'), list):
            metadata['subjects'] = metadata['subjects'][:5]  # Max 5 subjects
        
        # Format rating
        if metadata.get('average_rating'):
            metadata['average_rating'] = round(float(metadata['average_rating']), 1)
        
        logger.info(f"✅ Metadata fetched for: {title} (Source: {metadata['source']})")
        return metadata
    
    def get_multiple_books_metadata(self, books: List[Dict]) -> List[Dict]:
        """
        Get metadata for multiple books
        
        Args:
            books: List of book dictionaries with 'title' and 'author' keys
            
        Returns:
            List of enhanced book dictionaries with metadata
        """
        logger.info(f"🔍 Fetching metadata for {len(books)} books...")
        
        enhanced_books = []
        for i, book in enumerate(books, 1):
            logger.info(f"📚 Processing book {i}/{len(books)}: {book.get('title', 'Unknown')}")
            
            # Get metadata
            metadata = self.get_book_metadata(
                title=book.get('title', ''),
                author=book.get('author', '')
            )
            
            # Merge with original book data
            enhanced_book = {**book, **metadata}
            enhanced_books.append(enhanced_book)
            
            # Small delay to be respectful to APIs
            time.sleep(0.2)
        
        logger.info(f"✅ Enhanced metadata for {len(enhanced_books)} books")
        return enhanced_books

# Global instance
metadata_service = BookMetadataService()
