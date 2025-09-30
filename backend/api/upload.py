from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path
import shutil
import uuid
from typing import Dict, Union
import os

router = APIRouter()

# Allowed image file types
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/image")
async def upload_image(file: UploadFile = File(...)) -> Dict[str, Union[str, int]]:
    """
    Upload and validate image file for book spine analysis
    
    Args:
        file: Uploaded image file
        
    Returns:
        Dict containing file information and status
    """
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_extension}"
        
        # Save file
        file_path = Path("static/uploads") / filename
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        return {
            "file_id": file_id,
            "filename": filename,
            "file_path": str(file_path),
            "file_size": len(file_content),
            "status": "uploaded",
            "message": "Image uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/image/{file_id}")
async def delete_image(file_id: str) -> Dict[str, str]:
    """
    Delete uploaded image file
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing deletion status
    """
    try:
        # Find the file
        upload_dir = Path("static/uploads")
        files = list(upload_dir.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete the file
        file_path = files[0]
        file_path.unlink()
        
        return {
            "file_id": file_id,
            "status": "deleted",
            "message": "Image deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@router.get("/image/{file_id}/info")
async def get_image_info(file_id: str) -> Dict[str, Union[str, int]]:
    """
    Get information about uploaded image
    
    Args:
        file_id: Unique file identifier
        
    Returns:
        Dict containing file information
    """
    try:
        # Find the file
        upload_dir = Path("static/uploads")
        files = list(upload_dir.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        file_size = file_path.stat().st_size
        
        return {
            "file_id": file_id,
            "filename": file_path.name,
            "file_size": file_size,
            "file_extension": file_path.suffix,
            "status": "available"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")

