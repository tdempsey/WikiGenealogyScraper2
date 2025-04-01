/**
 * JavaScript for search functionality
 */

/**
 * Perform search for people using the API
 * @param {string} query - The search query
 * @param {number} page - The page number
 */
function performSearch(query, page) {
    // Show loading indicator
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('resultsContainer').innerHTML = '';
    document.getElementById('pagination').innerHTML = '';
    
    // Make API request
    fetch(`/api/search?query=${encodeURIComponent(query)}&page=${page}`)
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            document.getElementById('loadingIndicator').style.display = 'none';
            
            // Display results
            displaySearchResults(data);
            
            // Create pagination if needed
            if (data.pages > 1) {
                createPagination(page, data.pages, query);
            }
        })
        .catch(error => {
            console.error('Error performing search:', error);
            document.getElementById('loadingIndicator').style.display = 'none';
            document.getElementById('resultsContainer').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    Error searching Wikidata: ${error.message}
                </div>
            `;
        });
}

/**
 * Display search results on the page
 * @param {Object} data - The search results data
 */
function displaySearchResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    if (!data.results || data.results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle mr-2"></i>
                No results found. Try a different search term.
            </div>
        `;
        return;
    }
    
    let html = `
        <p class="mb-3">Found ${data.total} results</p>
        <div class="list-group">
    `;
    
    data.results.forEach(result => {
        html += `
            <a href="/details/${result.id}" class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${escapeHtml(result.label)}</h5>
                    <small class="text-muted">${result.id}</small>
                </div>
                <p class="mb-1">${escapeHtml(result.description || 'No description available')}</p>
            </a>
        `;
    });
    
    html += '</div>';
    resultsContainer.innerHTML = html;
}

/**
 * Create pagination controls
 * @param {number} currentPage - The current page number
 * @param {number} totalPages - The total number of pages
 * @param {string} query - The search query
 */
function createPagination(currentPage, totalPages, query) {
    const paginationContainer = document.getElementById('pagination');
    
    let html = '<nav aria-label="Search results pages"><ul class="pagination">';
    
    // Previous button
    if (currentPage > 1) {
        html += `
            <li class="page-item">
                <a class="page-link" href="/search?query=${encodeURIComponent(query)}&page=${currentPage - 1}" aria-label="Previous">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
        `;
    } else {
        html += `
            <li class="page-item disabled">
                <a class="page-link" href="#" aria-label="Previous">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
        `;
    }
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        if (i === currentPage) {
            html += `<li class="page-item active"><a class="page-link" href="#">${i}</a></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="/search?query=${encodeURIComponent(query)}&page=${i}">${i}</a></li>`;
        }
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `
            <li class="page-item">
                <a class="page-link" href="/search?query=${encodeURIComponent(query)}&page=${currentPage + 1}" aria-label="Next">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        `;
    } else {
        html += `
            <li class="page-item disabled">
                <a class="page-link" href="#" aria-label="Next">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        `;
    }
    
    html += '</ul></nav>';
    paginationContainer.innerHTML = html;
    
    // Attach event listeners to prevent page refresh and use AJAX instead
    document.querySelectorAll('#pagination .page-link').forEach(link => {
        link.addEventListener('click', function(event) {
            if (!this.parentElement.classList.contains('disabled') && !this.parentElement.classList.contains('active')) {
                event.preventDefault();
                
                const href = this.getAttribute('href');
                if (href && href !== '#') {
                    const url = new URL(href, window.location.origin);
                    const newQuery = url.searchParams.get('query');
                    const newPage = parseInt(url.searchParams.get('page'));
                    
                    // Update browser URL
                    history.pushState({}, "", href);
                    
                    // Perform new search
                    performSearch(newQuery, newPage);
                }
            }
        });
    });
}

/**
 * Helper function to escape HTML special characters
 * @param {string} html - The string to escape
 * @returns {string} - The escaped string
 */
function escapeHtml(html) {
    if (!html) return '';
    
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}