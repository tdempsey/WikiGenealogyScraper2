/**
 * JavaScript for person details page
 */

/**
 * Load details for a specific person
 * @param {string} entityId - The Wikidata entity ID
 */
function loadPersonDetails(entityId) {
    // Show loading indicator
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('detailsContainer').style.display = 'none';
    
    // Load person details
    fetch(`/api/details/${entityId}`)
        .then(response => response.json())
        .then(personData => {
            if (!personData) {
                throw new Error('Person not found');
            }
            
            // Display person details
            displayPersonDetails(personData);
            
            // Load family relations
            return fetch(`/api/family/${entityId}`);
        })
        .then(response => response.json())
        .then(familyData => {
            // Display family relations
            displayFamilyRelations(familyData);
            
            // Initialize visualization if D3.js is available
            if (typeof d3 !== 'undefined') {
                // Convert family data to network format
                const networkData = {
                    nodes: [],
                    links: []
                };
                
                // Add central person
                networkData.nodes.push({
                    id: entityId,
                    name: document.getElementById('personName').innerText,
                    type: 'self'
                });
                
                // Add parents and links
                familyData.parents.forEach(parent => {
                    networkData.nodes.push({
                        id: parent.id,
                        name: parent.name,
                        type: 'parent'
                    });
                    
                    networkData.links.push({
                        source: parent.id,
                        target: entityId,
                        type: 'parent'
                    });
                });
                
                // Add children and links
                familyData.children.forEach(child => {
                    networkData.nodes.push({
                        id: child.id,
                        name: child.name,
                        type: 'child'
                    });
                    
                    networkData.links.push({
                        source: entityId,
                        target: child.id,
                        type: 'parent'
                    });
                });
                
                // Add spouses and links
                familyData.spouses.forEach(spouse => {
                    networkData.nodes.push({
                        id: spouse.id,
                        name: spouse.name,
                        type: 'spouse'
                    });
                    
                    networkData.links.push({
                        source: entityId,
                        target: spouse.id,
                        type: 'spouse'
                    });
                });
                
                // Add siblings and links
                familyData.siblings.forEach(sibling => {
                    networkData.nodes.push({
                        id: sibling.id,
                        name: sibling.name,
                        type: 'sibling'
                    });
                    
                    // Add links to parents if available
                    let linkedToParent = false;
                    familyData.parents.forEach(parent => {
                        networkData.links.push({
                            source: parent.id,
                            target: sibling.id,
                            type: 'parent'
                        });
                        linkedToParent = true;
                    });
                    
                    // If no parent links, link directly to central person
                    if (!linkedToParent) {
                        networkData.links.push({
                            source: entityId,
                            target: sibling.id,
                            type: 'sibling'
                        });
                    }
                });
                
                // Deduplicate nodes
                const uniqueNodes = Array.from(new Map(networkData.nodes.map(node => [node.id, node])).values());
                networkData.nodes = uniqueNodes;
                
                // Initialize visualization
                initializeVisualization(networkData);
            }
            
            // Hide loading indicator
            document.getElementById('loadingIndicator').style.display = 'none';
            document.getElementById('detailsContainer').style.display = 'block';
        })
        .catch(error => {
            console.error('Error loading person details:', error);
            document.getElementById('loadingIndicator').style.display = 'none';
            document.getElementById('detailsContainer').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    Error loading person details: ${error.message}
                </div>
                <a href="/search" class="btn btn-primary">
                    <i class="fas fa-arrow-left mr-1"></i>
                    Back to Search
                </a>
            `;
        });
}

/**
 * Display person details on the page
 * @param {Object} person - The person data
 */
function displayPersonDetails(person) {
    // Basic info
    document.getElementById('personName').innerText = person.name || 'Unknown';
    document.getElementById('personDescription').innerText = person.bio || '';
    document.getElementById('birthDate').innerText = person.birth_date ? formatDate(person.birth_date) : '-';
    document.getElementById('deathDate').innerText = person.death_date ? formatDate(person.death_date) : '-';
    document.getElementById('gender').innerText = person.gender || '-';
    document.getElementById('birthPlace').innerText = person.birth_place || '-';
    
    // Data source
    const sourceText = person.source === 'database' 
        ? `Data from local database (last updated: ${formatDate(person.last_updated)})`
        : 'Data from Wikidata';
    
    const sourceIcon = person.source === 'database' 
        ? `<i class="fas fa-database"></i>`
        : `<i class="fas fa-cloud"></i>`;
    
    document.getElementById('dataSource').innerHTML = `${sourceIcon} ${sourceText}`;
    
    // If we have a database record, update the database tab
    if (person.source === 'database' && person.last_updated) {
        document.getElementById('lastUpdated').innerText = formatDate(person.last_updated);
        document.getElementById('wikidataId').innerText = person.id;
    }
    
    // Occupations
    if (person.occupations && person.occupations.length > 0) {
        document.getElementById('occupation').innerText = person.occupations.join(', ');
    }
    
    // Image
    if (person.image_url) {
        const personImage = document.getElementById('personImage');
        personImage.src = person.image_url;
        personImage.alt = `${person.name} image`;
        personImage.style.display = 'block';
    }
}

/**
 * Display family relations on the page
 * @param {Object} familyData - The family data with nodes and links
 */
function displayFamilyRelations(familyData) {
    // Display parents
    displayRelationSection(
        document.getElementById('parentsList'), 
        familyData.parents, 
        'parent'
    );
    
    // Display children
    displayRelationSection(
        document.getElementById('childrenList'), 
        familyData.children, 
        'child'
    );
    
    // Display spouses
    displayRelationSection(
        document.getElementById('spousesList'), 
        familyData.spouses, 
        'spouse'
    );
    
    // Display siblings
    displayRelationSection(
        document.getElementById('siblingsList'), 
        familyData.siblings, 
        'sibling'
    );
}

/**
 * Display a section of family relations
 * @param {HTMLElement} container - The container element
 * @param {Array} relations - The list of related people
 * @param {string} relationType - The type of relation
 */
function displayRelationSection(container, relations, relationType) {
    if (!relations || relations.length === 0) {
        container.innerHTML = `<p class="text-muted">No ${relationType}s found.</p>`;
        return;
    }
    
    // Create a map of already displayed people by ID to prevent duplicates
    const displayedPeople = new Map();
    
    let html = '';
    
    relations.forEach(person => {
        // Skip if this person has already been displayed
        if (displayedPeople.has(person.id)) {
            return;
        }
        displayedPeople.set(person.id, true);
        
        html += `
            <div class="person-card">
                <div class="person-card-image">
                    ${
                        person.image_url 
                            ? `<img src="${person.image_url}" alt="${escapeHtml(person.name)}">`
                            : `<div class="placeholder"><i class="fas fa-user"></i></div>`
                    }
                </div>
                <div class="person-card-content">
                    <div class="person-card-title">
                        <a href="/details/${person.id}">${escapeHtml(person.name)}</a>
                    </div>
                    <div class="person-card-dates">
                        ${person.birth_date ? formatDate(person.birth_date) : '?'} - 
                        ${person.death_date ? formatDate(person.death_date) : (relationType === 'parent' || relationType === 'spouse' ? '?' : '')}
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Helper function to format dates in a readable way
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
        return dateString; // Return the original string if it's not a valid date
    }
    
    // Format the date
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Helper function to capitalize the first letter of a string
 * @param {string} string - The input string
 * @returns {string} - The string with first letter capitalized
 */
function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
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