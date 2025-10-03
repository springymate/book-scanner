// Book Scanner Frontend JavaScript
class BookScanner {
    constructor() {
        this.selectedGenres = new Set();
        this.currentStep = 1;
        this.uploadedImage = null;
        this.uploadedFileId = null;
        this.detectedBooks = [];
        this.allDetectedBooks = [];
        this.recommendations = [];
        this.analysisResults = null;
        
        this.initializeGenres();
        this.bindEvents();
        this.updateProgressIndicator();
    }

    // Initialize genre data
    initializeGenres() {
        this.genres = [
            'Fiction',
            'Non-Fiction', 
            'Business',
            'Design',
            'Self-Help',
            'Science',
            'Fantasy',
            'Biography',
            'History',
            'Young Adult',
            'Horror',
            'Poetry',
            'Comics',
            'Mystery',
            'Romance',
            'Science Fiction',
            'Thriller',
            'Classics',
            'Philosophy',
            'Psychology'
        ];
        
        this.renderGenres();
    }

    // Render genre selection grid
    renderGenres() {
        const genreGrid = document.getElementById('genreGrid');
        genreGrid.innerHTML = '';

        this.genres.forEach(genre => {
            const genreItem = document.createElement('div');
            genreItem.className = 'genre-item';
            genreItem.textContent = genre;
            genreItem.dataset.genre = genre;
            
            // Check if this genre should be pre-selected (matching the image)
            if (['Mystery', 'Romance', 'Science Fiction', 'Thriller', 'Classics'].includes(genre)) {
                genreItem.classList.add('selected');
                this.selectedGenres.add(genre);
            }
            
            genreItem.addEventListener('click', () => this.toggleGenre(genre));
            genreGrid.appendChild(genreItem);
        });

        this.updateContinueButton();
    }

    // Toggle genre selection
    toggleGenre(genre) {
        const genreItem = document.querySelector(`[data-genre="${genre}"]`);
        
        if (this.selectedGenres.has(genre)) {
            this.selectedGenres.delete(genre);
            genreItem.classList.remove('selected');
        } else {
            this.selectedGenres.add(genre);
            genreItem.classList.add('selected');
        }
        
        this.updateContinueButton();
    }

    // Update continue button state
    updateContinueButton() {
        const continueBtn = document.getElementById('continueBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const isEnabled = this.selectedGenres.size > 0;
        
        continueBtn.disabled = !isEnabled;
        clearAllBtn.disabled = !isEnabled;
        
        if (isEnabled) {
            continueBtn.style.opacity = '1';
            continueBtn.style.cursor = 'pointer';
            clearAllBtn.style.opacity = '1';
            clearAllBtn.style.pointerEvents = 'auto';
        } else {
            continueBtn.style.opacity = '0.6';
            continueBtn.style.cursor = 'not-allowed';
            clearAllBtn.style.opacity = '0.6';
            clearAllBtn.style.pointerEvents = 'none';
        }
    }

    // Clear all selected preferences
    clearAllPreferences() {
        // Clear all selected genres
        this.selectedGenres.clear();
        
        // Remove selected class from all genre items
        const genreItems = document.querySelectorAll('.genre-item');
        genreItems.forEach(item => {
            item.classList.remove('selected');
        });
        
        // Update button states
        this.updateContinueButton();
        
        // Show a brief confirmation
        this.showNotification('All preferences cleared!', 'success');
    }

    // Bind event listeners
    bindEvents() {
        // Navigation buttons
        document.getElementById('continueBtn').addEventListener('click', () => this.nextStep());
        document.getElementById('backToPreferencesBtn').addEventListener('click', () => this.previousStep());
        document.getElementById('getRecommendationsBtn').addEventListener('click', () => this.getRecommendations());
        
        // Clear all preferences button
        document.getElementById('clearAllBtn').addEventListener('click', () => this.clearAllPreferences());

        // File upload
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadZone = document.getElementById('uploadZone');
        const changeImageBtn = document.getElementById('changeImageBtn');
        const analyzeBtn = document.getElementById('analyzeBtn');

        uploadBtn.addEventListener('click', () => fileInput.click());
        changeImageBtn.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop
        uploadZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        uploadZone.addEventListener('drop', (e) => this.handleDrop(e));
        
        analyzeBtn.addEventListener('click', () => this.analyzeBooks());
    }

    // Handle file selection
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }

