#!/usr/bin/env python3
"""
Book Spine Detection using OpenAI Vision and YOLO
This script detects book spines, analyzes them using OpenAI Vision API, and returns book data without saving cropped images.
"""

import numpy as np
from ultralytics import YOLO
import cv2
import openai
from PIL import Image
import base64
import io
from typing import List, Tuple, Dict, Optional
import os
import re

from pathlib import Path

from dotenv import load_dotenv
# Load environment variables from .env file in project root
current_dir = Path(__file__).parent.parent.parent  # Go up to project root
env_path = current_dir / ".env"
load_dotenv(env_path)

# Import the book categorizer
try:
    from services.book_categorizer import BookCategorizer
except ImportError:
    from backend.services.book_categorizer import BookCategorizer


class BookSpineDetector:
    def __init__(self, model_path: str, openai_api_key: str):
        """
        Initialize the BookSpineDetector with YOLO model and OpenAI Vision.
        
        Args:
            model_path (str): Path to YOLO model weights
            openai_api_key (str): OpenAI API key
        """
        # Fix for PyTorch 2.6+ weights_only issue
        import torch
        import os
        
        # Set environment variable to allow loading with weights_only=False
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        
        # Load YOLO model with proper error handling
        try:
            # Set environment variables for better compatibility
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            os.environ['TORCH_USE_CUDA_DSA'] = '1'
            
            # Simple approach: just load the model directly
            self.model = YOLO(model_path)
            print("✅ YOLO model loaded successfully")
            
        except Exception as e:
            print(f"⚠️  Initial YOLO load failed: {e}")
            try:
                # Fallback: Try with monkey-patched torch.load
                import torch
                original_load = torch.load
                
                def patched_load(*args, **kwargs):
                    # Remove weights_only parameter if present
                    kwargs.pop('weights_only', None)
                    return original_load(*args, **kwargs)
                
                # Apply the patch
                torch.load = patched_load
                
                try:
                    self.model = YOLO(model_path)
                    print("✅ YOLO model loaded with patched torch.load")
                finally:
                    # Restore original torch.load
                    torch.load = original_load
                    
            except Exception as e2:
                print(f"❌ Failed to load YOLO model: {e2}")
                # Last resort: try with a different model loading approach
                try:
                    # Try loading with explicit weights_only=False
                    import torch
                    original_load = torch.load
                    
                    def safe_load(*args, **kwargs):
                        # Force weights_only=False
                        kwargs['weights_only'] = False
                        return original_load(*args, **kwargs)
                    
                    torch.load = safe_load
                    
                    try:
                        self.model = YOLO(model_path)
                        print("✅ YOLO model loaded with weights_only=False")
                    finally:
                        torch.load = original_load
                        
                except Exception as e3:
                    print(f"❌ All YOLO loading methods failed: {e3}")
                    # Don't raise the exception, just set model to None
                    self.model = None
                    print("⚠️  Continuing without YOLO model - some features will be disabled")
        
        if self.model is not None:
            # Check for CUDA availability more safely
            try:
                import torch
                if torch.cuda.is_available():
                    self.model.to("cuda")
                    print("✅ Using CUDA for YOLO model")
                else:
                    self.model.to("cpu")
                    print("✅ Using CPU for YOLO model")
            except Exception as e:
                self.model.to("cpu")
                print(f"⚠️  CUDA check failed, using CPU: {e}")
        
        # Initialize OpenAI with proxy support for office environments
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
            print("✅ OpenAI client initialized for book analysis")
                
        except (AttributeError, TypeError) as e:
            if "proxies" in str(e):
                # Fallback for httpx version compatibility issues
                import httpx
                self.openai_client = openai.OpenAI(
                    api_key=openai_api_key,
                    http_client=httpx.Client()
                )
            else:
                # Fallback for older OpenAI versions
                openai.api_key = openai_api_key
                self.openai_client = openai
        
        # Initialize book categorizer
        try:
            self.categorizer = BookCategorizer(openai_api_key)
            print("✅ BookCategorizer initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize BookCategorizer: {e}")
            self.categorizer = None
        
        # System prompt for OpenAI Vision
        self.system_prompt = """You are a visual analysis expert specializing in book spine analysis. You can see the actual book spine image and need to extract book metadata from it.

        Core Analysis Rules (In Priority Order):
        1. Visual Text Analysis:
            - Look for text patterns on the book spine
            - [Small Text] + [Large Text] Pattern:
                * If small text is surname-like → it's likely Author
                * Example: Small "KING" + Large "MISERY" → Author: King, Title: Misery
            - Multiple text sizes indicate different elements
            - Consistent text size/style usually belongs together
        
        2. Author Identification:
            - Usually smaller text than title
            - Often at top or bottom of spine
            - Can be surname only or full name
            - Look for common author name patterns
        
        3. Title Identification:
            - Usually largest/most prominent text
            - Often includes articles (The, A, An)
            - Forms complete phrase
            - May span multiple lines in same style
            - Look for book title patterns
        
        4. Genre Analysis:
            - Analyze visual cues that indicate genre:
                * Color schemes (dark colors often indicate mystery/thriller)
                * Font styles (serif fonts suggest literary fiction)
                * Visual elements (spaceships = sci-fi, swords = fantasy)
                * Series indicators (Harry Potter = fantasy, etc.)
            - Consider title keywords that suggest genre
            - Look for genre-specific visual design elements
            - Use your knowledge of popular books and their genres
            - Provide THREE genres in order of relevance (primary, secondary, tertiary)
        
        5. Visual Layout Analysis:
            - Analyze the overall layout of the spine
            - Consider text positioning and hierarchy
            - Look for series information
            - Identify publisher logos or text
        
        6. Special Cases:
            - Well-known series (Harry Potter, etc):
                * If title is clear → can infer famous author and genres
                * Must note inference in reasoning
            - Series books with numbers
            - Translated works
        
        7. Always Ignore:
            - Marketing text (BESTSELLER, COMING SOON)
            - Publisher names (unless part of title)
            - Price/ISBN
            - Series labels (unless part of title)
            - Decorative elements

        Uncertainty Handling:
        - Include "Need Validation" in the front and state the reason in uncertainty notes if:
            * Cannot correctly determine one of book metadata (either title, author, or genres are unclear)
            * Text is completely illegible or missing
            * No recognizable patterns match any standard book spine layout
            * Image quality is too poor to read
        
        - Always write "None" in uncertainty notes when there are no uncertainties

        Use standard format to output book metadata:
        TITLE:
        AUTHOR:
        GENRE: [Primary Genre, Secondary Genre, Tertiary Genre]
        SPINE_APPEARANCE:
        REASONING:
        UNCERTAINTY_NOTES:"""

        print(f"✅ BookSpineDetector initialized")

    def detect_books(self, image: np.ndarray) -> List[Dict]:
        """
        Detect books in the image and return book data with annotations.
        
        Args:
            image (np.ndarray): Input image
            
        Returns:
            List[Dict]: List of book data dictionaries with annotations
        """
        print("🔍 Detecting books in image...")
        
        if self.model is None:
            print("❌ YOLO model not available - cannot detect books")
            return []
        
        results = self.model.predict(source=image, conf=0.50, save=False, show=False)[0]
        detected_books = []
        
        # Debug information
        print(f"🔍 YOLO results type: {type(results)}")
        print(f"🔍 Has obb attribute: {hasattr(results, 'obb') if results else 'No results'}")
        if results and hasattr(results, 'obb'):
            print(f"🔍 OBB type: {type(results.obb)}")
            print(f"🔍 OBB value: {results.obb}")
        
        # Check if we have OBB (oriented bounding boxes) or regular boxes
        if not results:
            print("❌ No results from YOLO model")
            return []
        
        # Try OBB first, then fall back to regular boxes
        if hasattr(results, 'obb') and results.obb is not None and len(results.obb) > 0:
            print(f"�� Found {len(results.obb)} potential books (OBB)")
            boxes = results.obb
        elif hasattr(results, 'boxes') and results.boxes is not None and len(results.boxes) > 0:
            print(f"📚 Found {len(results.boxes)} potential books (regular boxes)")
            boxes = results.boxes
        else:
            print("❌ No books detected in the image")
            print("�� Try lowering the confidence threshold or check if your model is trained for book detection")
            return []
        
        for i, box in enumerate(boxes):
            try:
                # Handle both OBB and regular boxes
                if hasattr(box, 'xyxyxyxy'):
                    # OBB (oriented bounding box) - 8 points
                    points = box.xyxyxyxy.cpu().numpy().reshape(-1, 2)
                else:
                    # Regular bounding box - convert to 4 corners
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                    points = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
               
                # Calculate angle and get rotation matrix
                edge1 = points[1] - points[0]
                angle = np.arctan2(edge1[1], edge1[0]) * 180 / np.pi
                
                # Get the center point
                center = np.mean(points, axis=0)
                
                # Get width and height of the rotated rectangle
                width = np.linalg.norm(points[1] - points[0])
                height = np.linalg.norm(points[2] - points[1])
                
                # Skip if width or height is too small
                if width < 10 or height < 10:
                    print(f"⚠️  Skipping book {i+1}: too small ({width:.1f}x{height:.1f})")
                    continue
                
                # Get rotation matrix
                rotation_matrix = cv2.getRotationMatrix2D(tuple(center), angle, 1.0)
                
                # Calculate new image size after rotation
                cos = np.abs(rotation_matrix[0, 0])
                sin = np.abs(rotation_matrix[0, 1])
                new_width = int(height * sin + width * cos)
                new_height = int(height * cos + width * sin)
                
                # Adjust rotation matrix
                rotation_matrix[0, 2] += new_width/2 - center[0]
                rotation_matrix[1, 2] += new_height/2 - center[1]
                
                # Rotate the whole image
                rotated_image = cv2.warpAffine(image, rotation_matrix, (new_width, new_height))
                
                # Calculate the bounding box in the rotated image
                rotated_points = cv2.transform(points.reshape(-1, 1, 2), rotation_matrix).reshape(-1, 2)
                x_min, y_min = np.min(rotated_points, axis=0)
                x_max, y_max = np.max(rotated_points, axis=0)
                
                # Ensure valid crop coordinates
                x_min, y_min = max(0, int(x_min)), max(0, int(y_min))
                x_max, y_max = min(rotated_image.shape[1], int(x_max)), min(rotated_image.shape[0], int(y_max))
                
                # Skip if crop dimensions are invalid
                if x_max <= x_min or y_max <= y_min:
                    print(f"⚠️  Skipping book {i+1}: invalid crop dimensions")
                    continue
                
                # Crop the rotated image for analysis
                cropped_image = rotated_image[y_min:y_max, x_min:x_max]
                
                # Analyze the cropped image
                book_info = self.analyze_image_with_vision(cropped_image, i + 1)
                
                # Add annotation data
                book_info.update({
                    'book_number': i + 1,
                    'bbox_coordinates': points.tolist(),
                    'center': center.tolist(),
                    'width': float(width),
                    'height': float(height),
                    'angle': float(angle),
                    'crop_coordinates': {
                        'x_min': int(x_min),
                        'y_min': int(y_min),
                        'x_max': int(x_max),
                        'y_max': int(y_max)
                    },
                    'confidence': 'high' if book_info['isValid'] else 'low'
                })
                
                detected_books.append(book_info)
                
                print(f"✅ Processed book {i+1}: {cropped_image.shape[1]}x{cropped_image.shape[0]} pixels")
                print(f"   Title: {book_info['title']}")
                print(f"   Author: {book_info['author']}")
                print(f"   Primary Genre: {book_info.get('primary_genre', 'Unknown')}")
                print(f"   Secondary Genre: {book_info.get('secondary_genre', 'Unknown')}")
                print(f"   Tertiary Genre: {book_info.get('tertiary_genre', 'Unknown')}")
                print(f"   Valid: {book_info['isValid']}")
                
            except Exception as e:
                print(f"❌ Error processing book {i+1}: {e}")
                continue
        
        if not detected_books:
            print("❌ No valid books could be processed")
            return []
        
        # Sort books by leftmost x coordinate
        detected_books.sort(key=lambda x: min(x['bbox_coordinates'][::2]))
        print(f"✅ Successfully processed {len(detected_books)} books")
        
        # Categorize books with genres
        if self.categorizer and detected_books:
            print("🏷️  Categorizing books with genres...")
            try:
                detected_books = self.categorizer.categorize_books(detected_books)
                print(f"✅ Successfully categorized {len(detected_books)} books")
            except Exception as e:
                print(f"❌ Error categorizing books: {e}")
                # Note: Books already have genres from OpenAI Vision API analysis
                # No need to add default genres as they're already extracted
        
        return detected_books

    def _process_cropped_image(self, image: np.ndarray) -> np.ndarray:
        """
        Process cropped image: resize to 1024px max dimension for better vision analysis
        
        Args:
            image (np.ndarray): Input cropped image
            
        Returns:
            np.ndarray: Processed image
        """
        height, width = image.shape[:2]
        target_size = 1024  # Larger size for better vision analysis
        scale = target_size / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize to target size
        final_image = cv2.resize(image, (new_width, new_height), 
                               interpolation=cv2.INTER_LANCZOS4)
        
        return final_image

    def image_to_base64(self, image: np.ndarray) -> str:
        """
        Convert OpenCV image to base64 string for OpenAI Vision API
        
        Args:
            image (np.ndarray): OpenCV image (BGR format)
            
        Returns:
            str: Base64 encoded image
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=95)
        img_bytes = buffer.getvalue()
        
        return base64.b64encode(img_bytes).decode('utf-8')

    def analyze_image_with_vision(self, image: np.ndarray, book_number: int) -> Dict[str, str]:
        """
        Analyze book spine image using OpenAI Vision API
        
        Args:
            image (np.ndarray): Input image
            book_number (int): Book number for debugging
            
        Returns:
            Dict[str, str]: Book metadatas
        """
        try:
            # Process image for better analysis
            processed_image = self._process_cropped_image(image)
            
            # Convert to base64
            base64_image = self.image_to_base64(processed_image)
            
            # Create the prompt
            prompt = f"""Analyze this book spine image and extract the book metadata.

            Look carefully at the text, layout, and visual elements on the book spine.
            Identify the title and author based on the visual hierarchy and text patterns.
            
            {self.system_prompt}
            
            Use standard format to output book metadata:
            TITLE:
            AUTHOR:
            GENRE: [Primary Genre, Secondary Genre, Tertiary Genre]
            SPINE_APPEARANCE:
            REASONING:
            UNCERTAINTY_NOTES:"""

            # Call OpenAI Vision API
            try:
                # Use the new API format (OpenAI v1.0+)
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500,
                    temperature=0.1
                )
            except Exception as api_error:
                print(f"❌ OpenAI API error: {api_error}")
                # Return a fallback response
                return {
                    'title': '',
                    'author': '',
                    'genre': '',
                    'primary_genre': '',
                    'secondary_genre': '',
                    'tertiary_genre': '',
                    'isValid': False,
                    'rawText': 'OpenAI API Error',
                    'reasoning': f'OpenAI API call failed: {str(api_error)}'
                }
            
            # Handle API response format
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message'):
                    response_text = response.choices[0].message.content
                else:
                    response_text = response.choices[0].text
            else:
                print(f"❌ Unexpected response format: {response}")
                return {
                    'title': '',
                    'author': '',
                    'genre': '',
                    'primary_genre': '',
                    'secondary_genre': '',
                    'tertiary_genre': '',
                    'isValid': False,
                    'rawText': 'Invalid API Response',
                    'reasoning': 'OpenAI API returned unexpected response format'
                }
            
            # Parse the response
            book_info = self._parse_openai_response(response_text)
            book_info['rawText'] = 'Vision Analysis'  # Indicate this came from vision
            
            return book_info
            
        except Exception as e:
            print(f"❌ OpenAI Vision API error for book {book_number}: {e}")
            return {
                'title': '',
                'author': '',
                'genre': '',
                'primary_genre': '',
                'secondary_genre': '',
                'tertiary_genre': '',
                'isValid': False,
                'rawText': 'Vision Analysis Failed',
                'reasoning': f'OpenAI Vision API error: {str(e)}'
            }

    def _parse_openai_response(self, response_text: str) -> Dict[str, str]:
        """
        Parse OpenAI response to extract book metadata
        
        Args:
            response_text (str): Raw response from OpenAI
            
        Returns:
            Dict[str, str]: Parsed book metadata
        """
        book_info = {
            'title': '',
            'author': '',
            'genre': '',
            'primary_genre': '',
            'secondary_genre': '',
            'tertiary_genre': '',
            'spine_appearance': '',
            'reasoning': '',
            'uncertainty_notes': '',
            'isValid': True
        }
        
        try:
            lines = response_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('TITLE:'):
                    book_info['title'] = line.replace('TITLE:', '').strip()
                elif line.startswith('AUTHOR:'):
                    book_info['author'] = line.replace('AUTHOR:', '').strip()
                elif line.startswith('GENRE:'):
                    # Extract genres from the GENRE line
                    genre_text = line.replace('GENRE:', '').strip()
                    
                    # Parse the genre list format: [Primary Genre, Secondary Genre, Tertiary Genre]
                    if genre_text.startswith('[') and genre_text.endswith(']'):
                        # Remove brackets and split by comma
                        genre_text = genre_text.strip('[]')
                        genres = [g.strip() for g in genre_text.split(',')]
                        
                        # Assign genres
                        book_info['primary_genre'] = genres[0] if len(genres) > 0 else ''
                        book_info['secondary_genre'] = genres[1] if len(genres) > 1 else ''
                        book_info['tertiary_genre'] = genres[2] if len(genres) > 2 else ''
                        
                        # Set the main genre field to the primary genre
                        book_info['genre'] = book_info['primary_genre']
                    else:
                        # Fallback if format is different
                        book_info['primary_genre'] = genre_text
                        book_info['secondary_genre'] = ''
                        book_info['tertiary_genre'] = ''
                        book_info['genre'] = genre_text
                elif line.startswith('SPINE_APPEARANCE:'):
                    book_info['spine_appearance'] = line.replace('SPINE_APPEARANCE:', '').strip()
                elif line.startswith('REASONING:'):
                    book_info['reasoning'] = line.replace('REASONING:', '').strip()
                elif line.startswith('UNCERTAINTY_NOTES:'):
                    book_info['uncertainty_notes'] = line.replace('UNCERTAINTY_NOTES:', '').strip()

        except Exception as e:
            book_info['uncertainty_notes'] = f"Parsing error: {str(e)}"
            book_info['isValid'] = False
        
        # Validate the extraction
        book_info['isValid'] = self._validate_extraction(book_info)
        
        return book_info

    def _validate_extraction(self, result: Dict[str, str]) -> bool:
        """
        Validate the extraction based on reasoning and uncertainty notes
        
        Args:
            result (Dict[str, str]): Extraction results
            
        Returns:
            bool: True if extraction is valid, False otherwise
        """
        # Check if "Need Validation" flag is present
        if "Need Validation" in result['uncertainty_notes']:
            return False
        
        # Additional validation checks
        high_risk_terms = [
            "cannot determine", "unclear", "not visible", "multiple possibilities",
            "completely obscured", "low confidence", "uncertain", "ambiguous"
        ]
        
        # Check uncertainty notes for high risk terms
        if any(term in result['uncertainty_notes'].lower() for term in high_risk_terms):
            return False
        
        # Validate reasoning quality
        if len(result['reasoning']) < 20:
            return False
        
        # Validate required fields
        if not result['title'].strip():
            return False
        
        # Validate genre field
        if not result['genre'].strip():
            return False
        
        # Check for placeholder or generic responses
        placeholder_terms = ["unknown", "n/a", "not available", "unclear"]
        if any(term in result['title'].lower() for term in placeholder_terms):
            return False
        
        return True

    def process_image(self, image_path: str) -> List[Dict]:
        """
        Process a single image and return book information with annotations
        
        Args:
            image_path (str): Path to input image
            
        Returns:
            List[Dict]: List of book information dictionaries with annotations
        """
        print(f"\n🖼️  Processing image: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        print(f"📐 Image dimensions: {image.shape[1]}x{image.shape[0]} pixels")
        
        # Detect and analyze books
        books = self.detect_books(image)
        
        if not books:
            print("❌ No books detected in the image")
            return []
        
        return books

    def get_annotations_data(self, image: np.ndarray) -> Dict:
        """
        Get annotation data for drawing bounding boxes on the original image
        
        Args:
            image (np.ndarray): Original image
            
        Returns:
            Dict: Annotation data including bounding boxes and colors
        """
        books = self.detect_books(image)
        
        if not books:
            return {"boxes": [], "colors": [], "labels": []}
        
        # Define rainbow colors (in BGR format)
        rainbow_colors = [
            (0, 0, 255),    # Red
            (0, 127, 255),  # Orange
            (0, 255, 255),  # Yellow
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (255, 0, 127),  # Indigo
            (255, 0, 255)   # Violet
        ]
        
        boxes = []
        colors = []
        labels = []
        
        for i, book in enumerate(books):
            # Get bounding box coordinates
            bbox_coords = np.array(book['bbox_coordinates'])
            boxes.append(bbox_coords)
            
            # Get color
            color = rainbow_colors[i % len(rainbow_colors)]
            colors.append(color)
            
            # Create label
            label = f"{i+1}. {book['title'][:20]}{'...' if len(book['title']) > 20 else ''}"
            labels.append(label)
        
        return {
            "boxes": boxes,
            "colors": colors,
            "labels": labels,
            "books": books
        }

    def get_genre_statistics(self, books: List[Dict]) -> Dict[str, int]:
        """
        Get genre statistics for a list of books.
        
        Args:
            books (List[Dict]): List of books with genre information
            
        Returns:
            Dict[str, int]: Genre statistics
        """
        if self.categorizer:
            return self.categorizer.get_genre_statistics(books)
        else:
            # Fallback statistics
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
        if self.categorizer:
            return self.categorizer.get_available_genres()
        else:
            # Fallback genre list
            return [
                "Fiction", "Non-Fiction", "Mystery", "Science Fiction", 
                "Fantasy", "Romance", "Thriller", "Biography", "History", 
                "Self-Help", "Business", "Technology", "Art", "Poetry", "Drama"
            ]