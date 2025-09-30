from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import json
import random
import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
current_dir = Path(__file__).parent.parent.parent  # Go up to project root
env_path = current_dir / ".env"
load_dotenv(env_path)

router = APIRouter()

# Pydantic models for request/response
class RecommendationRequest(BaseModel):
    detected_books: List[Dict[str, Any]]
    selected_genres: List[str]
    max_recommendations: int = 5

# Initialize OpenAI client with proxy support for office environments
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key and openai_api_key != "your_openai_api_key_here":
        # For office environments with proxies, we need to handle this differently
        # The new OpenAI client doesn't support proxies in constructor
        # So we'll use httpx client with proxy support
        
        import httpx
        
        # Check if we're in a proxy environment
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        # Create httpx client with minimal configuration to avoid proxy issues
        http_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Create OpenAI client with the custom httpx client
        openai_client = openai.OpenAI(api_key=openai_api_key, http_client=http_client)
        print("✅ OpenAI client initialized for recommendations")
    else:
        openai_client = None
        print("⚠️ OpenAI API key not set - will use fallback recommendations")
except Exception as e:
    openai_client = None
    print(f"❌ Failed to initialize OpenAI client: {e}")
    print(f"   This might be due to proxy settings. Check your network configuration.")

# Genre suggestions based on detected books with actual categorization
def get_genre_suggestions(detected_books: List[Dict]) -> List[str]:
    """
    Generate genre suggestions based on detected books with actual categorization
    """
    if not detected_books:
        return []
    
    # Extract genres from detected books
    detected_genres = []
    for book in detected_books:
        genre = book.get('genre', 'Fiction')
        if genre and genre != 'Unknown':
            detected_genres.append(genre)
    
    # If we have detected genres, use them
    if detected_genres:
        # Get unique genres and return top 5
        unique_genres = list(set(detected_genres))
        return unique_genres[:5]
    
    # Fallback to common genres if no categorization available
    common_genres = [
        "Fiction", "Non-Fiction", "Mystery", "Science Fiction", 
        "Fantasy", "Romance", "Thriller", "Biography", "History", 
        "Self-Help", "Business", "Technology", "Art", "Poetry", "Drama"
    ]
    
    return random.sample(common_genres, min(5, len(common_genres)))

# Image-based recommendations: Books similar to what you already have
def get_image_based_recommendations(detected_books: List[Dict], preferred_genres: List[str], max_recommendations: int = 10) -> List[Dict]:
    """
    Get recommendations based on the books detected in the uploaded image and user preferences
    """
    if not detected_books:
        return []
    
    # Get detected genres and authors
    detected_genres = set()
    detected_authors = set()
    detected_titles = set()
    
    for book in detected_books:
        if book.get('genre') and book['genre'] != 'Unknown':
            detected_genres.add(book['genre'])
        if book.get('author') and book['author'] != 'Unknown':
            detected_authors.add(book['author'])
        if book.get('title') and book['title'] != 'Unknown':
            detected_titles.add(book['title'].lower())
    
    # Curated recommendations based on detected content
    recommendations = []
    
    # High priority: Same genre + same author
    for book in get_curated_books():
        if (book['genre'] in detected_genres and 
            book['author'] in detected_authors and 
            book['title'].lower() not in detected_titles):
            book['recommendation_reason'] = f"Another {book['genre'].lower()} book by {book['author']}, similar to your collection"
            book['priority'] = 'high'
            recommendations.append(book)
    
    # Medium priority: Same genre, different author
    for book in get_curated_books():
        if (book['genre'] in detected_genres and 
            book['author'] not in detected_authors and 
            book['title'].lower() not in detected_titles and
            len(recommendations) < max_recommendations):
            book['recommendation_reason'] = f"Similar {book['genre'].lower()} book that matches your reading taste"
            book['priority'] = 'medium'
            recommendations.append(book)
    
    # Lower priority: Related genres
    related_genres = get_related_genres(detected_genres)
    for book in get_curated_books():
        if (book['genre'] in related_genres and 
            book['title'].lower() not in detected_titles and
            len(recommendations) < max_recommendations):
            book['recommendation_reason'] = f"Related {book['genre'].lower()} book that complements your collection"
            book['priority'] = 'low'
            recommendations.append(book)
    
    return recommendations[:max_recommendations]

