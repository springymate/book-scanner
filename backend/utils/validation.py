import re
from typing import List, Dict, Any, Optional
from pathlib import Path

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_file_upload(file_path: str, allowed_extensions: List[str], max_size: int) -> bool:
    """
    Validate file upload parameters
    
    Args:
        file_path: Path to the uploaded file
        allowed_extensions: List of allowed file extensions
        max_size: Maximum file size in bytes
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Check if file exists
        if not Path(file_path).exists():
            raise ValidationError("File does not exist")
        
        # Check file extension
        file_extension = Path(file_path).suffix.lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(f"File extension '{file_extension}' not allowed. Allowed: {allowed_extensions}")
        
        # Check file size
        file_size = Path(file_path).stat().st_size
        if file_size > max_size:
            raise ValidationError(f"File too large: {file_size} bytes. Maximum: {max_size} bytes")
        
        # Check if file is not empty
        if file_size == 0:
            raise ValidationError("File is empty")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"File validation error: {str(e)}")

def validate_book_data(book_data: Dict[str, Any]) -> bool:
    """
    Validate book data structure and content
    
    Args:
        book_data: Dictionary containing book information
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Check required fields
        required_fields = ['title', 'author', 'isValid']
        for field in required_fields:
            if field not in book_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate title
        title = book_data.get('title', '').strip()
        if not title:
            raise ValidationError("Title cannot be empty")
        
        if len(title) > 500:
            raise ValidationError("Title too long (max 500 characters)")
        
        # Validate author
        author = book_data.get('author', '').strip()
        if not author:
            raise ValidationError("Author cannot be empty")
        
        if len(author) > 200:
            raise ValidationError("Author name too long (max 200 characters)")
        
        # Validate isValid field
        if not isinstance(book_data.get('isValid'), bool):
            raise ValidationError("isValid must be a boolean")
        
        # Validate optional fields if present
        if 'rating' in book_data:
            rating = book_data['rating']
            if not isinstance(rating, (int, float)) or not (0 <= rating <= 5):
                raise ValidationError("Rating must be a number between 0 and 5")
        
        if 'reasoning' in book_data:
            reasoning = book_data['reasoning']
            if not isinstance(reasoning, str):
                raise ValidationError("Reasoning must be a string")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Book data validation error: {str(e)}")

def validate_genre_list(genres: List[str]) -> bool:
    """
    Validate list of genres
    
    Args:
        genres: List of genre strings
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        if not isinstance(genres, list):
            raise ValidationError("Genres must be a list")
        
        if len(genres) == 0:
            raise ValidationError("At least one genre must be provided")
        
        if len(genres) > 20:
            raise ValidationError("Too many genres (max 20)")
        
        # Validate each genre
        for genre in genres:
            if not isinstance(genre, str):
                raise ValidationError("Each genre must be a string")
            
            genre = genre.strip()
            if not genre:
                raise ValidationError("Genre cannot be empty")
            
            if len(genre) > 50:
                raise ValidationError(f"Genre name too long: {genre}")
            
            # Check for valid characters (letters, spaces, hyphens, apostrophes)
            if not re.match(r"^[a-zA-Z\s\-']+$", genre):
                raise ValidationError(f"Invalid genre name: {genre}")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Genre validation error: {str(e)}")

def validate_api_key(api_key: str, key_type: str = "API") -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key string
        key_type: Type of API key for error messages
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        if not api_key:
            raise ValidationError(f"{key_type} key is required")
        
        if not isinstance(api_key, str):
            raise ValidationError(f"{key_type} key must be a string")
        
        api_key = api_key.strip()
        if len(api_key) < 10:
            raise ValidationError(f"{key_type} key too short (min 10 characters)")
        
        if len(api_key) > 200:
            raise ValidationError(f"{key_type} key too long (max 200 characters)")
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9\-_]+$", api_key):
            raise ValidationError(f"Invalid {key_type} key format")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"{key_type} key validation error: {str(e)}")

def validate_file_id(file_id: str) -> bool:
    """
    Validate file ID format (UUID)
    
    Args:
        file_id: File ID string
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        if not file_id:
            raise ValidationError("File ID is required")
        
        if not isinstance(file_id, str):
            raise ValidationError("File ID must be a string")
        
        file_id = file_id.strip()
        
        # Check UUID format (basic pattern)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, file_id, re.IGNORECASE):
            raise ValidationError("Invalid file ID format (must be UUID)")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"File ID validation error: {str(e)}")

def validate_pagination_params(page: int, per_page: int) -> bool:
    """
    Validate pagination parameters
    
    Args:
        page: Page number (1-based)
        per_page: Items per page
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        if not isinstance(page, int) or page < 1:
            raise ValidationError("Page must be a positive integer")
        
        if not isinstance(per_page, int) or per_page < 1:
            raise ValidationError("Per page must be a positive integer")
        
        if per_page > 100:
            raise ValidationError("Per page cannot exceed 100")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Pagination validation error: {str(e)}")

def sanitize_string(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing potentially harmful characters
    
    Args:
        input_string: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized string
    """
    if not isinstance(input_string, str):
        return ""
    
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', input_string)
    
    # Limit length
    sanitized = sanitized[:max_length]
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized

def validate_recommendation_params(
    detected_books: List[Dict],
    preferred_genres: List[str],
    max_recommendations: int
) -> bool:
    """
    Validate recommendation request parameters
    
    Args:
        detected_books: List of detected book data
        preferred_genres: List of preferred genres
        max_recommendations: Maximum number of recommendations
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Validate detected_books
        if not isinstance(detected_books, list):
            raise ValidationError("Detected books must be a list")
        
        # Validate each book in detected_books
        for i, book in enumerate(detected_books):
            if not isinstance(book, dict):
                raise ValidationError(f"Book at index {i} must be a dictionary")
            
            validate_book_data(book)
        
        # Validate preferred_genres
        validate_genre_list(preferred_genres)
        
        # Validate max_recommendations
        if not isinstance(max_recommendations, int):
            raise ValidationError("Max recommendations must be an integer")
        
        if max_recommendations < 1:
            raise ValidationError("Max recommendations must be at least 1")
        
        if max_recommendations > 50:
            raise ValidationError("Max recommendations cannot exceed 50")
        
        # Check that at least one source of recommendations is provided
        if not detected_books and not preferred_genres:
            raise ValidationError("Either detected books or preferred genres must be provided")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Recommendation parameter validation error: {str(e)}")

