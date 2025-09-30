// BookSpine Detector - Simplified Version (No Recommendations)
class BookSpineDetector {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.currentStep = 1;
        this.uploadedFile = null;
        this.analysisResults = null;
    }

    initializeElements() {
        // Upload elements
        this.uploadZone = document.getElementById('uploadZone');
        this.fileInput = document.getElementById('fileInput');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.imagePreview = document.getElementById('imagePreview');
        this.previewImage = document.getElementById('previewImage');
        this.removeImage = document.getElementById('removeImage');
        this.analyzeBtn = document.getElementById('analyzeBtn');

        // Step elements
        this.step1 = document.getElementById('step1');
        this.step2 = document.getElementById('step2');
        this.loading = document.getElementById('loading');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorMessage = document.getElementById('errorMessage');
        this.errorText = document.getElementById('errorText');

        // Results elements
        this.summaryStats = document.getElementById('summaryStats');
        this.detectedBooks = document.getElementById('detectedBooks');
        this.annotatedImage = document.getElementById('annotatedImage');

        // Action buttons
        this.backBtn = document.getElementById('backBtn');
        this.downloadBtn = document.getElementById('downloadBtn');
    }

    setupEventListeners() {
        // Upload events
        this.uploadZone.addEventListener('click', () => this.fileInput.click());
        this.uploadBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.removeImage.addEventListener('click', () => this.removeUploadedImage());

        // Drag and drop events
        this.uploadZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadZone.addEventListener('drop', (e) => this.handleDrop(e));

        // Analysis events
        this.analyzeBtn.addEventListener('click', () => this.analyzeImage());
        this.backBtn.addEventListener('click', () => this.goBackToUpload());
        this.downloadBtn.addEventListener('click', () => this.downloadResults());
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadZone.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }

    processFile(file) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showError('Please select a valid image file.');
            return;
        }

        // Validate file size (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            this.showError('File size must be less than 10MB.');
            return;
        }

        this.uploadedFile = file;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            this.previewImage.src = e.target.result;
            this.imagePreview.style.display = 'block';
            this.uploadZone.style.display = 'none';
            this.analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    removeUploadedImage() {
        this.uploadedFile = null;
        this.imagePreview.style.display = 'none';
        this.uploadZone.style.display = 'block';
        this.analyzeBtn.disabled = true;
        this.fileInput.value = '';
    }

    async analyzeImage() {
        if (!this.uploadedFile) {
            this.showError('Please upload an image first.');
            return;
        }

        this.showStep(2);
        this.showLoading(true);
        this.hideError();

        try {
            const formData = new FormData();
            formData.append('file', this.uploadedFile);

            const response = await fetch('/api/analyze/books', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed');
            }

            const results = await response.json();
            this.analysisResults = results;
            this.displayResults(results);

        } catch (error) {
            console.error('Analysis error:', error);
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(results) {
        this.hideError();
        this.resultsSection.style.display = 'block';
        this.downloadBtn.style.display = 'inline-block';

        // Display summary stats
        const totalBooks = results.detected_books.length;
        const validBooks = results.detected_books.filter(book => book.isValid).length;
        
        this.summaryStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-number">${totalBooks}</div>
                <div class="stat-label">Books Detected</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${validBooks}</div>
                <div class="stat-label">Successfully Analyzed</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${Math.round((validBooks / totalBooks) * 100)}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        `;

        // Display detected books
        this.detectedBooks.innerHTML = results.detected_books.map((book, index) => `
            <div class="book-card ${book.isValid ? 'valid' : 'invalid'}">
                <div class="book-number">${index + 1}</div>
                <div class="book-info">
                    <h4>${book.title || 'Unknown Title'}</h4>
                    <p class="book-author">${book.author || 'Unknown Author'}</p>
                    ${book.genre ? `<span class="book-genre">${book.genre}</span>` : ''}
                    ${book.isValid ? 
                        '<div class="book-status valid"><i class="fas fa-check"></i> Analyzed</div>' : 
                        '<div class="book-status invalid"><i class="fas fa-times"></i> Analysis Failed</div>'
                    }
                </div>
                <div class="book-confidence">
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${(book.confidence || 0) * 100}%"></div>
                    </div>
                    <span class="confidence-text">${Math.round((book.confidence || 0) * 100)}%</span>
                </div>
            </div>
        `).join('');

        // Display annotated image if available
        if (results.annotated_image_url) {
            this.annotatedImage.innerHTML = `
                <h3>Annotated Image</h3>
                <img src="${results.annotated_image_url}" alt="Annotated image with detected book spines" class="annotated-img">
            `;
        }
    }

    showStep(step) {
        this.currentStep = step;
        
        // Hide all steps
        this.step1.classList.remove('active');
        this.step2.classList.remove('active');
        
        // Show current step
        if (step === 1) {
            this.step1.classList.add('active');
        } else if (step === 2) {
            this.step2.classList.add('active');
        }
    }

    showLoading(show) {
        this.loading.style.display = show ? 'block' : 'none';
        this.resultsSection.style.display = show ? 'none' : 'block';
    }

    showError(message) {
        this.errorText.textContent = message;
        this.errorMessage.style.display = 'block';
        this.resultsSection.style.display = 'none';
    }

    hideError() {
        this.errorMessage.style.display = 'none';
    }

    goBackToUpload() {
        this.showStep(1);
        this.resultsSection.style.display = 'none';
        this.downloadBtn.style.display = 'none';
        this.hideError();
    }

    downloadResults() {
        if (!this.analysisResults) return;

        const data = {
            timestamp: new Date().toISOString(),
            total_books: this.analysisResults.detected_books.length,
            valid_books: this.analysisResults.detected_books.filter(book => book.isValid).length,
            books: this.analysisResults.detected_books.map(book => ({
                title: book.title,
                author: book.author,
                genre: book.genre,
                confidence: book.confidence,
                isValid: book.isValid
            }))
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `book_analysis_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BookSpineDetector();
});
