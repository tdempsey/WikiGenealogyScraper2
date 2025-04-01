"""
Batch scraper for recursively collecting genealogical data from Wikidata.

This script:
1. Takes a starting Wikidata entity ID
2. Retrieves information about that person
3. Retrieves all relatives (parents, children, spouses, siblings)
4. For each relative, repeats the process up to a specified depth
5. Stores all collected data in a PostgreSQL database

Usage:
    python batch_scraper.py --entity_id Q9682 --max_depth 3
    python batch_scraper.py --search "Elizabeth II" --max_depth 2
"""
import argparse
import datetime
import logging
import time
import sys
from queue import Queue

from database_schema import setup_database, Person, Occupation, Relationship
from wikidata_api import search_person, get_person_details, get_family_relations

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BatchScraper")

class BatchScraper:
    """Batch scraper for genealogical data from Wikidata."""
    
    def __init__(self, db_session, max_depth=2, delay_seconds=1):
        """
        Initialize the scraper.
        
        Args:
            db_session: SQLAlchemy session for database operations
            max_depth: Maximum recursion depth (default: 2)
            delay_seconds: Delay between API requests to avoid rate limiting (default: 1 second)
        """
        self.db_session = db_session
        self.max_depth = max_depth
        self.delay_seconds = delay_seconds
        self.queue = Queue()
        self.processed_ids = set()
        self.stats = {
            'people_processed': 0,
            'people_added': 0,
            'people_updated': 0,
            'relationships_added': 0,
            'api_calls': 0,
            'errors': 0
        }
    
    def _api_call_with_delay(self, func, *args, **kwargs):
        """Make an API call with a delay to avoid rate limiting."""
        self.stats['api_calls'] += 1
        result = func(*args, **kwargs)
        time.sleep(self.delay_seconds)
        return result
    
    def _is_person_in_db(self, entity_id):
        """Check if a person is already in the database."""
        return self.db_session.query(Person).filter_by(wikidata_id=entity_id).first() is not None
    
    def _update_or_create_person(self, person_data):
        """Update an existing person record or create a new one."""
        entity_id = person_data.get('id')
        if not entity_id:
            logger.warning("Person data missing ID, skipping")
            return None
            
        # Check if person already exists
        person = self.db_session.query(Person).filter_by(wikidata_id=entity_id).first()
        
        if person:
            # Update existing record
            person.name = person_data.get('name', person.name)
            if person_data.get('birth_date'):
                person.birth_date = datetime.datetime.fromisoformat(person_data['birth_date'].replace('Z', '+00:00'))
            if person_data.get('death_date'):
                person.death_date = datetime.datetime.fromisoformat(person_data['death_date'].replace('Z', '+00:00'))
            person.bio = person_data.get('bio', person.bio)
            person.gender = person_data.get('gender', person.gender)
            person.image_url = person_data.get('image_url', person.image_url)
            person.birth_place = person_data.get('birth_place', person.birth_place)
            person.last_updated = datetime.datetime.now()
            self.stats['people_updated'] += 1
        else:
            # Create new person
            person = Person(
                wikidata_id=entity_id,
                name=person_data.get('name', 'Unknown'),
                bio=person_data.get('bio'),
                gender=person_data.get('gender'),
                image_url=person_data.get('image_url'),
                birth_place=person_data.get('birth_place'),
                last_updated=datetime.datetime.now()
            )
            
            # Handle dates
            if person_data.get('birth_date'):
                try:
                    person.birth_date = datetime.datetime.fromisoformat(person_data['birth_date'].replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid birth date format: {person_data['birth_date']}")
                    
            if person_data.get('death_date'):
                try:
                    person.death_date = datetime.datetime.fromisoformat(person_data['death_date'].replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid death date format: {person_data['death_date']}")
            
            self.db_session.add(person)
            self.stats['people_added'] += 1
            
        # Handle occupations
        if person_data.get('occupations'):
            # Clear existing occupations
            person.occupations = []
            
            # Add new occupations
            for occupation_name in person_data['occupations']:
                # Check if occupation exists
                occupation = self.db_session.query(Occupation).filter_by(name=occupation_name).first()
                if not occupation:
                    occupation = Occupation(name=occupation_name)
                    self.db_session.add(occupation)
                    self.db_session.flush()  # Generate ID without committing
                
                person.occupations.append(occupation)
        
        self.db_session.commit()
        return person
    
    def _add_relationship(self, source_id, target_id, relation_type):
        """Add a relationship between two people to the database."""
        # Check if relationship already exists
        existing = self.db_session.query(Relationship).filter_by(
            source_id=source_id, 
            target_id=target_id,
            relation_type=relation_type
        ).first()
        
        if not existing:
            relationship = Relationship(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type
            )
            self.db_session.add(relationship)
            self.db_session.commit()
            self.stats['relationships_added'] += 1
    
    def _process_relatives(self, entity_id, relatives, current_depth):
        """Process relatives and add them to the queue."""
        for relation_type, relation_list in relatives.items():
            for relation in relation_list:
                relation_id = relation['id']
                relation_type_normalized = relation_type.rstrip('s')  # Convert 'parents' to 'parent', etc.
                
                # For parents, the relation is FROM the parent TO the person
                if relation_type == 'parents':
                    self._add_relationship(relation_id, entity_id, 'parent')
                # For children, the relation is FROM the person TO the child
                elif relation_type == 'children':
                    self._add_relationship(entity_id, relation_id, 'parent')
                # For spouses, the relation is bidirectional
                elif relation_type == 'spouses':
                    self._add_relationship(entity_id, relation_id, 'spouse')
                # For siblings, the relation is bidirectional
                elif relation_type == 'siblings':
                    self._add_relationship(entity_id, relation_id, 'sibling')
                
                # Create a basic person record
                self._update_or_create_person(relation)
                
                # Add to queue for further processing if within depth limit
                if current_depth < self.max_depth and relation_id not in self.processed_ids:
                    self.queue.put((relation_id, current_depth + 1))
    
    def process_person(self, entity_id, current_depth=0):
        """
        Process a single person and their relationships.
        
        Args:
            entity_id: Wikidata entity ID (e.g., "Q9682")
            current_depth: Current recursion depth
        """
        if entity_id in self.processed_ids:
            return
            
        self.processed_ids.add(entity_id)
        
        try:
            # Get person details
            logger.info(f"Processing {entity_id} at depth {current_depth}/{self.max_depth}")
            person_data = self._api_call_with_delay(get_person_details, entity_id)
            if not person_data:
                logger.warning(f"No data found for entity {entity_id}")
                return
                
            # Update or create person record
            self._update_or_create_person(person_data)
            
            # Get family relations
            relatives = self._api_call_with_delay(get_family_relations, entity_id)
            
            # Process relatives
            self._process_relatives(entity_id, relatives, current_depth)
            
            self.stats['people_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing entity {entity_id}: {str(e)}")
            self.stats['errors'] += 1
    
    def run_from_entity_id(self, entity_id):
        """
        Run the scraper starting from a specific entity ID.
        
        Args:
            entity_id: Wikidata entity ID (e.g., "Q9682")
        """
        logger.info(f"Starting batch scraping from entity ID: {entity_id}")
        self.queue.put((entity_id, 0))
        
        while not self.queue.empty():
            current_id, depth = self.queue.get()
            self.process_person(current_id, depth)
            
        logger.info(f"Batch scraping completed. Stats: {self.stats}")
    
    def run_from_search(self, query):
        """
        Run the scraper starting from a search query.
        
        Args:
            query: Search query string (e.g., "Elizabeth II")
        """
        logger.info(f"Searching for: {query}")
        search_results = self._api_call_with_delay(search_person, query)
        
        if not search_results or not search_results.get('results'):
            logger.error(f"No results found for query: {query}")
            return
            
        # Take the first result
        first_result = search_results['results'][0]
        entity_id = first_result['id']
        
        logger.info(f"Found entity ID: {entity_id} ({first_result['label']})")
        self.run_from_entity_id(entity_id)

def main():
    """Main function to run the batch scraper."""
    parser = argparse.ArgumentParser(description="Batch scraper for genealogical data from Wikidata")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--entity_id", help="Wikidata entity ID (e.g., Q9682 for Elizabeth II)")
    group.add_argument("--search", help="Search query to find a person")
    parser.add_argument("--max_depth", type=int, default=2, help="Maximum recursion depth (default: 2)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API requests in seconds (default: 1.0)")
    
    args = parser.parse_args()
    
    # Set up database
    logger.info("Setting up database connection")
    db_session = setup_database()
    
    # Create scraper
    scraper = BatchScraper(db_session, max_depth=args.max_depth, delay_seconds=args.delay)
    
    # Run scraper
    if args.entity_id:
        scraper.run_from_entity_id(args.entity_id)
    elif args.search:
        scraper.run_from_search(args.search)

if __name__ == "__main__":
    main()