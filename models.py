"""
Models for the genealogy data visualization application.

These classes represent the domain models used in the application's business logic,
separate from the database schema.
"""

class Person:
    """Class representing a person in our genealogy database."""
    
    def __init__(self, id, name, birth_date=None, death_date=None, bio=None, 
                 gender=None, image_url=None, birth_place=None, occupations=None):
        """
        Initialize a person object.
        
        Args:
            id (str): Wikidata entity ID
            name (str): Person's name
            birth_date (datetime, optional): Date of birth
            death_date (datetime, optional): Date of death
            bio (str, optional): Biographical information
            gender (str, optional): Gender
            image_url (str, optional): URL to person's image
            birth_place (str, optional): Place of birth
            occupations (list, optional): List of occupations
        """
        self.id = id
        self.name = name
        self.birth_date = birth_date
        self.death_date = death_date
        self.bio = bio
        self.gender = gender
        self.image_url = image_url
        self.birth_place = birth_place
        self.occupations = occupations or []
    
    def to_dict(self):
        """Convert Person object to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'death_date': self.death_date.isoformat() if self.death_date else None,
            'bio': self.bio,
            'gender': self.gender,
            'image_url': self.image_url,
            'birth_place': self.birth_place,
            'occupations': self.occupations
        }

class Relation:
    """Class representing a relation between two people."""
    
    def __init__(self, source_id, target_id, relation_type):
        """
        Initialize a relation between two people.
        
        Args:
            source_id (str): ID of the source person
            target_id (str): ID of the target person
            relation_type (str): Type of relation (parent, spouse, sibling)
        """
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type

class FamilyTree:
    """Class for managing family tree data."""
    
    def __init__(self):
        """Initialize an empty family tree."""
        self.people = {}
        self.relations = []
    
    def add_person(self, person):
        """Add a person to the family tree."""
        self.people[person.id] = person
    
    def get_person(self, person_id):
        """Get a person from the family tree by ID."""
        return self.people.get(person_id)
    
    def add_relation(self, source_id, target_id, relation_type):
        """Add a relation between two people."""
        relation = Relation(source_id, target_id, relation_type)
        self.relations.append(relation)
    
    def get_relations_for_person(self, person_id):
        """Get all relations for a person."""
        return [r for r in self.relations if r.source_id == person_id or r.target_id == person_id]
    
    def get_family_network(self, person_id, max_depth=2):
        """
        Get a network of family relationships centered on a person.
        
        Args:
            person_id (str): ID of the central person
            max_depth (int): Maximum depth of relationships to include
            
        Returns:
            dict: Network data suitable for D3.js visualization
        """
        if person_id not in self.people:
            return None
        
        # Initialize network data
        network = {
            'nodes': [],
            'links': []
        }
        
        # Keep track of processed people
        processed_people = set()
        
        # Helper function to add a person and their relations
        def add_person_and_relations(p_id, depth=0):
            if p_id in processed_people or depth > max_depth:
                return
            
            processed_people.add(p_id)
            person = self.get_person(p_id)
            
            if not person:
                return
            
            # Add person to nodes
            node_type = 'self' if p_id == person_id else 'other'
            network['nodes'].append({
                'id': person.id,
                'name': person.name,
                'type': node_type
            })
            
            # Stop if max depth reached
            if depth >= max_depth:
                return
            
            # Process relations
            for relation in self.get_relations_for_person(p_id):
                # Determine target ID
                target_id = relation.target_id if relation.source_id == p_id else relation.source_id
                
                # Add link
                network['links'].append({
                    'source': relation.source_id,
                    'target': relation.target_id,
                    'type': relation.relation_type
                })
                
                # Add related person
                add_person_and_relations(target_id, depth + 1)
        
        # Start with the central person
        add_person_and_relations(person_id)
        
        return network