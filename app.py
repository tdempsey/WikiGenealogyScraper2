import os
import threading
import logging
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy without binding it to an app
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)

# Configure app
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "genealogy_scraper_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Import models after initializing db
with app.app_context():
    from database_schema import Person, Relationship, Occupation
    from wikidata_api import search_person, get_person_details, get_family_relations
    
    # Create tables if they don't exist
    db.create_all()

# Import batch scraper
from batch_scraper import BatchScraper

# Track running jobs
scraper_jobs = {}

@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Render the search page."""
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    
    return render_template('search.html', query=query, page=page)

@app.route('/api/search')
def api_search():
    """API endpoint for searching people in Wikidata."""
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return jsonify({"error": "No search query provided"}), 400
    
    results = search_person(query, page=page)
    return jsonify(results)

@app.route('/details/<entity_id>')
def details(entity_id):
    """Render the details page for a specific person."""
    # First check if person exists in our database
    person = db.session.query(Person).filter_by(wikidata_id=entity_id).first()
    
    # If not in database, we'll get data from Wikidata API
    in_database = person is not None
    
    return render_template('details.html', entity_id=entity_id, in_database=in_database)

@app.route('/api/details/<entity_id>')
def api_details(entity_id):
    """API endpoint for getting details about a specific person."""
    # First check if person exists in our database
    person = db.session.query(Person).filter_by(wikidata_id=entity_id).first()
    
    if person:
        # Format data from the database
        person_data = {
            'id': person.wikidata_id,
            'name': person.name,
            'birth_date': person.birth_date.isoformat() if person.birth_date else None,
            'death_date': person.death_date.isoformat() if person.death_date else None,
            'bio': person.bio,
            'gender': person.gender,
            'image_url': person.image_url,
            'birth_place': person.birth_place,
            'occupations': [occ.name for occ in person.occupations],
            'source': 'database',
            'last_updated': person.last_updated.isoformat() if person.last_updated else None
        }
    else:
        # Get data from the Wikidata API
        person_data = get_person_details(entity_id)
        if person_data:
            person_data['source'] = 'wikidata'
    
    if not person_data:
        return jsonify({"error": "Person not found"}), 404
    
    return jsonify(person_data)

@app.route('/api/family/<entity_id>')
def api_family(entity_id):
    """API endpoint for getting family relations of a specific person."""
    # First check if we have this person's relationships in our database
    person = db.session.query(Person).filter_by(wikidata_id=entity_id).first()
    
    if person:
        # Get relationships from database
        relations = db.session.query(Relationship).filter(
            (Relationship.source_id == entity_id) | 
            (Relationship.target_id == entity_id)
        ).all()
        
        # Organize by relationship type
        family_data = {
            'parents': [],
            'children': [],
            'spouses': [],
            'siblings': []
        }
        
        for relation in relations:
            if relation.relation_type == 'parent':
                if relation.source_id == entity_id:
                    # This person is the parent
                    child = db.session.query(Person).filter_by(wikidata_id=relation.target_id).first()
                    if child:
                        family_data['children'].append({
                            'id': child.wikidata_id,
                            'name': child.name,
                            'birth_date': child.birth_date.isoformat() if child.birth_date else None,
                            'death_date': child.death_date.isoformat() if child.death_date else None,
                            'image_url': child.image_url
                        })
                else:
                    # This person is the child
                    parent = db.session.query(Person).filter_by(wikidata_id=relation.source_id).first()
                    if parent:
                        family_data['parents'].append({
                            'id': parent.wikidata_id,
                            'name': parent.name,
                            'birth_date': parent.birth_date.isoformat() if parent.birth_date else None,
                            'death_date': parent.death_date.isoformat() if parent.death_date else None,
                            'image_url': parent.image_url
                        })
            
            elif relation.relation_type == 'spouse':
                # Find the spouse
                spouse_id = relation.target_id if relation.source_id == entity_id else relation.source_id
                spouse = db.session.query(Person).filter_by(wikidata_id=spouse_id).first()
                if spouse:
                    family_data['spouses'].append({
                        'id': spouse.wikidata_id,
                        'name': spouse.name,
                        'birth_date': spouse.birth_date.isoformat() if spouse.birth_date else None,
                        'death_date': spouse.death_date.isoformat() if spouse.death_date else None,
                        'image_url': spouse.image_url
                    })
            
            elif relation.relation_type == 'sibling':
                # Find the sibling
                sibling_id = relation.target_id if relation.source_id == entity_id else relation.source_id
                sibling = db.session.query(Person).filter_by(wikidata_id=sibling_id).first()
                if sibling:
                    family_data['siblings'].append({
                        'id': sibling.wikidata_id,
                        'name': sibling.name,
                        'birth_date': sibling.birth_date.isoformat() if sibling.birth_date else None,
                        'death_date': sibling.death_date.isoformat() if sibling.death_date else None,
                        'image_url': sibling.image_url
                    })
        
        family_data['source'] = 'database'
    else:
        # Get data from the Wikidata API
        family_data = get_family_relations(entity_id)
        if family_data:
            family_data['source'] = 'wikidata'
    
    if not family_data:
        return jsonify({"error": "Family relations not found"}), 404
        
    return jsonify(family_data)

@app.route('/batch')
def batch_page():
    """Render the batch scraping page."""
    # Get stats about the database
    stats = {
        'people_count': db.session.query(Person).count(),
        'relationship_count': db.session.query(Relationship).count(),
        'occupation_count': db.session.query(Occupation).count()
    }
    
    # Get running and completed jobs
    jobs = []
    for job_id, job_info in scraper_jobs.items():
        jobs.append({
            'id': job_id,
            'entity_id': job_info.get('entity_id'),
            'query': job_info.get('query'),
            'status': job_info.get('status'),
            'started': job_info.get('started'),
            'finished': job_info.get('finished'),
            'stats': job_info.get('stats')
        })
    
    return render_template('batch.html', stats=stats, jobs=jobs)

@app.route('/api/batch/start', methods=['POST'])
def api_batch_start():
    """API endpoint to start a batch scraping job."""
    entity_id = request.form.get('entity_id')
    query = request.form.get('query')
    max_depth = request.form.get('max_depth', 2, type=int)
    
    if not entity_id and not query:
        return jsonify({"error": "Either entity_id or query must be provided"}), 400
    
    # Generate a job ID
    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Create job info
    job_info = {
        'entity_id': entity_id,
        'query': query,
        'status': 'starting',
        'started': datetime.datetime.now().isoformat(),
        'finished': None,
        'stats': None
    }
    
    scraper_jobs[job_id] = job_info
    
    # Start the job in a background thread
    def run_scraper_job():
        with app.app_context():
            try:
                # Create a new SQLAlchemy session for this thread
                session = db.create_scoped_session()
                
                # Update job status
                job_info['status'] = 'running'
                
                # Create scraper
                scraper = BatchScraper(session, max_depth=max_depth)
                
                # Run scraper
                if entity_id:
                    scraper.run_from_entity_id(entity_id)
                elif query:
                    scraper.run_from_search(query)
                
                # Update job info
                job_info['status'] = 'completed'
                job_info['finished'] = datetime.datetime.now().isoformat()
                job_info['stats'] = scraper.stats
                
            except Exception as e:
                logger.error(f"Error in scraper job {job_id}: {str(e)}")
                job_info['status'] = 'failed'
                job_info['error'] = str(e)
                job_info['finished'] = datetime.datetime.now().isoformat()
    
    thread = threading.Thread(target=run_scraper_job)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "started",
        "message": "Batch scraping job started successfully"
    })

@app.route('/api/batch/status/<job_id>')
def api_batch_status(job_id):
    """API endpoint to get the status of a batch scraping job."""
    if job_id not in scraper_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(scraper_jobs[job_id])

@app.route('/api/database/stats')
def api_database_stats():
    """API endpoint to get database statistics."""
    # Get basic counts
    stats = {
        'people_count': db.session.query(Person).count(),
        'relationship_count': db.session.query(Relationship).count(),
        'occupation_count': db.session.query(Occupation).count()
    }
    
    # Get most recent people
    recent_people = db.session.query(Person).order_by(Person.last_updated.desc()).limit(10).all()
    stats['recent_people'] = [
        {
            'id': p.wikidata_id,
            'name': p.name,
            'last_updated': p.last_updated.isoformat() if p.last_updated else None
        }
        for p in recent_people
    ]
    
    return jsonify(stats)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500