# Genre-based recommendations: Books in your preferred genres
def get_genre_based_recommendations(preferred_genres: List[str], max_recommendations: int = 10) -> List[Dict]:
    """
    Get recommendations based on user's preferred genres
    """
    if not preferred_genres:
        return []
    
    recommendations = []
    curated_books = get_curated_books()
    
    # Sort books by rating within each genre
    genre_books = {}
    for book in curated_books:
        genre = book['genre']
        if genre not in genre_books:
            genre_books[genre] = []
        genre_books[genre].append(book)
    
    # Get top-rated books from each preferred genre
    for genre in preferred_genres:
        if genre in genre_books:
            # Sort by rating and take top books
            genre_books[genre].sort(key=lambda x: x['rating'], reverse=True)
            for book in genre_books[genre][:3]:  # Top 3 from each genre
                if len(recommendations) < max_recommendations:
                    book['recommendation_reason'] = f"Highly rated {genre.lower()} book in your preferred genres"
                    book['priority'] = 'high'
                    recommendations.append(book)
    
    # If we need more books, add from related genres
    if len(recommendations) < max_recommendations:
        related_genres = get_related_genres(set(preferred_genres))
        for genre in related_genres:
            if genre in genre_books and len(recommendations) < max_recommendations:
                genre_books[genre].sort(key=lambda x: x['rating'], reverse=True)
                for book in genre_books[genre][:2]:  # Top 2 from related genres
                    if len(recommendations) < max_recommendations:
                        book['recommendation_reason'] = f"Popular {genre.lower()} book that might interest you"
                        book['priority'] = 'medium'
                        recommendations.append(book)
    
    return recommendations[:max_recommendations]

# Get related genres for better recommendations
def get_related_genres(genres: set) -> set:
    """
    Get genres related to the input genres
    """
    related_map = {
        'Fiction': {'Romance', 'Mystery', 'Thriller', 'Drama'},
        'Science Fiction': {'Fantasy', 'Technology'},
        'Fantasy': {'Science Fiction', 'Fiction'},
        'Mystery': {'Thriller', 'Fiction'},
        'Thriller': {'Mystery', 'Fiction'},
        'Romance': {'Fiction', 'Drama'},
        'Non-Fiction': {'Biography', 'History', 'Self-Help', 'Business'},
        'Biography': {'Non-Fiction', 'History'},
        'History': {'Biography', 'Non-Fiction'},
        'Self-Help': {'Non-Fiction', 'Business'},
        'Business': {'Self-Help', 'Non-Fiction', 'Technology'},
        'Technology': {'Business', 'Science Fiction'},
        'Art': {'Poetry', 'Drama'},
        'Poetry': {'Art', 'Drama'},
        'Drama': {'Poetry', 'Art', 'Fiction'}
    }
    
    related = set()
    for genre in genres:
        if genre in related_map:
            related.update(related_map[genre])
    
    # Remove original genres
    related = related - genres
    return related

