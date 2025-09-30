from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile
from pathlib import Path
try:
    from book_detector.book_detector import BookSpineDetector
except ImportError:
    from backend.book_detector.book_detector import BookSpineDetector
import os
import cv2
import numpy as np
import uuid
from typing import Dict, List, Any, Union
import json
from dotenv import load_dotenv
from io import BytesIO
from pydantic import BaseModel

# Load environment variables from .env file
# Look for .env file in the project root (one level up from backend)
current_dir = Path(__file__).parent.parent.parent  # Go up to project root
env_path = current_dir / ".env"
load_dotenv(env_path)

router = APIRouter()

# Pydantic models for request/response
class FileIdRequest(BaseModel):
    file_id: str

class AnalyzeWithPreferencesRequest(BaseModel):
    file_id: str
    selected_genres: List[str]

# Initialize detector (you'll need to set up environment variables)
try:
    # Get the correct path to the model file
    current_dir = Path(__file__).parent.parent.parent  # Go up to project root
    model_path = current_dir / "models" / "yolo_weights" / "best.pt"
    
    # Check if model file exists
    if not model_path.exists():
        print(f"❌ Model file not found at: {model_path}")
        detector = None
    else:
        # Check if OpenAI API key is set
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your_openai_api_key_here":
            print("❌ OpenAI API key not set. Please update .env file with your actual API key.")
            detector = None
        else:
            detector = BookSpineDetector(
                model_path=str(model_path),
                openai_api_key=openai_key
            )
            print("✅ BookSpineDetector initialized successfully")
            
except Exception as e:
    print(f"❌ Error initializing detector: {e}")
    print(f"   Error type: {type(e).__name__}")
    detector = None

