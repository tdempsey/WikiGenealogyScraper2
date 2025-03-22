/**
 * Person details functionality for the genealogy application
 */

// DOM elements
const loadingContainer = document.getElementById('loading-container');
const personContainer = document.getElementById('person-container');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');

// Person details elements
const personName = document.getElementById('person-name');
const personDates = document.getElementById('person-dates');
const personDescription = document.getElementById('person-description');
const personImage = document.getElementById('person-image');
const personImageContainer = document.getElementById('person-image-container');
const birthDate = document.getElementById('birth-date');
const deathDate = document.getElementById('death-date');
const birthPlace = document.getElementById('birth-place');
const gender = document.getElementById('gender');
const occupationsList = document.getElementById('occupations-list');

// Family section containers
const parentsContainer = document.getElementById('parents-container');
const childrenContainer = document.getElementById('children-container');
const spousesContainer = document.getElementById('spouses-container');
const siblingsContainer = document.getElementById('siblings-container');

// The entity ID is set in the template via the 'entityId' variable

// Load person details when the page loads
document.addEventListener('DOMContentLoaded', function() {
    loadPersonDetails(entityId);
});

/**
 * Load details for a specific person
 * @param {string} entityId - The Wikidata entity ID
 */
function loadPersonDetails(entityId) {
    // Show loading state
    loadingContainer.classList.remove('d-none');
    personContainer.classList.add('d-none');
    errorContainer.classList.add('d-none');
    
    // Fetch person details
    fetch(`/api/details/${entityId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(personData => {
            // Display person details
            displayPersonDetails(personData);
            
            // Now fetch family relations
            return fetch(`/api/family/${entityId}`);
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(familyData => {
            // Display family relations
            displayFamilyRelations(familyData);
            
            // Initialize the family visualization
            if (typeof initializeVisualization === 'function') {
                initializeVisualization(familyData);
            }
        })
        .catch(error => {
            // Show error message
            errorMessage.textContent = `Error loading person details: ${error.message}`;
            errorContainer.classList.remove('d-none');
            console.error('Error:', error);
        })
        .finally(() => {
            // Hide loading indicator
            loadingContainer.classList.add('d-none');
        });
}

/**
 * Display person details on the page
 * @param {Object} person - The person data
 */
function displayPersonDetails(person) {
    // Set basic information
    document.title = `${person.name} - Wikidata Genealogy Explorer`;
    personName.textContent = person.name || 'Unknown Name';
    
    // Format and display birth/death dates
    let datesText = '';
    if (person.birth_date) {
        const birthYear = new Date(person.birth_date).getFullYear();
        datesText += birthYear;
    }
    datesText += ' - ';
    if (person.death_date) {
        const deathYear = new Date(person.death_date).getFullYear();
        datesText += deathYear;
    }
    personDates.textContent = datesText !== ' - ' ? datesText : '';
    
    // Set description
    personDescription.textContent = person.bio || '';
    
    // Set image if available
    if (person.image_url) {
        personImage.src = person.image_url;
        personImage.alt = `Image of ${person.name}`;
        personImageContainer.classList.remove('d-none');
    } else {
        personImageContainer.classList.add('d-none');
    }
    
    // Set personal information
    if (person.birth_date) {
        birthDate.textContent = formatDate(person.birth_date);
    } else {
        document.getElementById('birth-date-row').classList.add('d-none');
    }
    
    if (person.death_date) {
        deathDate.textContent = formatDate(person.death_date);
    } else {
        document.getElementById('death-date-row').classList.add('d-none');
    }
    
    if (person.birth_place) {
        birthPlace.textContent = person.birth_place;
    } else {
        document.getElementById('birth-place-row').classList.add('d-none');
    }
    
    if (person.gender) {
        gender.textContent = capitalizeFirstLetter(person.gender);
    } else {
        document.getElementById('gender-row').classList.add('d-none');
    }
    
    // Set occupations
    if (person.occupations && person.occupations.length > 0) {
        occupationsList.innerHTML = '';
        person.occupations.forEach(occupation => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = occupation;
            occupationsList.appendChild(li);
        });
    } else {
        document.getElementById('occupations-card').classList.add('d-none');
    }
    
    // Show person container
    personContainer.classList.remove('d-none');
}

/**
 * Display family relations on the page
 * @param {Object} familyData - The family data with nodes and links
 */
function displayFamilyRelations(familyData) {
    // Group nodes by their relationship to the central person
    const centralPerson = familyData.nodes.find(node => node.depth === 0);
    if (!centralPerson) return;
    
    const relations = {
        parents: [],
        children: [],
        spouses: [],
        siblings: []
    };
    
    // Find direct relations using links
    familyData.links.forEach(link => {
        // Skip links not directly connected to central person
        if (link.source !== centralPerson.id && link.target !== centralPerson.id) {
            return;
        }
        
        const relationType = link.type;
        const relatedId = link.source === centralPerson.id ? link.target : link.source;
        const relatedPerson = familyData.nodes.find(node => node.id === relatedId);
        
        if (!relatedPerson) return;
        
        if (relationType === 'parent') {
            // If central person is the target, then the source is a parent
            if (link.target === centralPerson.id) {
                relations.parents.push(relatedPerson);
            } else {
                // If central person is the source, then the target is a child
                relations.children.push(relatedPerson);
            }
        } else if (relationType === 'spouse') {
            relations.spouses.push(relatedPerson);
        } else if (relationType === 'sibling') {
            relations.siblings.push(relatedPerson);
        }
    });
    
    // Display each type of relation
    displayRelationSection(parentsContainer, relations.parents, 'parent');
    displayRelationSection(childrenContainer, relations.children, 'child');
    displayRelationSection(spousesContainer, relations.spouses, 'spouse');
    displayRelationSection(siblingsContainer, relations.siblings, 'sibling');
}

/**
 * Display a section of family relations
 * @param {HTMLElement} container - The container element
 * @param {Array} relations - The list of related people
 * @param {string} relationType - The type of relation
 */
function displayRelationSection(container, relations, relationType) {
    container.innerHTML = '';
    
    if (relations.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        
        let iconClass = 'fas fa-question';
        let message = 'No information available';
        
        if (relationType === 'parent') {
            iconClass = 'fas fa-user-friends';
            message = 'No parents found in the data';
        } else if (relationType === 'child') {
            iconClass = 'fas fa-child';
            message = 'No children found in the data';
        } else if (relationType === 'spouse') {
            iconClass = 'fas fa-heart';
            message = 'No spouses found in the data';
        } else if (relationType === 'sibling') {
            iconClass = 'fas fa-users';
            message = 'No siblings found in the data';
        }
        
        emptyState.innerHTML = `
            <div class="empty-state-icon">
                <i class="${iconClass}"></i>
            </div>
            <p>${message}</p>
        `;
        
        container.appendChild(emptyState);
        return;
    }
    
    // Sort relations by birth date if available
    relations.sort((a, b) => {
        if (!a.birth_date) return 1;
        if (!b.birth_date) return -1;
        return new Date(a.birth_date) - new Date(b.birth_date);
    });
    
    // Create cards for each relation
    relations.forEach(relation => {
        const card = document.createElement('div');
        card.className = 'relation-card mb-3';
        
        let lifespan = '';
        if (relation.birth_date) {
            const birthYear = new Date(relation.birth_date).getFullYear();
            lifespan += birthYear;
        }
        lifespan += ' - ';
        if (relation.death_date) {
            const deathYear = new Date(relation.death_date).getFullYear();
            lifespan += deathYear;
        }
        
        // Create relation badge
        const badgeClass = `relation-badge relation-${relationType}`;
        const badgeText = capitalizeFirstLetter(relationType);
        
        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">${escapeHtml(relation.name || 'Unknown')}</h5>
                        ${lifespan !== ' - ' ? `<p class="text-muted small mb-2">${lifespan}</p>` : ''}
                        <span class="${badgeClass}">${badgeText}</span>
                    </div>
                    <a href="/details/${relation.id}" class="btn btn-sm btn-outline-primary">View</a>
                </div>
                ${relation.bio ? `<p class="card-text mt-2">${escapeHtml(relation.bio)}</p>` : ''}
            </div>
        `;
        
        container.appendChild(card);
    });
}

/**
 * Helper function to format dates in a readable way
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return dateString; // Return original string if parsing fails
        }
        
        // Format: Month Day, Year (e.g., January 1, 2000)
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        return date.toLocaleDateString('en-US', options);
    } catch (e) {
        console.error('Error formatting date:', e);
        return dateString;
    }
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