# Curated book database with intelligent recommendations
def get_curated_books() -> List[Dict]:
    """
    Get a curated list of high-quality books for recommendations
    """
    return [
        # Fiction
        {
            "title": "The Seven Husbands of Evelyn Hugo",
            "author": "Taylor Jenkins Reid",
            "genre": "Fiction",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1501139238",
            "bookshop_url": "https://bookshop.org/books/the-seven-husbands-of-evelyn-hugo/9781501139239",
            "reason": "A compelling character-driven story that matches your fiction preferences",
            "source": "Goodreads"
        },
        {
            "title": "The Midnight Library",
            "author": "Matt Haig",
            "genre": "Fiction",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0525559477",
            "bookshop_url": "https://bookshop.org/books/the-midnight-library/9780525559474",
            "reason": "A thought-provoking novel about life choices and second chances",
            "source": "Goodreads"
        },
        {
            "title": "Where the Crawdads Sing",
            "author": "Delia Owens",
            "genre": "Fiction",
            "rating": 4.6,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0735219095",
            "bookshop_url": "https://bookshop.org/books/where-the-crawdads-sing/9780735219090",
            "reason": "A beautiful coming-of-age story with mystery elements",
            "source": "Goodreads"
        },
        {
            "title": "The Kite Runner",
            "author": "Khaled Hosseini",
            "genre": "Fiction",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/159463193X",
            "bookshop_url": "https://bookshop.org/books/the-kite-runner/9781594631931",
            "reason": "A powerful story of friendship and redemption",
            "source": "Goodreads"
        },
        
        # Science Fiction
        {
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "genre": "Science Fiction",
            "rating": 4.7,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0593135202",
            "bookshop_url": "https://bookshop.org/books/project-hail-mary/9780593135204",
            "reason": "A thrilling sci-fi adventure that matches your reading preferences",
            "source": "Goodreads"
        },
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "genre": "Science Fiction",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0441172717",
            "bookshop_url": "https://bookshop.org/books/dune/9780441172719",
            "reason": "A classic epic sci-fi masterpiece with complex world-building",
            "source": "Goodreads"
        },
        {
            "title": "The Martian",
            "author": "Andy Weir",
            "genre": "Science Fiction",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0553418025",
            "bookshop_url": "https://bookshop.org/books/the-martian/9780553418026",
            "reason": "A gripping survival story set on Mars with scientific accuracy",
            "source": "Goodreads"
        },
        {
            "title": "Foundation",
            "author": "Isaac Asimov",
            "genre": "Science Fiction",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0553293354",
            "bookshop_url": "https://bookshop.org/books/foundation/9780553293357",
            "reason": "A foundational work of science fiction with grand scope",
            "source": "Goodreads"
        },
        
        # Fantasy
        {
            "title": "The Name of the Wind",
            "author": "Patrick Rothfuss",
            "genre": "Fantasy",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0756404746",
            "bookshop_url": "https://bookshop.org/books/the-name-of-the-wind/9780756404741",
            "reason": "An epic fantasy with beautiful prose and intricate magic system",
            "source": "Goodreads"
        },
        {
            "title": "Mistborn: The Final Empire",
            "author": "Brandon Sanderson",
            "genre": "Fantasy",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/076531178X",
            "bookshop_url": "https://bookshop.org/books/mistborn-the-final-empire/9780765311788",
            "reason": "A unique magic system and compelling heist story",
            "source": "Goodreads"
        },
        {
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "genre": "Fantasy",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/054792822X",
            "bookshop_url": "https://bookshop.org/books/the-hobbit/9780547928227",
            "reason": "A timeless fantasy adventure that started it all",
            "source": "Goodreads"
        },
        
        # Mystery/Thriller
        {
            "title": "The Silent Patient",
            "author": "Alex Michaelides",
            "genre": "Thriller",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1250301696",
            "bookshop_url": "https://bookshop.org/books/the-silent-patient/9781250301697",
            "reason": "A psychological thriller that will keep you guessing until the end",
            "source": "Goodreads"
        },
        {
            "title": "Gone Girl",
            "author": "Gillian Flynn",
            "genre": "Thriller",
            "rating": 4.1,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/030758836X",
            "bookshop_url": "https://bookshop.org/books/gone-girl/9780307588364",
            "reason": "A twisted psychological thriller with unreliable narrators",
            "source": "Goodreads"
        },
        {
            "title": "The Girl with the Dragon Tattoo",
            "author": "Stieg Larsson",
            "genre": "Mystery",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0307269752",
            "bookshop_url": "https://bookshop.org/books/the-girl-with-the-dragon-tattoo/9780307269751",
            "reason": "A complex mystery with strong characters and social commentary",
            "source": "Goodreads"
        },
        {
            "title": "The Da Vinci Code",
            "author": "Dan Brown",
            "genre": "Mystery",
            "rating": 4.0,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0307474275",
            "bookshop_url": "https://bookshop.org/books/the-da-vinci-code/9780307474278",
            "reason": "A fast-paced mystery thriller with historical elements",
            "source": "Goodreads"
        },
        
        # Romance
        {
            "title": "The Hating Game",
            "author": "Sally Thorne",
            "genre": "Romance",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0062439598",
            "bookshop_url": "https://bookshop.org/books/the-hating-game/9780062439598",
            "reason": "A delightful enemies-to-lovers romance with great chemistry",
            "source": "Goodreads"
        },
        {
            "title": "Beach Read",
            "author": "Emily Henry",
            "genre": "Romance",
            "rating": 4.1,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1984806734",
            "bookshop_url": "https://bookshop.org/books/beach-read/9781984806734",
            "reason": "A charming romance with depth and humor",
            "source": "Goodreads"
        },
        {
            "title": "The Kiss Quotient",
            "author": "Helen Hoang",
            "genre": "Romance",
            "rating": 4.0,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0451490807",
            "bookshop_url": "https://bookshop.org/books/the-kiss-quotient/9780451490803",
            "reason": "A unique romance with neurodiverse representation",
            "source": "Goodreads"
        },
        
        # Non-Fiction
        {
            "title": "Sapiens",
            "author": "Yuval Noah Harari",
            "genre": "Non-Fiction",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0062316095",
            "bookshop_url": "https://bookshop.org/books/sapiens/9780062316097",
            "reason": "A fascinating exploration of human history and development",
            "source": "Goodreads"
        },
        {
            "title": "Educated",
            "author": "Tara Westover",
            "genre": "Biography",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0399590501",
            "bookshop_url": "https://bookshop.org/books/educated/9780399590504",
            "reason": "A powerful memoir about education, family, and self-discovery",
            "source": "Goodreads"
        },
        {
            "title": "Thinking, Fast and Slow",
            "author": "Daniel Kahneman",
            "genre": "Business",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0374533555",
            "bookshop_url": "https://bookshop.org/books/thinking-fast-and-slow/9780374533557",
            "reason": "A fascinating exploration of how our minds make decisions",
            "source": "Goodreads"
        },
        {
            "title": "Atomic Habits",
            "author": "James Clear",
            "genre": "Self-Help",
            "rating": 4.8,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0735211299",
            "bookshop_url": "https://bookshop.org/books/atomic-habits/9780735211292",
            "reason": "A practical guide to building good habits and breaking bad ones",
            "source": "Goodreads"
        },
        {
            "title": "The Power of Now",
            "author": "Eckhart Tolle",
            "genre": "Self-Help",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1577314808",
            "bookshop_url": "https://bookshop.org/books/the-power-of-now/9781577314806",
            "reason": "A transformative guide to spiritual enlightenment and mindfulness",
            "source": "Goodreads"
        },
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "genre": "Technology",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0132350882",
            "bookshop_url": "https://bookshop.org/books/clean-code/9780132350884",
            "reason": "Essential principles for writing maintainable software",
            "source": "Goodreads"
        },
        {
            "title": "The Pragmatic Programmer",
            "author": "David Thomas",
            "genre": "Technology",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/020161622X",
            "bookshop_url": "https://bookshop.org/books/the-pragmatic-programmer/9780201616224",
            "reason": "Timeless advice for becoming a better programmer",
            "source": "Goodreads"
        }
    ]