@router.post("/books")
async def analyze_books(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Analyze uploaded image for book spines and extract metadata
    
    Args:
        file: Uploaded image file
        
    Returns:
        Dict containing detected books and analysis results
    """
    print(f"🔍 Analyze books endpoint called with file: {file.filename}")
    
    if not detector:
        error_msg = "Book detector not initialized. "
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
            error_msg += "Please set your OpenAI API key in the .env file."
        else:
            error_msg += "YOLO model failed to load. Check server logs for details. The application can still work with basic functionality."
        raise HTTPException(status_code=500, detail=error_msg)
    
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        file_content = await file.read()
        
        # Convert bytes to numpy array for OpenCV
        nparr = np.frombuffer(file_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Analyze the image directly
        results = detector.detect_books(image)
        
        # Get annotations data for drawing
        annotations_data = detector.get_annotations_data(image)
        
        # Create annotated image (simplified for now)
        annotated_image = image.copy()
        
        # Save annotated image
        file_id = str(uuid.uuid4())
        annotated_image_path = f"static/results/{file_id}_annotated.jpg"
        os.makedirs(os.path.dirname(annotated_image_path), exist_ok=True)
        cv2.imwrite(annotated_image_path, annotated_image)
        
        # Also save the original image for future reference
        original_image_path = f"static/uploads/{file_id}.jpg"
        os.makedirs(os.path.dirname(original_image_path), exist_ok=True)
        cv2.imwrite(original_image_path, image)
        
        # Get genre statistics
        genre_stats = {}
        if detector and results:
            try:
                genre_stats = detector.get_genre_statistics(results)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                genre_stats = {}
        
        return {
            "file_id": file_id,
            "books": results,
            "detected_books": results,
            "total_books": len(results),
            "valid_books": sum(1 for book in results if book.get('isValid', False)),
            "annotated_image_url": f"/static/results/{file_id}_annotated.jpg",
            "genre_statistics": genre_stats,
            "message": "Analysis completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/books-by-id")
async def analyze_books_by_id(request: FileIdRequest) -> Dict[str, Any]:
    """
    Analyze uploaded image for book spines and extract metadata
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing detected books and analysis results
    """
    if not detector:
        raise HTTPException(status_code=500, detail="Book detector not initialized. Check API keys.")
    
    try:
        # Find the uploaded file
        upload_dir = Path("static/uploads")
        files = list(upload_dir.glob(f"{request.file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        
        # Analyze the image
        books = detector.process_image(str(file_path))
        
        # Save results to JSON file
        results_path = Path("static/results") / f"{request.file_id}_analysis.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2, ensure_ascii=False)
        
        # Get genre statistics
        genre_stats = {}
        if detector and books:
            try:
                genre_stats = detector.get_genre_statistics(books)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                genre_stats = {}
        
        return {
            "books": books,
            "total_detected": len(books),
            "valid_extractions": sum(1 for book in books if book.get('isValid', False)),
            "analysis_id": request.file_id,
            "results_path": str(results_path),
            "genre_statistics": genre_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/books/{file_id}")
async def get_analysis_results(file_id: str) -> Dict[str, Any]:
    """
    Get previously analyzed book data
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing book analysis results
    """
    try:
        results_path = Path("static/results") / f"{file_id}_analysis.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        with open(results_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
        
        # Get genre statistics
        genre_stats = {}
        if detector and books:
            try:
                genre_stats = detector.get_genre_statistics(books)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                genre_stats = {}
        
        return {
            "books": books,
            "total_detected": len(books),
            "valid_extractions": sum(1 for book in books if book.get('isValid', False)),
            "analysis_id": file_id,
            "genre_statistics": genre_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@router.post("/annotations")
async def get_annotations(file_id: str) -> Dict:
    """
    Get annotation data for drawing bounding boxes
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing annotation data for frontend rendering
    """
    if not detector:
        raise HTTPException(status_code=500, detail="Book detector not initialized")
    
    try:
        # Find the uploaded file
        upload_dir = Path("static/uploads")
        files = list(upload_dir.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        
        # Load image
        image = cv2.imread(str(file_path))
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Get annotation data
        annotation_data = detector.get_annotations_data(image)
        
        return {
            "file_id": file_id,
            "annotations": annotation_data,
            "image_dimensions": {
                "width": image.shape[1],
                "height": image.shape[0]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get annotations: {str(e)}")

@router.delete("/books/{file_id}")
async def delete_analysis(file_id: str) -> Dict[str, str]:
    """
    Delete analysis results
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing deletion status
    """
    try:
        results_path = Path("static/results") / f"{file_id}_analysis.json"
        
        if results_path.exists():
            results_path.unlink()
        
        return {
            "file_id": file_id,
            "status": "deleted",
            "message": "Analysis results deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete analysis: {str(e)}")

@router.get("/genres")
async def get_available_genres() -> Dict[str, Any]:
    """
    Get the list of available genres for categorization
    
    Returns:
        Dict containing available genres
    """
    if not detector:
        raise HTTPException(status_code=500, detail="Book detector not initialized")
    
    try:
        available_genres = detector.get_available_genres()
        return {
            "genres": available_genres,
            "total_genres": len(available_genres),
            "message": "Available genres retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get genres: {str(e)}")

@router.post("/books/{file_id}/filter")
async def filter_books_by_genre(file_id: str, genres: List[str]) -> Dict[str, Any]:
    """
    Filter books by genre
    
    Args:
        file_id: Unique file identifier
        genres: List of genres to filter by
        
    Returns:
        Dict containing filtered books
    """
    try:
        results_path = Path("static/results") / f"{file_id}_analysis.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        with open(results_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
        
        # Filter books by genre
        filtered_books = []
        for book in books:
            book_genre = book.get('genre', 'Unknown')
            if book_genre in genres:
                filtered_books.append(book)
        
        # Get genre statistics for filtered results
        genre_stats = {}
        if detector and filtered_books:
            try:
                genre_stats = detector.get_genre_statistics(filtered_books)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                genre_stats = {}
        
        return {
            "books": filtered_books,
            "total_filtered": len(filtered_books),
            "total_original": len(books),
            "filtered_genres": genres,
            "genre_statistics": genre_stats,
            "analysis_id": file_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to filter books: {str(e)}")

@router.get("/books/{file_id}/statistics")
async def get_book_statistics(file_id: str) -> Dict[str, Any]:
    """
    Get comprehensive statistics for analyzed books
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing book statistics
    """
    try:
        results_path = Path("static/results") / f"{file_id}_analysis.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        with open(results_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
        
        # Calculate statistics
        total_books = len(books)
        valid_books = sum(1 for book in books if book.get('isValid', False))
        
        # Genre statistics
        genre_stats = {}
        if detector and books:
            try:
                genre_stats = detector.get_genre_statistics(books)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                genre_stats = {}
        
        # Author statistics
        author_stats = {}
        for book in books:
            author = book.get('author', 'Unknown')
            author_stats[author] = author_stats.get(author, 0) + 1
        
        # Confidence statistics
        confidence_stats = {'high': 0, 'low': 0, 'unknown': 0}
        for book in books:
            confidence = book.get('genre_confidence', 'unknown')
            if confidence in confidence_stats:
                confidence_stats[confidence] += 1
            else:
                confidence_stats['unknown'] += 1
        
        return {
            "analysis_id": file_id,
            "total_books": total_books,
            "valid_books": valid_books,
            "invalid_books": total_books - valid_books,
            "genre_statistics": genre_stats,
            "author_statistics": author_stats,
            "confidence_statistics": confidence_stats,
            "most_common_genre": max(genre_stats.items(), key=lambda x: x[1])[0] if genre_stats else "Unknown",
            "most_common_author": max(author_stats.items(), key=lambda x: x[1])[0] if author_stats else "Unknown"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/books/analyze-with-preferences")
async def analyze_books_with_preferences(request: AnalyzeWithPreferencesRequest) -> Dict[str, Any]:
    """
    Analyze uploaded image for book spines, extract metadata, and filter by user preferences
    
    Args:
        request: Request containing file_id and selected genres
        
    Returns:
        Dict containing filtered books that match user preferences
    """
    print(f"🔍 Analyze with preferences called for file: {request.file_id}")
    print(f"📚 Selected genres: {request.selected_genres}")
    
    if not detector:
        error_msg = "Book detector not initialized. "
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
            error_msg += "Please set your OpenAI API key in the .env file."
        else:
            error_msg += "YOLO model failed to load. Check server logs for details."
        raise HTTPException(status_code=500, detail=error_msg)
    
    try:
        # Find the uploaded file
        upload_dir = Path("static/uploads")
        files = list(upload_dir.glob(f"{request.file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        
        # Analyze the image using the book detector
        print(f"🔍 Analyzing image: {file_path}")
        all_books = detector.process_image(str(file_path))
        
        if not all_books:
            return {
                "file_id": request.file_id,
                "all_books": [],
                "filtered_books": [],
                "total_detected": 0,
                "total_matching_preferences": 0,
                "selected_genres": request.selected_genres,
                "genre_matches": {},
                "message": "No books detected in the image"
            }
        
        # Filter books based on user preferences
        filtered_books = []
        genre_matches = {}
        
        for book in all_books:
            # Get book genres (primary, secondary, tertiary)
            primary_genre = book.get('primary_genre', '').strip()
            secondary_genre = book.get('secondary_genre', '').strip()
            tertiary_genre = book.get('tertiary_genre', '').strip()
            
            # Check if any of the book's genres match user preferences
            book_genres = [g for g in [primary_genre, secondary_genre, tertiary_genre] if g]
            matching_genres = []
            
            for user_genre in request.selected_genres:
                for book_genre in book_genres:
                    # Case-insensitive matching with some flexibility
                    if (user_genre.lower() in book_genre.lower() or 
                        book_genre.lower() in user_genre.lower() or
                        user_genre.lower() == book_genre.lower()):
                        matching_genres.append(user_genre)
                        break
            
            # If book matches any user preference, include it
            if matching_genres:
                # Add matching info to the book
                book['matching_genres'] = list(set(matching_genres))
                book['match_score'] = len(matching_genres) / len(request.selected_genres)
                filtered_books.append(book)
                
                # Update genre match statistics
                for genre in matching_genres:
                    genre_matches[genre] = genre_matches.get(genre, 0) + 1
        
        # Sort filtered books by match score (highest first)
        filtered_books.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Get genre statistics for all books
        all_genre_stats = {}
        if detector and all_books:
            try:
                all_genre_stats = detector.get_genre_statistics(all_books)
            except Exception as e:
                print(f"Error getting genre statistics: {e}")
                all_genre_stats = {}
        
        # Get genre statistics for filtered books
        filtered_genre_stats = {}
        if detector and filtered_books:
            try:
                filtered_genre_stats = detector.get_genre_statistics(filtered_books)
            except Exception as e:
                print(f"Error getting filtered genre statistics: {e}")
                filtered_genre_stats = {}
        
        # Save results to JSON file
        results_data = {
            "file_id": request.file_id,
            "all_books": all_books,
            "filtered_books": filtered_books,
            "selected_genres": request.selected_genres,
            "genre_matches": genre_matches,
            "analysis_timestamp": str(Path().cwd())
        }
        
        results_path = Path("static/results") / f"{request.file_id}_preferences_analysis.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        # Fetch metadata for filtered books (covers, ratings, etc.)
        enhanced_books = []
        if filtered_books:
            try:
                print("📚 Fetching book metadata (covers, ratings)...")
                from ..services.book_metadata import metadata_service
                
                # Prepare books for metadata fetching
                books_for_metadata = []
                for book in filtered_books:
                    books_for_metadata.append({
                        'title': book.get('title', ''),
                        'author': book.get('author', '')
                    })
                
                # Fetch metadata
                enhanced_books = metadata_service.get_multiple_books_metadata(books_for_metadata)
                print(f"✅ Enhanced {len(enhanced_books)} books with metadata")
                
            except Exception as e:
                print(f"⚠️ Failed to fetch metadata: {e}")
                enhanced_books = filtered_books  # Fallback to original data
        else:
            enhanced_books = filtered_books
        
        print(f"✅ Analysis complete: {len(all_books)} total books, {len(filtered_books)} matching preferences")
        
        return {
            "file_id": request.file_id,
            "all_books": all_books,
            "filtered_books": enhanced_books,  # Return enhanced books with metadata
            "total_detected": len(all_books),
            "total_matching_preferences": len(filtered_books),
            "selected_genres": request.selected_genres,
            "genre_matches": genre_matches,
            "all_genre_statistics": all_genre_stats,
            "filtered_genre_statistics": filtered_genre_stats,
            "results_path": str(results_path),
            "message": f"Analysis complete: {len(all_books)} books detected, {len(filtered_books)} match your preferences"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in analyze_books_with_preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis with preferences failed: {str(e)}")

