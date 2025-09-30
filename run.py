#!/usr/bin/env python3
"""
Development runner for BookSpine Recommender
"""

import uvicorn
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_requirements():
    """Check if all required files and directories exist"""
    required_files = [
        "backend/main.py",
        "backend/book_detector/book_detector.py",
        "frontend/index.html",
        "frontend/styles.css",
        "frontend/script.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    return True

def check_environment():
    """Check environment variables and configuration"""
    # Load environment variables
    load_dotenv(".env")    
    # Check required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please create a .env file with the required variables.")
        print("   You can copy env.example to .env and fill in your API keys.")
        return False
    
    # Check optional environment variables
    optional_vars = ["GOODREADS_API_KEY"]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_optional:
        print("⚠️  Optional environment variables not set:")
        for var in missing_optional:
            print(f"   - {var}")
        print("   (Will use mock data for recommendations)")
    
    return True

def check_model_files():
    """Check if YOLO model files exist"""
    model_path = os.getenv("MODEL_PATH", "models/yolo_weights/best.pt")
    
    if not Path(model_path).exists():
        print(f"⚠️  YOLO model not found at: {model_path}")
        print("   Please ensure your trained model is in the correct location.")
        print("   The app will still run but book detection may not work.")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "static/uploads",
        "static/crops", 
        "static/results",
        "static/assets/images"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created necessary directories")

def main():
    """Main function to run the development server"""
    print("🚀 Starting BookSpine Recommender...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please ensure all required files are present.")
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        print("\n❌ Please configure your environment variables.")
        sys.exit(1)
    
    # Check model files
    check_model_files()
    
    # Create directories
    create_directories()
    
    print("\n✅ All checks passed!")
    print("\n🌐 Starting development server...")
    print("📚 Frontend: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/api/docs")
    print("📖 API Redoc: http://localhost:8000/api/redoc")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Run the FastAPI server
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["backend"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

