#!/usr/bin/env python3
"""
Book Metadata API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from ..services.book_metadata import metadata_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

class BookMetadataRequest(BaseModel):
    title: str
    author: Optional[str] = None

class MultipleBooksMetadataRequest(BaseModel):
    books: List[Dict[str, Any]]

@router.post("/book")
async def get_book_metadata(request: BookMetadataRequest) -> Dict[str, Any]:
    """
    Get metadata for a single book
    
    Args:
        request: BookMetadataRequest with title and optional author
        
    Returns:
        Dict containing book metadata including cover URL, rating, etc.
    """
    try:
        logger.info(f"📚 Fetching metadata for: {request.title} by {request.author or 'Unknown'}")
        
        metadata = metadata_service.get_book_metadata(
            title=request.title,
            author=request.author
        )
        
        return {
            "success": True,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching metadata for {request.title}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")

@router.post("/books")
async def get_multiple_books_metadata(request: MultipleBooksMetadataRequest) -> Dict[str, Any]:
    """
    Get metadata for multiple books
    
    Args:
        request: MultipleBooksMetadataRequest with list of books
        
    Returns:
        Dict containing enhanced book data with metadata
    """
    try:
        logger.info(f"📚 Fetching metadata for {len(request.books)} books")
        
        enhanced_books = metadata_service.get_multiple_books_metadata(request.books)
        
        return {
            "success": True,
            "books": enhanced_books,
            "count": len(enhanced_books)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching metadata for multiple books: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for metadata service"""
    return {"status": "healthy", "service": "book_metadata"}