# Enhanced book recommendations based on detected books and user preferences
def get_book_recommendations(detected_books: List[Dict], preferred_genres: List[str], max_recommendations: int = 20) -> List[Dict]:
    """
    Generate book recommendations based on detected books and preferred genres
    """
    # Enhanced book database with more diverse recommendations
    sample_books = [
        # Fiction
        {
            "title": "The Seven Husbands of Evelyn Hugo",
            "author": "Taylor Jenkins Reid",
            "genre": "Fiction",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1501139238",
            "bookshop_url": "https://bookshop.org/books/the-seven-husbands-of-evelyn-hugo/9781501139239",
            "reason": "A compelling character-driven story that matches your fiction preferences",
            "source": "Goodreads"
        },
        {
            "title": "The Midnight Library",
            "author": "Matt Haig",
            "genre": "Fiction",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0525559477",
            "bookshop_url": "https://bookshop.org/books/the-midnight-library/9780525559474",
            "reason": "A thought-provoking novel about life choices and second chances",
            "source": "Goodreads"
        },
        {
            "title": "Where the Crawdads Sing",
            "author": "Delia Owens",
            "genre": "Fiction",
            "rating": 4.6,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0735219095",
            "bookshop_url": "https://bookshop.org/books/where-the-crawdads-sing/9780735219090",
            "reason": "A beautiful coming-of-age story with mystery elements",
            "source": "Goodreads"
        },
        
        # Science Fiction
        {
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "genre": "Science Fiction",
            "rating": 4.7,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0593135202",
            "bookshop_url": "https://bookshop.org/books/project-hail-mary/9780593135204",
            "reason": "A thrilling sci-fi adventure that matches your reading preferences",
            "source": "Goodreads"
        },
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "genre": "Science Fiction",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0441172717",
            "bookshop_url": "https://bookshop.org/books/dune/9780441172719",
            "reason": "A classic epic sci-fi masterpiece with complex world-building",
            "source": "Goodreads"
        },
        {
            "title": "The Martian",
            "author": "Andy Weir",
            "genre": "Science Fiction",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0553418025",
            "bookshop_url": "https://bookshop.org/books/the-martian/9780553418026",
            "reason": "A gripping survival story set on Mars with scientific accuracy",
            "source": "Goodreads"
        },
        
        # Fantasy
        {
            "title": "The Name of the Wind",
            "author": "Patrick Rothfuss",
            "genre": "Fantasy",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0756404746",
            "bookshop_url": "https://bookshop.org/books/the-name-of-the-wind/9780756404741",
            "reason": "An epic fantasy with beautiful prose and intricate magic system",
            "source": "Goodreads"
        },
        {
            "title": "Mistborn: The Final Empire",
            "author": "Brandon Sanderson",
            "genre": "Fantasy",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/076531178X",
            "bookshop_url": "https://bookshop.org/books/mistborn-the-final-empire/9780765311788",
            "reason": "A unique magic system and compelling heist story",
            "source": "Goodreads"
        },
        
        # Mystery/Thriller
        {
            "title": "The Silent Patient",
            "author": "Alex Michaelides",
            "genre": "Thriller",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1250301696",
            "bookshop_url": "https://bookshop.org/books/the-silent-patient/9781250301697",
            "reason": "A psychological thriller that will keep you guessing until the end",
            "source": "Goodreads"
        },
        {
            "title": "Gone Girl",
            "author": "Gillian Flynn",
            "genre": "Thriller",
            "rating": 4.1,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/030758836X",
            "bookshop_url": "https://bookshop.org/books/gone-girl/9780307588364",
            "reason": "A twisted psychological thriller with unreliable narrators",
            "source": "Goodreads"
        },
        {
            "title": "The Girl with the Dragon Tattoo",
            "author": "Stieg Larsson",
            "genre": "Mystery",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0307269752",
            "bookshop_url": "https://bookshop.org/books/the-girl-with-the-dragon-tattoo/9780307269751",
            "reason": "A complex mystery with strong characters and social commentary",
            "source": "Goodreads"
        },
        
        # Romance
        {
            "title": "The Hating Game",
            "author": "Sally Thorne",
            "genre": "Romance",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0062439598",
            "bookshop_url": "https://bookshop.org/books/the-hating-game/9780062439598",
            "reason": "A delightful enemies-to-lovers romance with great chemistry",
            "source": "Goodreads"
        },
        {
            "title": "Beach Read",
            "author": "Emily Henry",
            "genre": "Romance",
            "rating": 4.1,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1984806734",
            "bookshop_url": "https://bookshop.org/books/beach-read/9781984806734",
            "reason": "A charming romance with depth and humor",
            "source": "Goodreads"
        },
        
        # Non-Fiction
        {
            "title": "Sapiens",
            "author": "Yuval Noah Harari",
            "genre": "Non-Fiction",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0062316095",
            "bookshop_url": "https://bookshop.org/books/sapiens/9780062316097",
            "reason": "A fascinating exploration of human history and development",
            "source": "Goodreads"
        },
        {
            "title": "Educated",
            "author": "Tara Westover",
            "genre": "Biography",
            "rating": 4.5,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0399590501",
            "bookshop_url": "https://bookshop.org/books/educated/9780399590504",
            "reason": "A powerful memoir about education, family, and self-discovery",
            "source": "Goodreads"
        },
        
        # Self-Help
        {
            "title": "Atomic Habits",
            "author": "James Clear",
            "genre": "Self-Help",
            "rating": 4.8,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0735211299",
            "bookshop_url": "https://bookshop.org/books/atomic-habits/9780735211292",
            "reason": "A practical guide to building good habits and breaking bad ones",
            "source": "Goodreads"
        },
        {
            "title": "The Power of Now",
            "author": "Eckhart Tolle",
            "genre": "Self-Help",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/1577314808",
            "bookshop_url": "https://bookshop.org/books/the-power-of-now/9781577314806",
            "reason": "A transformative guide to spiritual enlightenment and mindfulness",
            "source": "Goodreads"
        },
        
        # Business
        {
            "title": "Thinking, Fast and Slow",
            "author": "Daniel Kahneman",
            "genre": "Business",
            "rating": 4.2,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0374533555",
            "bookshop_url": "https://bookshop.org/books/thinking-fast-and-slow/9780374533557",
            "reason": "A fascinating exploration of how our minds make decisions",
            "source": "Goodreads"
        },
        {
            "title": "The Lean Startup",
            "author": "Eric Ries",
            "genre": "Business",
            "rating": 4.1,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0307887898",
            "bookshop_url": "https://bookshop.org/books/the-lean-startup/9780307887894",
            "reason": "A revolutionary approach to building successful businesses",
            "source": "Goodreads"
        },
        
        # Technology
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "genre": "Technology",
            "rating": 4.4,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/0132350882",
            "bookshop_url": "https://bookshop.org/books/clean-code/9780132350884",
            "reason": "Essential principles for writing maintainable software",
            "source": "Goodreads"
        },
        {
            "title": "The Pragmatic Programmer",
            "author": "David Thomas",
            "genre": "Technology",
            "rating": 4.3,
            "cover_url": "https://images-na.ssl-images-amazon.com/images/I/81Z5Q6Q6Q6L.jpg",
            "amazon_url": "https://amazon.com/dp/020161622X",
            "bookshop_url": "https://bookshop.org/books/the-pragmatic-programmer/9780201616224",
            "reason": "Timeless advice for becoming a better programmer",
            "source": "Goodreads"
        }
    ]
    
    # Get detected genres from the user's books
    detected_genres = set()
    for book in detected_books:
        genre = book.get('genre', '')
        if genre and genre != 'Unknown':
            detected_genres.add(genre)
    
    # Prioritize recommendations based on detected genres and user preferences
    priority_books = []
    secondary_books = []
    
    for book in sample_books:
        book_genre = book["genre"]
        
        # High priority: matches both detected genres AND user preferences
        if book_genre in detected_genres and book_genre in preferred_genres:
            priority_books.append(book)
        # Medium priority: matches user preferences
        elif book_genre in preferred_genres:
            secondary_books.append(book)
    
    # Sort by rating within each priority group
    priority_books.sort(key=lambda x: x["rating"], reverse=True)
    secondary_books.sort(key=lambda x: x["rating"], reverse=True)
    
    # Combine recommendations
    recommendations = priority_books + secondary_books
    
    # If we still need more books, add some from detected genres
    if len(recommendations) < max_recommendations:
        remaining_books = [book for book in sample_books 
                          if book not in recommendations and book["genre"] in detected_genres]
        remaining_books.sort(key=lambda x: x["rating"], reverse=True)
        recommendations.extend(remaining_books)
    
    # Final fallback: add any remaining books
    if len(recommendations) < max_recommendations:
        final_books = [book for book in sample_books if book not in recommendations]
        final_books.sort(key=lambda x: x["rating"], reverse=True)
        recommendations.extend(final_books)
    
    return recommendations[:max_recommendations]

