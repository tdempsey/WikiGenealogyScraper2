import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from models import Person, FamilyTree, family_tree_data
from wikidata_api import search_person, get_person_details, get_family_relations

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
CORS(app)

# Routes
@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Render the search page."""
    return render_template('search.html')

@app.route('/api/search')
def api_search():
    """API endpoint for searching people in Wikidata."""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        page = int(request.args.get('page', 1))
        results = search_person(query, page)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/details/<entity_id>')
def details(entity_id):
    """Render the details page for a specific person."""
    return render_template('details.html', entity_id=entity_id)

@app.route('/api/details/<entity_id>')
def api_details(entity_id):
    """API endpoint for getting details about a specific person."""
    try:
        # Check if person is already in our data
        existing_person = family_tree_data.get_person(entity_id)
        
        if existing_person:
            return jsonify(existing_person.to_dict())
        
        # If not, fetch from Wikidata
        person_data = get_person_details(entity_id)
        
        # Add to our in-memory storage
        person = Person(
            id=entity_id,
            name=person_data.get('name', 'Unknown'),
            birth_date=person_data.get('birth_date'),
            death_date=person_data.get('death_date'),
            bio=person_data.get('description', ''),
            gender=person_data.get('gender'),
            image_url=person_data.get('image_url'),
            birth_place=person_data.get('birth_place'),
            occupations=person_data.get('occupations', [])
        )
        
        family_tree_data.add_person(person)
        
        return jsonify(person.to_dict())
    
    except Exception as e:
        logger.error(f"Details error: {str(e)}")
        return jsonify({'error': f'Failed to get details: {str(e)}'}), 500

@app.route('/api/family/<entity_id>')
def api_family(entity_id):
    """API endpoint for getting family relations of a specific person."""
    try:
        relations = get_family_relations(entity_id)
        
        # Add all relations to our in-memory data store
        for relation_type, relation_list in relations.items():
            for relation in relation_list:
                if not family_tree_data.get_person(relation['id']):
                    person = Person(
                        id=relation['id'],
                        name=relation['name'],
                        birth_date=relation.get('birth_date'),
                        death_date=relation.get('death_date'),
                        bio=relation.get('description', ''),
                        gender=relation.get('gender')
                    )
                    family_tree_data.add_person(person)
                
                # Add relationship
                if relation_type == 'parents':
                    family_tree_data.add_relation(relation['id'], entity_id, 'parent')
                elif relation_type == 'children':
                    family_tree_data.add_relation(entity_id, relation['id'], 'parent')
                elif relation_type == 'spouses':
                    family_tree_data.add_relation(entity_id, relation['id'], 'spouse')
                elif relation_type == 'siblings':
                    family_tree_data.add_relation(entity_id, relation['id'], 'sibling')
        
        # Get the structured family data for visualization
        family_data = family_tree_data.get_family_network(entity_id)
        return jsonify(family_data)
    
    except Exception as e:
        logger.error(f"Family relations error: {str(e)}")
        return jsonify({'error': f'Failed to get family relations: {str(e)}'}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