    // Handle drag over
    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('dragover');
    }

    // Handle drag leave
    handleDragLeave(event) {
        event.currentTarget.classList.remove('dragover');
    }

    // Handle drop
    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    // Process uploaded file
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

        this.uploadedImage = file;
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewImg = document.getElementById('previewImg');
            previewImg.src = e.target.result;
            
            document.getElementById('uploadZone').style.display = 'none';
            document.getElementById('imagePreview').style.display = 'block';
            
            // Enable analyze button
            document.getElementById('analyzeBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // Analyze books using the real API
    async analyzeBooks() {
        const analyzeBtn = document.getElementById('analyzeBtn');
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span class="btn-text">Analyzing...</span>';

        try {
            // First upload the image
            const formData = new FormData();
            formData.append('file', this.uploadedImage);

            const uploadResponse = await fetch('/api/upload/image', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed: ${uploadResponse.statusText}`);
            }

            const uploadResult = await uploadResponse.json();
            this.uploadedFileId = uploadResult.file_id;

            // Now analyze with user preferences
            const analysisResponse = await fetch('/api/analyze/books/analyze-with-preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: this.uploadedFileId,
                    selected_genres: Array.from(this.selectedGenres)
                })
            });

            if (!analysisResponse.ok) {
                throw new Error(`Analysis failed: ${analysisResponse.statusText}`);
            }

            const analysisResult = await analysisResponse.json();
            
            // Store the analysis results
            this.allDetectedBooks = analysisResult.all_books || [];
            this.detectedBooks = analysisResult.filtered_books || [];
            this.analysisResults = analysisResult;

            // Render the detected books
            this.renderDetectedBooks();
            
            // Enable recommendations button
            document.getElementById('getRecommendationsBtn').disabled = false;
            
            // Show analysis summary
            this.showAnalysisSummary(analysisResult);
            
        } catch (error) {
            console.error('Analysis error:', error);
            this.showError(`Analysis failed: ${error.message}`);
            
            // Fallback to mock data for demonstration
            this.detectedBooks = this.generateMockDetectedBooks();
            this.renderDetectedBooks();
            document.getElementById('getRecommendationsBtn').disabled = false;
        } finally {
            // Reset analyze button
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i><span class="btn-text">Analyze Books</span>';
        }
    }

    // Generate mock detected books
    generateMockDetectedBooks() {
        const mockBooks = [
            { id: 1, title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', genre: 'Classics' },
            { id: 2, title: '1984', author: 'George Orwell', genre: 'Science Fiction' },
            { id: 3, title: 'To Kill a Mockingbird', author: 'Harper Lee', genre: 'Classics' },
            { id: 4, title: 'Pride and Prejudice', author: 'Jane Austen', genre: 'Romance' },
            { id: 5, title: 'The Catcher in the Rye', author: 'J.D. Salinger', genre: 'Fiction' },
            { id: 6, title: 'Lord of the Flies', author: 'William Golding', genre: 'Fiction' },
            { id: 7, title: 'The Hobbit', author: 'J.R.R. Tolkien', genre: 'Fantasy' },
            { id: 8, title: 'Harry Potter', author: 'J.K. Rowling', genre: 'Fantasy' }
        ];

        return mockBooks.slice(0, Math.floor(Math.random() * 6) + 3); // Random 3-8 books
    }

    // Render detected books
    renderDetectedBooks() {
        const detectedBooksGrid = document.getElementById('detectedBooksGrid');
        const detectedBooksCount = document.getElementById('detectedBooksCount');
        
        detectedBooksCount.textContent = this.detectedBooks.length;
        
        detectedBooksGrid.innerHTML = '';
        
        this.detectedBooks.forEach(book => {
            const bookElement = document.createElement('div');
            bookElement.className = 'detected-book';
            
            // Create a more detailed book card with cover image and rating
            const title = book.title || 'Unknown Title';
            const author = book.author || 'Unknown Author';
            const genre = book.genre || book.primary_genre || 'Unknown Genre';
            const matchingGenres = book.matching_genres ? book.matching_genres.join(', ') : '';
            const coverUrl = book.cover_url || null;
            const rating = book.average_rating || null;
            const ratingsCount = book.ratings_count || 0;
            
            // Create cover image or placeholder - original size
            const coverHtml = coverUrl ? 
                `<img src="${coverUrl}" alt="${title}" style="width: 100%; height: auto; border-radius: 8px 8px 0 0;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                '';
            
            // Create rating display
            const ratingHtml = rating ? 
                `<div style="display: flex; align-items: center; gap: 4px; margin-top: 4px;">
                    <span style="color: #ffd700; font-size: 0.7rem;">★</span>
                    <span style="font-size: 0.6rem; color: #ccc;">${rating}</span>
                    ${ratingsCount > 0 ? `<span style="font-size: 0.5rem; color: #888;">(${ratingsCount})</span>` : ''}
                </div>` : '';
            
            bookElement.innerHTML = `
                <div style="background: #2a2a2a; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); height: 100%;">
                    ${coverHtml}
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 10px 8px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; ${coverUrl ? 'border-radius: 0 0 8px 8px;' : 'border-radius: 8px;'}">
                        <div>
                            <!-- Book Title -->
                            <div style="font-weight: 600; font-size: 0.75rem; color: #ffffff; margin-bottom: 4px; line-height: 1.2; text-align: center;">
                                ${title.length > 18 ? title.substring(0, 18) + '...' : title}
                            </div>
                            
                            <!-- Author -->
                            <div style="font-size: 0.65rem; color: #e0e0e0; margin-bottom: 4px; text-align: center; opacity: 0.9;">
                                by ${author.length > 16 ? author.substring(0, 16) + '...' : author}
                            </div>
                        </div>
                        
                        <div>
                            <!-- Rating -->
                            ${rating ? `
                            <div style="display: flex; align-items: center; justify-content: center; gap: 3px; margin-bottom: 4px;">
                                <div style="display: flex; align-items: center; gap: 2px;">
                                    <span style="color: #ffd700; font-size: 0.65rem;">★</span>
                                    <span style="font-size: 0.65rem; color: #ffffff; font-weight: 500;">${rating}</span>
                                </div>
                                ${ratingsCount > 0 ? `<span style="font-size: 0.55rem; color: #b0b0b0;">(${ratingsCount})</span>` : ''}
                            </div>
                            ` : ''}
                            
                            <!-- Matching Genres -->
                            ${matchingGenres ? `
                            <div style="font-size: 0.55rem; color: #90ee90; text-align: center; opacity: 0.9;">
                                ✓ ${matchingGenres.length > 12 ? matchingGenres.substring(0, 12) + '...' : matchingGenres}
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    ${!coverUrl ? `<div style="background: #333; height: 196px; display: flex; align-items: center; justify-content: center; color: #666; font-size: 0.6rem;">No Cover</div>` : ''}
                </div>
            `;
            
            // Remove click handler - no modal in step 2
            bookElement.style.cursor = 'default';
            bookElement.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                return false;
            });
            detectedBooksGrid.appendChild(bookElement);
        });
        
        document.getElementById('detectedBooksSection').style.display = 'block';
    }

    // Show analysis summary
    showAnalysisSummary(analysisResult) {
        const totalDetected = analysisResult.total_detected || 0;
        const totalMatching = analysisResult.total_matching_preferences || 0;
        const selectedGenres = analysisResult.selected_genres || [];
        
        // Create a summary message
        let summaryMessage = `Analysis Complete! `;
        summaryMessage += `${totalDetected} books detected, ${totalMatching} match your preferences.`;
        
        if (totalMatching === 0 && totalDetected > 0) {
            summaryMessage += ` No books match your selected genres: ${selectedGenres.join(', ')}.`;
        }
        
        // Show the summary as a toast notification
        this.showSuccess(summaryMessage);
    }

    // Get recommendations using OpenAI API
    async getRecommendations() {
        this.nextStep();
        
        // Show loading
        document.getElementById('loadingSection').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        
        try {
            // Call the new recommendation API
            const response = await fetch('/api/recommend/books', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    detected_books: this.detectedBooks,
                    selected_genres: Array.from(this.selectedGenres),
                    max_recommendations: 5
                })
            });

            if (!response.ok) {
                throw new Error(`Recommendation failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Store the recommendations
            this.recommendations = result.recommendations || [];
            this.recommendationSource = result.recommendation_source || 'Unknown';
            this.recommendationStats = {
                total: result.total_recommendations || 0,
                detectedBooks: result.detected_books_count || 0,
                selectedGenres: result.selected_genres || []
            };
            
            // Render the recommendations
            this.renderRecommendations();
            
            // Show success message
            this.showSuccess(`Generated ${this.recommendations.length} personalized recommendations using ${this.recommendationSource}!`);
            
        } catch (error) {
            console.error('Recommendation error:', error);
            this.showError(`Recommendation failed: ${error.message}`);
            
            // Fallback to using filtered books as recommendations
            this.recommendations = this.detectedBooks.map(book => ({
                title: book.title || 'Unknown Title',
                author: book.author || 'Unknown Author',
                genre: book.genre || book.primary_genre || 'Unknown Genre',
                rating: 4.0,
                reason: 'Based on your preferences and collection',
                amazon_url: '#',
                bookshop_url: '#',
                source: 'Fallback Recommendation'
            }));
            
            this.renderRecommendations();
        } finally {
            // Hide loading and show results
            document.getElementById('loadingSection').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';
        }
    }

    // Generate mock recommendations
    generateMockRecommendations() {
        const allBooks = [
            { title: 'The Seven Husbands of Evelyn Hugo', author: 'Taylor Jenkins Reid', genre: 'Romance', match: 95 },
            { title: 'Dune', author: 'Frank Herbert', genre: 'Science Fiction', match: 92 },
            { title: 'The Silent Patient', author: 'Alex Michaelides', genre: 'Thriller', match: 88 },
            { title: 'Murder on the Orient Express', author: 'Agatha Christie', genre: 'Mystery', match: 85 },
            { title: 'Jane Eyre', author: 'Charlotte Brontë', genre: 'Classics', match: 82 },
            { title: 'The Martian', author: 'Andy Weir', genre: 'Science Fiction', match: 80 },
            { title: 'Gone Girl', author: 'Gillian Flynn', genre: 'Thriller', match: 78 },
            { title: 'The Nightingale', author: 'Kristin Hannah', genre: 'Fiction', match: 75 }
        ];

        // Filter books based on selected genres and sort by match percentage
        return allBooks
            .filter(book => this.selectedGenres.has(book.genre))
            .sort((a, b) => b.match - a.match)
            .slice(0, 6);
    }

    // Render detected books in step 3
    renderDetectedBooksInStep3() {
        console.log('🎯 Rendering detected books in step 3...', this.detectedBooks.length);
        const detectedBooksGrid = document.getElementById('detectedBooksGridStep3');
        const detectedBooksCount = document.getElementById('detectedBooksCountStep3');
        
        if (!detectedBooksGrid || !detectedBooksCount) {
            console.error('❌ Missing elements:', { detectedBooksGrid, detectedBooksCount });
            return;
        }
        
        detectedBooksCount.textContent = this.detectedBooks.length;
        
        detectedBooksGrid.innerHTML = '';
        
        this.detectedBooks.forEach(book => {
            const bookElement = document.createElement('div');
            bookElement.className = 'recommendation-card';
            
            // Create a detailed book card similar to recommendation cards
            const title = book.title || 'Unknown Title';
            const author = book.author || 'Unknown Author';
            const matchingGenres = book.matching_genres ? book.matching_genres.join(', ') : '';
            const coverUrl = book.cover_url || null;
            const rating = book.average_rating || null;
            const ratingsCount = book.ratings_count || 0;
            const fullDescription = book.description || book.synopsis || 'No description available.';
            const shortDescription = fullDescription.length > 200 ? fullDescription.substring(0, 200) + '...' : fullDescription;
            const matchReasoning = book.match_reasoning || 'This book aligns with your reading preferences and offers compelling content that matches your interests.';
            
            // Create cover image or placeholder
            const coverHtml = coverUrl ? 
                `<img src="${coverUrl}" alt="${title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                '';
            
            // Create rating stars
            const ratingStars = rating ? '★'.repeat(Math.floor(rating)) + '☆'.repeat(5 - Math.floor(rating)) : '';
            
            bookElement.innerHTML = `
                <div class="recommendation-cover">
                    ${coverHtml}
                    <div class="no-cover" style="display: none; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #666;">
                        <i class="fas fa-book" style="font-size: 2rem; margin-bottom: 8px;"></i>
                        <span>No Cover Available</span>
                    </div>
                    <div class="cover-overlay">
                        ${rating ? `
                        <div class="rating-display">
                            <span class="rating-stars">${ratingStars}</span>
                            <span class="rating-number">${rating}</span>
                        </div>
                        ` : ''}
                        <div class="match-badge">Great match</div>
                    </div>
                </div>
                
                <div class="recommendation-details">
                    <h3 class="recommendation-title">${title}</h3>
                    <p class="recommendation-author">by ${author}</p>
                    
                    <div class="match-reason">
                        <div class="match-reason-label">Why This Matches You:</div>
                        <p class="match-reason-text">${matchReasoning}</p>
                    </div>
                    
                    <p class="recommendation-description">${shortDescription}</p>
                    ${fullDescription.length > 200 ? `<span class="description-toggle" onclick="this.previousElementSibling.innerHTML='${fullDescription.replace(/'/g, "\\'")}'; this.style.display='none';">Read More</span>` : ''}
                    
                    <div class="recommendation-actions">
                        
                        
                    </div>
                </div>
            `;
            
            // Remove click handler - no modal in step 3
            bookElement.style.cursor = 'default';
            bookElement.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                return false;
            });
            detectedBooksGrid.appendChild(bookElement);
        });
        
        const detectedBooksSection = document.getElementById('detectedBooksSectionStep3');
        if (detectedBooksSection) {
            detectedBooksSection.style.display = 'block';
        }
    }

    // Render recommendations
    renderRecommendations() {
        // First render the detected books in step 3
        this.renderDetectedBooksInStep3();
        
        const booksGrid = document.getElementById('booksGrid');
        booksGrid.innerHTML = '';

        if (this.recommendations.length === 0) {
            booksGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #a0a0a0;">
                    <i class="fas fa-book-open" style="font-size: 3rem; margin-bottom: 20px; opacity: 0.5;"></i>
                    <h3>No recommendations found</h3>
                    <p>We couldn't find any new books that match your preferences. Try selecting different genres or upload a different image.</p>
                </div>
            `;
            return;
        }

        // Add recommendation header with stats
        const recommendationsHeader = document.querySelector('.recommendations-header');
        if (recommendationsHeader) {
            const sourceText = this.recommendationSource ? ` (Powered by ${this.recommendationSource})` : '';
            recommendationsHeader.innerHTML = `
                <h3>Recommended for You${sourceText}</h3>
                <p>${this.recommendations.length} personalized recommendations based on your ${this.recommendationStats?.detectedBooks || 0} detected books and preferences</p>
                <div class="recommendation-filters">
                    <button class="filter-btn active" data-filter="all">All (${this.recommendations.length})</button>
                    ${this.getGenreFilterButtons()}
                    <select class="sort-select" id="sortSelect">
                        <option value="rating">Sort by Rating</option>
                        <option value="title">Sort by Title</option>
                        <option value="author">Sort by Author</option>
                        <option value="genre">Sort by Genre</option>
                    </select>
                </div>
            `;
            
            // Add filter and sort functionality
            this.addFilterAndSortHandlers();
        }

        // Render all recommendations initially
        this.renderFilteredRecommendations(this.recommendations);
    }

    // Get genre filter buttons
    getGenreFilterButtons() {
        const genres = [...new Set(this.recommendations.map(book => book.genre))];
        return genres.map(genre => {
            const count = this.recommendations.filter(book => book.genre === genre).length;
            return `<button class="filter-btn" data-filter="${genre}">${genre} (${count})</button>`;
        }).join('');
    }

    // Add filter and sort event handlers
    addFilterAndSortHandlers() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                // Filter recommendations
                const filter = e.target.dataset.filter;
                let filtered = this.recommendations;
                
                if (filter !== 'all') {
                    filtered = this.recommendations.filter(book => book.genre === filter);
                }
                
                this.renderFilteredRecommendations(filtered);
            });
        });

        // Sort select
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                const sortBy = e.target.value;
                const activeFilter = document.querySelector('.filter-btn.active').dataset.filter;
                
                let filtered = this.recommendations;
                if (activeFilter !== 'all') {
                    filtered = this.recommendations.filter(book => book.genre === activeFilter);
                }
                
                // Sort the filtered results
                filtered.sort((a, b) => {
                    switch (sortBy) {
                        case 'rating':
                            return (b.rating || 0) - (a.rating || 0);
                        case 'title':
                            return a.title.localeCompare(b.title);
                        case 'author':
                            return a.author.localeCompare(b.author);
                        case 'genre':
                            return a.genre.localeCompare(b.genre);
                        default:
                            return 0;
                    }
                });
                
                this.renderFilteredRecommendations(filtered);
            });
        }
    }

    // Render filtered recommendations
    renderFilteredRecommendations(recommendations) {
        const booksGrid = document.getElementById('booksGrid');
        booksGrid.innerHTML = '';

        recommendations.forEach(book => {
            const recommendationCard = document.createElement('div');
            recommendationCard.className = 'recommendation-card';
            
            // Get rating and create stars
            const rating = book.average_rating || book.rating || 0;
            const stars = '★'.repeat(Math.floor(rating)) + '☆'.repeat(5 - Math.floor(rating));
            
            // Get cover image or use placeholder
            const coverUrl = book.cover_url || null;
            const coverHtml = coverUrl ? 
                `<img src="${coverUrl}" alt="${book.title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                '';
            
            // Get description and truncate if too long
            const fullDescription = book.description || book.reason || 'A compelling read that matches your interests.';
            const shortDescription = fullDescription.length > 200 ? fullDescription.substring(0, 200) + '...' : fullDescription;
            const isLongDescription = fullDescription.length > 200;
            
            // Create match reason text
            const matchReason = book.reason || `This book aligns with your interest in ${book.genre} and offers a compelling narrative that matches your reading preferences.`;
            
            recommendationCard.innerHTML = `
                <div class="recommendation-cover">
                    ${coverHtml}
                    <div class="no-cover" style="display: ${coverUrl ? 'none' : 'flex'}; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #666;">
                        <i class="fas fa-book" style="font-size: 2rem; margin-bottom: 8px;"></i>
                        <span>No Cover Available</span>
                    </div>
                    <div class="cover-overlay">
                        <div class="rating-display">
                            <span class="rating-stars">${stars}</span>
                            <span class="rating-number">${rating.toFixed(1)}</span>
                        </div>
                        <div class="match-badge">Great match</div>
                    </div>
                </div>
                
                <div class="recommendation-details">
                    <h3 class="recommendation-title">${book.title}</h3>
                    <p class="recommendation-author">by ${book.author}</p>
                    
                    <div class="match-reason">
                        <div class="match-reason-label">Why This Matches You:</div>
                        <p class="match-reason-text">${matchReason}</p>
                    </div>
                    
                    <p class="recommendation-description">${shortDescription}</p>
                    ${isLongDescription ? `<span class="description-toggle" onclick="this.previousElementSibling.innerHTML='${fullDescription.replace(/'/g, "\\'")}'; this.style.display='none';">Read More</span>` : ''}
                    
                    <div class="recommendation-actions">
                        ${book.amazon_url && book.amazon_url !== '#' ? `<a href="${book.amazon_url}" target="_blank" class="action-btn amazon-btn">Amazon</a>` : ''}
                        ${book.bookshop_url && book.bookshop_url !== '#' ? `<a href="${book.bookshop_url}" target="_blank" class="action-btn bookshop-btn">Bookshop</a>` : ''}
                    </div>
                </div>
            `;
            
            booksGrid.appendChild(recommendationCard);
        });
    }

    // Show book details
    showBookDetails(book) {
        const title = book.title || 'Unknown Title';
        const author = book.author || 'Unknown Author';
        const genre = book.genre || book.primary_genre || 'Unknown Genre';
        const rating = book.rating || 0;
        const reason = book.reason || book.reasoning || 'No reasoning available';
        const source = book.source || 'Unknown Source';
        const amazonUrl = book.amazon_url;
        const bookshopUrl = book.bookshop_url;
        
        // Create a more detailed modal instead of alert
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 20px;
        `;
        
        modal.innerHTML = `
            <div style="background: #2a2a3e; border-radius: 16px; padding: 30px; max-width: 500px; width: 100%; max-height: 80vh; overflow-y: auto; position: relative;">
                <button class="close-modal" style="position: absolute; top: 15px; right: 15px; background: none; border: none; color: #a0a0a0; font-size: 1.5rem; cursor: pointer;">&times;</button>
                
                <div style="text-align: center; margin-bottom: 20px;">
                    <i class="fas fa-book" style="font-size: 3rem; color: #667eea; margin-bottom: 15px;"></i>
                    <h2 style="color: #ffffff; margin-bottom: 10px;">${title}</h2>
                    <p style="color: #a0a0a0; font-size: 1.1rem;">by ${author}</p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #a0a0a0;">Genre:</span>
                        <span style="color: #667eea; font-weight: 500;">${genre}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #a0a0a0;">Rating:</span>
                        <span style="color: #ffd700;">${'★'.repeat(Math.floor(rating))}${'☆'.repeat(5 - Math.floor(rating))} (${rating.toFixed(1)})</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #a0a0a0;">Source:</span>
                        <span style="color: #28a745;">${source}</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4 style="color: #ffffff; margin-bottom: 10px;">Why you might enjoy this book:</h4>
                    <p style="color: #a0a0a0; line-height: 1.5;">${reason}</p>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: center;">
                    ${amazonUrl && amazonUrl !== '#' ? `<a href="${amazonUrl}" target="_blank" class="action-btn amazon-btn" style="background: #ff9900; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 500;">Buy on Amazon</a>` : ''}
                    ${bookshopUrl && bookshopUrl !== '#' ? `<a href="${bookshopUrl}" target="_blank" class="action-btn bookshop-btn" style="background: #667eea; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 500;">Buy on Bookshop</a>` : ''}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal handlers
        modal.querySelector('.close-modal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    // Show success message
    showSuccess(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            z-index: 1000;
            font-weight: 500;
            max-width: 400px;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 5000);
    }

    // Navigation methods
    nextStep() {
        if (this.currentStep < 3) {
            this.currentStep++;
            this.updateStepDisplay();
            this.updateProgressIndicator();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepDisplay();
            this.updateProgressIndicator();
        }
    }

    // Update step display
    updateStepDisplay() {
        // Hide all steps
        document.querySelectorAll('.step-container').forEach(step => {
            step.classList.remove('active');
            step.style.display = 'none';
        });

        // Show current step
        const currentStepElement = document.getElementById(`step${this.currentStep}`);
        currentStepElement.classList.add('active');
        currentStepElement.style.display = 'block';
    }

    // Update progress indicator
    updateProgressIndicator() {
        document.querySelectorAll('.progress-step').forEach((step, index) => {
            if (index + 1 <= this.currentStep) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
    }

    // Show error message
    showError(message) {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4757;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            z-index: 1000;
            font-weight: 500;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    }

    // Show notification message
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#667eea'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            font-size: 0.9rem;
            font-weight: 500;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BookScanner();
});

// Add some utility functions for better UX
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scrolling for better navigation
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add loading states for better feedback
    const style = document.createElement('style');
    style.textContent = `
        .fa-spinner {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .genre-item {
            user-select: none;
        }
        
        .genre-item:active {
            transform: scale(0.98);
        }
        
        .btn:active {
            transform: scale(0.98);
        }
    `;
    document.head.appendChild(style);
});