# OpenAI-powered book recommendations
def get_openai_recommendations(detected_books: List[Dict], selected_genres: List[str], max_recommendations: int = 5) -> List[Dict]:
    """
    Generate book recommendations using OpenAI API based on user preferences and detected books
    """
    if not openai_client:
        print("⚠️ OpenAI client not available, using fallback recommendations")
        return get_fallback_recommendations(detected_books, selected_genres, max_recommendations)
    
    try:
        # Prepare the prompt for OpenAI
        detected_titles = [book.get('title', 'Unknown') for book in detected_books if book.get('title')]
        detected_authors = [book.get('author', 'Unknown') for book in detected_books if book.get('author')]
        detected_genres = [book.get('genre', 'Unknown') for book in detected_books if book.get('genre')]
        
        # Create comprehensive prompt
        prompt = f"""
You are an expert book recommendation system. Based on the user's preferences and their current book collection, recommend new books they would enjoy.

USER'S PREFERRED GENRES: {', '.join(selected_genres)}

BOOKS ALREADY IN THEIR COLLECTION:
{chr(10).join([f"- {book.get('title', 'Unknown')} by {book.get('author', 'Unknown')} ({book.get('genre', 'Unknown')})" for book in detected_books])}

DETECTED GENRES IN COLLECTION: {', '.join(set(detected_genres))}
DETECTED AUTHORS IN COLLECTION: {', '.join(set(detected_authors))}

REQUIREMENTS:
1. Recommend EXACTLY {max_recommendations} books (no more, no less) that match the user's preferred genres
2. DO NOT recommend any books already in their collection (listed above)
3. Focus on books that align with their genre preferences: {', '.join(selected_genres)}
4. Consider books by authors similar to those they already have
5. Include a mix of popular and lesser-known but excellent books
6. Provide diverse recommendations within their preferred genres
7. IMPORTANT: Return exactly {max_recommendations} books in the JSON array

For each recommendation, provide:
- Title
- Author
- Genre (must be one of their preferred genres: {', '.join(selected_genres)})
- Rating (1-5 scale)
- Brief reason why they would enjoy it
- Amazon URL (use format: https://amazon.com/dp/[ISBN])
- Bookshop URL (use format: https://bookshop.org/books/[title]/[ISBN])

Format your response as a JSON array with EXACTLY {max_recommendations} books using this structure:
[
  {{
    "title": "Book Title 1",
    "author": "Author Name 1",
    "genre": "Genre",
    "rating": 4.5,
    "reason": "Why they would enjoy this book",
    "amazon_url": "https://amazon.com/dp/1234567890",
    "bookshop_url": "https://bookshop.org/books/book-title/1234567890",
    "source": "OpenAI Recommendation"
  }},
  {{
    "title": "Book Title 2",
    "author": "Author Name 2",
    "genre": "Genre",
    "rating": 4.2,
    "reason": "Why they would enjoy this book",
    "amazon_url": "https://amazon.com/dp/0987654321",
    "bookshop_url": "https://bookshop.org/books/book-title-2/0987654321",
    "source": "OpenAI Recommendation"
  }}
  // ... continue for all {max_recommendations} books
]

Return ONLY the JSON array with exactly {max_recommendations} books, no additional text.
"""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert book recommendation system. Always respond with valid JSON arrays containing book recommendations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        
        # Clean up the response (remove any markdown formatting)
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        # Parse JSON
        recommendations = json.loads(response_text)
        
        # Validate and clean the recommendations
        validated_recommendations = []
        for rec in recommendations:
            if isinstance(rec, dict) and all(key in rec for key in ['title', 'author', 'genre']):
                # Ensure genre is in user's preferred genres
                if rec['genre'] in selected_genres:
                    validated_recommendations.append(rec)
        
        print(f"✅ OpenAI generated {len(validated_recommendations)} recommendations")
        return validated_recommendations[:max_recommendations]
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse OpenAI response as JSON: {e}")
        print(f"Response: {response_text}")
        return get_fallback_recommendations(detected_books, selected_genres, max_recommendations)
    except Exception as e:
        print(f"❌ OpenAI recommendation error: {e}")
        return get_fallback_recommendations(detected_books, selected_genres, max_recommendations)

