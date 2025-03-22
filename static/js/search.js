/**
 * Search functionality for the genealogy application
 */

// DOM elements
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const loadingIndicator = document.getElementById('loading-indicator');
const resultsContainer = document.getElementById('results-container');
const resultsHeading = document.getElementById('results-heading');
const resultsList = document.getElementById('results-list');
const pagination = document.getElementById('pagination');
const noResults = document.getElementById('no-results');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');

// Current search state
let currentQuery = '';
let currentPage = 1;
let totalResults = 0;
let resultsPerPage = 10;

// Add event listener to the search form
searchForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const query = searchInput.value.trim();
    
    if (query) {
        currentQuery = query;
        currentPage = 1;
        performSearch(query, currentPage);
        
        // Update URL with the search query for sharing/bookmarking
        const url = new URL(window.location);
        url.searchParams.set('query', query);
        window.history.pushState({}, '', url);
    }
});

/**
 * Perform search for people using the API
 * @param {string} query - The search query
 * @param {number} page - The page number
 */
function performSearch(query, page) {
    // Show loading indicator
    loadingIndicator.classList.remove('d-none');
    resultsContainer.classList.add('d-none');
    noResults.classList.add('d-none');
    errorMessage.classList.add('d-none');
    
    // Build API URL
    const apiUrl = `/api/search?query=${encodeURIComponent(query)}&page=${page}`;
    
    // Fetch search results
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Update current search state
            currentPage = data.page || 1;
            totalResults = data.total || 0;
            
            // Display results
            displaySearchResults(data);
        })
        .catch(error => {
            // Display error message
            errorText.textContent = `Error searching: ${error.message}`;
            errorMessage.classList.remove('d-none');
            console.error('Search error:', error);
        })
        .finally(() => {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
        });
}

/**
 * Display search results on the page
 * @param {Object} data - The search results data
 */
function displaySearchResults(data) {
    // Clear previous results
    resultsList.innerHTML = '';
    
    const results = data.results || [];
    
    if (results.length === 0) {
        // Show no results message
        noResults.classList.remove('d-none');
        return;
    }
    
    // Update results heading
    resultsHeading.textContent = `Search Results for "${currentQuery}" (${totalResults} found)`;
    
    // Create result cards
    results.forEach(person => {
        const resultCard = document.createElement('div');
        resultCard.className = 'card search-result-card mb-3';
        
        resultCard.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">${escapeHtml(person.name)}</h5>
                    <a href="/details/${person.id}" class="btn btn-sm btn-primary">View Details</a>
                </div>
                ${person.description ? `<p class="card-text text-muted mt-2">${escapeHtml(person.description)}</p>` : ''}
                <div class="mt-2">
                    <small class="text-muted">Wikidata ID: ${person.id}</small>
                </div>
            </div>
        `;
        
        resultsList.appendChild(resultCard);
    });
    
    // Create pagination
    createPagination(currentPage, Math.ceil(totalResults / resultsPerPage));
    
    // Show results container
    resultsContainer.classList.remove('d-none');
}

/**
 * Create pagination controls
 * @param {number} currentPage - The current page number
 * @param {number} totalPages - The total number of pages
 */
function createPagination(currentPage, totalPages) {
    pagination.innerHTML = '';
    
    if (totalPages <= 1) {
        return;
    }
    
    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.setAttribute('aria-label', 'Previous');
    prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
    
    if (currentPage > 1) {
        prevLink.addEventListener('click', function(e) {
            e.preventDefault();
            performSearch(currentQuery, currentPage - 1);
        });
    }
    
    prevLi.appendChild(prevLink);
    pagination.appendChild(prevLi);
    
    // Page numbers
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Adjust startPage if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    // First page if not visible
    if (startPage > 1) {
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item';
        
        const firstLink = document.createElement('a');
        firstLink.className = 'page-link';
        firstLink.href = '#';
        firstLink.textContent = '1';
        
        firstLink.addEventListener('click', function(e) {
            e.preventDefault();
            performSearch(currentQuery, 1);
        });
        
        firstLi.appendChild(firstLink);
        pagination.appendChild(firstLi);
        
        // Ellipsis if needed
        if (startPage > 2) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            
            const ellipsisSpan = document.createElement('span');
            ellipsisSpan.className = 'page-link';
            ellipsisSpan.innerHTML = '&hellip;';
            
            ellipsisLi.appendChild(ellipsisSpan);
            pagination.appendChild(ellipsisLi);
        }
    }
    
    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        
        if (i !== currentPage) {
            pageLink.addEventListener('click', function(e) {
                e.preventDefault();
                performSearch(currentQuery, i);
            });
        }
        
        pageLi.appendChild(pageLink);
        pagination.appendChild(pageLi);
    }
    
    // Ellipsis and last page if not visible
    if (endPage < totalPages) {
        // Ellipsis if needed
        if (endPage < totalPages - 1) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            
            const ellipsisSpan = document.createElement('span');
            ellipsisSpan.className = 'page-link';
            ellipsisSpan.innerHTML = '&hellip;';
            
            ellipsisLi.appendChild(ellipsisSpan);
            pagination.appendChild(ellipsisLi);
        }
        
        // Last page
        const lastLi = document.createElement('li');
        lastLi.className = 'page-item';
        
        const lastLink = document.createElement('a');
        lastLink.className = 'page-link';
        lastLink.href = '#';
        lastLink.textContent = totalPages;
        
        lastLink.addEventListener('click', function(e) {
            e.preventDefault();
            performSearch(currentQuery, totalPages);
        });
        
        lastLi.appendChild(lastLink);
        pagination.appendChild(lastLi);
    }
    
    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.setAttribute('aria-label', 'Next');
    nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
    
    if (currentPage < totalPages) {
        nextLink.addEventListener('click', function(e) {
            e.preventDefault();
            performSearch(currentQuery, currentPage + 1);
        });
    }
    
    nextLi.appendChild(nextLink);
    pagination.appendChild(nextLi);
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
