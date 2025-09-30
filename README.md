# 📚 BookSpine Recommender

An AI-powered web application that analyzes book spines from photos and provides personalized book recommendations with purchase links.

## ✨ Features

- **Smart Book Detection**: Uses YOLO computer vision to detect and analyze book spines in photos
- **AI-Powered Analysis**: Leverages OpenAI Vision API to extract book titles and authors
- **Personalized Recommendations**: Content-based filtering with genre preferences
- **Purchase Integration**: Direct links to Amazon and Bookshop.org
- **Responsive Design**: Beautiful, mobile-friendly interface
- **Real-time Processing**: Fast image analysis and recommendation generation

## 🏗️ Architecture

### Backend (FastAPI)
- **Book Detection**: YOLO model for spine detection and cropping
- **AI Analysis**: OpenAI Vision API for text extraction
- **Recommendation Engine**: Content-based filtering with genre matching
- **API Integration**: Goodreads API for book metadata
- **Image Processing**: OpenCV for image enhancement and manipulation

### Frontend (Vanilla JS)
- **Upload Interface**: Drag-and-drop image upload
- **Genre Selection**: Interactive genre preference selection
- **Results Display**: Beautiful book cards with purchase links
- **Responsive Design**: Mobile-first, modern UI

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- YOLO model weights (trained for book detection)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd book_recommender_v1
   ```

2. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

4. **Add your YOLO model**
   ```bash
   # Place your trained model at:
   models/yolo_weights/best.pt
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Open your browser**
   - Frontend: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (will use mock data if not provided)
GOODREADS_API_KEY=your_goodreads_api_key_here
AMAZON_AFFILIATE_ID=your_amazon_affiliate_id_here
BOOKSHOP_AFFILIATE_ID=your_bookshop_affiliate_id_here

# Application settings
DEBUG=True
MAX_FILE_SIZE=10485760  # 10MB
CONFIDENCE_THRESHOLD=0.5
MAX_RECOMMENDATIONS=20
```

### Model Configuration

Place your trained YOLO model at `models/yolo_weights/best.pt`. The model should be trained to detect book spines with oriented bounding boxes.

## 📁 Project Structure

```
book_recommender_v1/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── api/                    # API endpoints
│   │   ├── upload.py          # Image upload
│   │   ├── analyze.py         # Book analysis
│   │   └── recommend.py       # Recommendations
│   ├── models/                 # Core models
│   │   ├── book_detector.py   # Book detection logic
│   │   ├── goodreads.py       # Goodreads API integration
│   │   └── recommendation.py  # Recommendation engine
│   ├── utils/                  # Utility functions
│   │   ├── image_processing.py
│   │   └── validation.py
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── styles.css             # Styling
│   └── script.js              # JavaScript functionality
├── models/                     # YOLO model weights
│   └── yolo_weights/
│       └── best.pt
├── static/                     # Static files
│   ├── uploads/               # Uploaded images
│   ├── crops/                 # Cropped book spines
│   └── results/               # Analysis results
├── run.py                     # Development runner
├── env.example               # Environment template
└── README.md                 # This file
```

## 🔌 API Endpoints

### Upload
- `POST /api/upload/image` - Upload image file
- `DELETE /api/upload/image/{file_id}` - Delete uploaded image
- `GET /api/upload/image/{file_id}/info` - Get image info

### Analysis
- `POST /api/analyze/books` - Analyze image for books
- `GET /api/analyze/books/{file_id}` - Get analysis results
- `POST /api/analyze/annotations` - Get annotation data

### Recommendations
- `POST /api/recommend/books` - Get book recommendations
- `POST /api/recommend/genres` - Get genre suggestions
- `GET /api/recommend/popular` - Get popular books
- `POST /api/recommend/similar` - Get similar books

## 🎯 Usage

1. **Upload Image**: Drag and drop or select a photo of book spines
2. **Select Genres**: Choose your preferred book genres
3. **Get Recommendations**: Receive personalized book suggestions with purchase links

## 🛠️ Development

### Running in Development Mode

```bash
python run.py
```

The server will start with auto-reload enabled for both backend and frontend changes.

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Testing

```bash
# Run tests (when implemented)
pytest backend/tests/
```

## 🚀 Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

### Using Heroku

1. Create a `Procfile`:
   ```
   web: python run.py
   ```

2. Deploy to Heroku:
   ```bash
   git push heroku main
   ```

### Environment Variables for Production

Set the following environment variables in your production environment:

- `OPENAI_API_KEY`
- `GOODREADS_API_KEY` (optional)
- `AMAZON_AFFILIATE_ID` (optional)
- `BOOKSHOP_AFFILIATE_ID` (optional)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the Vision API
- Ultralytics for YOLO implementation
- Goodreads for book metadata
- FastAPI for the web framework

## 📞 Support

If you encounter any issues or have questions:

1. Check the [API documentation](http://localhost:8000/api/docs)
2. Review the logs for error messages
3. Ensure all environment variables are set correctly
4. Verify your YOLO model is properly trained and placed

## 🔮 Future Enhancements

- [ ] User accounts and reading lists
- [ ] Advanced filtering options
- [ ] Social sharing features
- [ ] Mobile app development
- [ ] Integration with more book retailers
- [ ] Machine learning model improvements
- [ ] Multi-language support

---

Built with ❤️ using FastAPI, OpenAI Vision, and modern web technologies.