def get_fallback_recommendations(detected_books: List[Dict], selected_genres: List[str], max_recommendations: int = 5) -> List[Dict]:
    """
    Fallback recommendation system when OpenAI is not available
    """
    # Get detected titles to exclude
    detected_titles = {book.get('title', '').lower() for book in detected_books if book.get('title')}
    
    # Filter curated books by user preferences and exclude detected books
    curated_books = get_curated_books()
    recommendations = []
    
    for book in curated_books:
        if (book['genre'] in selected_genres and 
            book['title'].lower() not in detected_titles and
            len(recommendations) < max_recommendations):
            book['source'] = 'Fallback Recommendation'
            recommendations.append(book)
    
    return recommendations

@router.post("/genres")
async def recommend_genres(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get genre suggestions based on detected books
    
    Args:
        request: Dict containing detected_books list
        
    Returns:
        Dict containing suggested genres
    """
    try:
        detected_books = request.get("detected_books", [])
        suggested_genres = get_genre_suggestions(detected_books)
        
        return {
            "suggested_genres": suggested_genres,
            "total_detected": len(detected_books),
            "message": "Genre suggestions generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate genre suggestions: {str(e)}")

@router.post("/books")
async def recommend_books(request: RecommendationRequest) -> Dict[str, Any]:
    """
    Get book recommendations based on detected books and preferred genres using OpenAI API
    
    Args:
        request: RecommendationRequest containing detected_books, selected_genres, and max_recommendations
        
    Returns:
        Dict containing OpenAI-powered recommendations
    """
    try:
        print(f"🔍 Generating recommendations for {len(request.detected_books)} detected books")
        print(f"📚 User preferred genres: {request.selected_genres}")
        
        # Get OpenAI-powered recommendations
        recommendations = get_openai_recommendations(
            request.detected_books, 
            request.selected_genres, 
            request.max_recommendations
        )
        
        # Fetch metadata for recommended books (covers, ratings, etc.)
        enhanced_recommendations = []
        if recommendations:
            try:
                print("📚 Fetching metadata for recommended books...")
                from ..services.book_metadata import metadata_service
                
                # Prepare books for metadata fetching
                books_for_metadata = []
                for book in recommendations:
                    books_for_metadata.append({
                        'title': book.get('title', ''),
                        'author': book.get('author', '')
                    })
                
                # Fetch metadata
                enhanced_recommendations = metadata_service.get_multiple_books_metadata(books_for_metadata)
                print(f"✅ Enhanced {len(enhanced_recommendations)} recommendations with metadata")
                
            except Exception as e:
                print(f"⚠️ Failed to fetch metadata for recommendations: {e}")
                enhanced_recommendations = recommendations  # Fallback to original data
        else:
            enhanced_recommendations = recommendations
        
        # Get fallback recommendations for comparison
        fallback_recommendations = get_fallback_recommendations(
            request.detected_books, 
            request.selected_genres, 
            request.max_recommendations
        )
        
        # Calculate statistics
        detected_titles = [book.get('title', '') for book in request.detected_books if book.get('title')]
        detected_genres = [book.get('genre', '') for book in request.detected_books if book.get('genre')]
        
        return {
            "recommendations": enhanced_recommendations,  # Return enhanced recommendations with metadata
            "fallback_recommendations": fallback_recommendations,
            "total_recommendations": len(enhanced_recommendations),
            "detected_books_count": len(request.detected_books),
            "detected_titles": detected_titles,
            "detected_genres": list(set(detected_genres)),
            "selected_genres": request.selected_genres,
            "recommendation_source": "OpenAI API" if openai_client else "Fallback System",
            "message": f"Generated {len(enhanced_recommendations)} personalized recommendations based on your preferences and collection"
        }
        
    except Exception as e:
        print(f"❌ Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

@router.post("/books/legacy")
async def recommend_books_legacy(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy recommendation endpoint for backward compatibility
    
    Args:
        request: Dict containing detected_books, preferred_genres, and max_recommendations
        
    Returns:
        Dict containing two sections of recommendations
    """
    try:
        detected_books = request.get("detected_books", [])
        preferred_genres = request.get("preferred_genres", [])
        max_recommendations = request.get("max_recommendations", 20)
        
        # Get recommendations for both sections
        image_based_recommendations = get_image_based_recommendations(detected_books, preferred_genres, max_recommendations // 2)
        genre_based_recommendations = get_genre_based_recommendations(preferred_genres, max_recommendations // 2)
        
        return {
            "image_based_recommendations": image_based_recommendations,
            "genre_based_recommendations": genre_based_recommendations,
            "total_image_recommendations": len(image_based_recommendations),
            "total_genre_recommendations": len(genre_based_recommendations),
            "detected_books_count": len(detected_books),
            "preferred_genres": preferred_genres,
            "message": "Legacy recommendations generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate legacy recommendations: {str(e)}")

