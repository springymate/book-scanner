import cv2
import numpy as np
from PIL import Image
import base64
import io
from typing import Tuple, Optional
import os

def validate_image_file(file_path: str) -> bool:
    """
    Validate if the file is a valid image
    
    Args:
        file_path: Path to the image file
        
    Returns:
        bool: True if valid image, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return False
        
        # Try to open with OpenCV
        image = cv2.imread(file_path)
        if image is None:
            return False
        
        # Check image dimensions
        height, width = image.shape[:2]
        if height < 10 or width < 10:
            return False
        
        return True
        
    except Exception:
        return False

def resize_image(image: np.ndarray, max_size: int = 2048) -> np.ndarray:
    """
    Resize image while maintaining aspect ratio
    
    Args:
        image: Input image
        max_size: Maximum dimension size
        
    Returns:
        Resized image
    """
    height, width = image.shape[:2]
    
    if max(height, width) <= max_size:
        return image
    
    # Calculate scale factor
    scale = max_size / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Resize image
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    return resized

def enhance_image(image: np.ndarray) -> np.ndarray:
    """
    Enhance image quality for better analysis
    
    Args:
        image: Input image
        
    Returns:
        Enhanced image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # Apply slight sharpening
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    
    return sharpened

def image_to_base64(image: np.ndarray, format: str = 'JPEG', quality: int = 95) -> str:
    """
    Convert OpenCV image to base64 string
    
    Args:
        image: OpenCV image (BGR format)
        format: Image format (JPEG, PNG)
        quality: Image quality (1-100)
        
    Returns:
        Base64 encoded image string
    """
    # Convert BGR to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_image = Image.fromarray(rgb_image)
    
    # Convert to base64
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format, quality=quality)
    img_bytes = buffer.getvalue()
    
    return base64.b64encode(img_bytes).decode('utf-8')

def base64_to_image(base64_string: str) -> np.ndarray:
    """
    Convert base64 string to OpenCV image
    
    Args:
        base64_string: Base64 encoded image
        
    Returns:
        OpenCV image (BGR format)
    """
    # Decode base64
    img_bytes = base64.b64decode(base64_string)
    
    # Convert to PIL Image
    pil_image = Image.open(io.BytesIO(img_bytes))
    
    # Convert to OpenCV format
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    return opencv_image

def create_thumbnail(image: np.ndarray, size: Tuple[int, int] = (300, 400)) -> np.ndarray:
    """
    Create a thumbnail of the image
    
    Args:
        image: Input image
        size: Thumbnail size (width, height)
        
    Returns:
        Thumbnail image
    """
    height, width = image.shape[:2]
    target_width, target_height = size
    
    # Calculate scale factor
    scale = min(target_width / width, target_height / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Resize image
    thumbnail = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Create canvas with target size
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    
    # Center the thumbnail on the canvas
    y_offset = (target_height - new_height) // 2
    x_offset = (target_width - new_width) // 2
    
    canvas[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = thumbnail
    
    return canvas

def detect_image_orientation(image: np.ndarray) -> str:
    """
    Detect if image is landscape or portrait
    
    Args:
        image: Input image
        
    Returns:
        'landscape' or 'portrait'
    """
    height, width = image.shape[:2]
    return 'landscape' if width > height else 'portrait'

def get_image_metadata(image: np.ndarray) -> dict:
    """
    Get basic metadata about the image
    
    Args:
        image: Input image
        
    Returns:
        Dictionary with image metadata
    """
    height, width = image.shape[:2]
    
    return {
        'width': width,
        'height': height,
        'channels': image.shape[2] if len(image.shape) > 2 else 1,
        'orientation': detect_image_orientation(image),
        'aspect_ratio': width / height,
        'total_pixels': width * height
    }

def crop_image_region(image: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
    """
    Crop a region from the image
    
    Args:
        image: Input image
        x: X coordinate of top-left corner
        y: Y coordinate of top-left corner
        width: Width of the crop
        height: Height of the crop
        
    Returns:
        Cropped image region
    """
    # Ensure coordinates are within image bounds
    x = max(0, min(x, image.shape[1] - 1))
    y = max(0, min(y, image.shape[0] - 1))
    width = min(width, image.shape[1] - x)
    height = min(height, image.shape[0] - y)
    
    return image[y:y + height, x:x + width]

def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """
    Rotate image by specified angle
    
    Args:
        image: Input image
        angle: Rotation angle in degrees
        
    Returns:
        Rotated image
    """
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    
    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new image size
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_width = int(height * sin + width * cos)
    new_height = int(height * cos + width * sin)
    
    # Adjust rotation matrix
    rotation_matrix[0, 2] += new_width / 2 - center[0]
    rotation_matrix[1, 2] += new_height / 2 - center[1]
    
    # Rotate image
    rotated = cv2.warpAffine(image, rotation_matrix, (new_width, new_height))
    
    return rotated

