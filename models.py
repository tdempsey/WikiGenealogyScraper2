class Person:
    """Class representing a person in our genealogy database."""
    
    def __init__(self, id, name, birth_date=None, death_date=None, bio=None, 
                 gender=None, image_url=None, birth_place=None, occupations=None):
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
            'birth_date': self.birth_date,
            'death_date': self.death_date,
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
        self.people = {}  # Dictionary of Person objects, keyed by ID
        self.relations = []  # List of Relation objects
    
    def add_person(self, person):
        """Add a person to the family tree."""
        self.people[person.id] = person
    
    def get_person(self, person_id):
        """Get a person from the family tree by ID."""
        return self.people.get(person_id)
    
    def add_relation(self, source_id, target_id, relation_type):
        """Add a relation between two people."""
        # Check if the relation already exists
        for relation in self.relations:
            if (relation.source_id == source_id and 
                relation.target_id == target_id and 
                relation.relation_type == relation_type):
                return  # Relation already exists
        
        # Add new relation
        self.relations.append(Relation(source_id, target_id, relation_type))
        
        # For spouse and sibling relations, add the inverse relation as well
        # (These are bidirectional relationships)
        if relation_type in ['spouse', 'sibling']:
            # Check if inverse relation already exists
            for relation in self.relations:
                if (relation.source_id == target_id and 
                    relation.target_id == source_id and 
                    relation.relation_type == relation_type):
                    return  # Inverse relation already exists
            
            # Add inverse relation
            self.relations.append(Relation(target_id, source_id, relation_type))
    
    def get_relations_for_person(self, person_id):
        """Get all relations for a person."""
        relations = {
            'parents': [],
            'children': [],
            'spouses': [],
            'siblings': []
        }
        
        # Get relations where person is the target
        for relation in self.relations:
            if relation.target_id == person_id and relation.relation_type == 'parent':
                parent = self.get_person(relation.source_id)
                if parent:
                    relations['parents'].append(parent.to_dict())
            
            # Get relations where person is the source
            if relation.source_id == person_id:
                if relation.relation_type == 'parent':
                    child = self.get_person(relation.target_id)
                    if child:
                        relations['children'].append(child.to_dict())
                elif relation.relation_type == 'spouse':
                    spouse = self.get_person(relation.target_id)
                    if spouse:
                        relations['spouses'].append(spouse.to_dict())
                elif relation.relation_type == 'sibling':
                    sibling = self.get_person(relation.target_id)
                    if sibling:
                        relations['siblings'].append(sibling.to_dict())
        
        return relations
    
    def get_family_network(self, person_id, max_depth=2):
        """
        Get a network of family relationships centered on a person.
        
        Args:
            person_id (str): ID of the central person
            max_depth (int): Maximum depth of relationships to include
            
        Returns:
            dict: Network data suitable for D3.js visualization
        """
        # BFS to find all related people within max_depth
        queue = [(person_id, 0)]  # (person_id, depth)
        visited = set([person_id])
        related_people = []
        links = []
        
        while queue:
            current_id, depth = queue.pop(0)
            
            current_person = self.get_person(current_id)
            if not current_person:
                continue
                
            # Add current person to the result
            person_data = current_person.to_dict()
            person_data['depth'] = depth
            related_people.append(person_data)
            
            # Stop at max depth
            if depth >= max_depth:
                continue
            
            # Find all direct relations
            for relation in self.relations:
                if relation.source_id == current_id:
                    target_id = relation.target_id
                    if target_id not in visited:
                        visited.add(target_id)
                        queue.append((target_id, depth + 1))
                        
                    # Add link
                    links.append({
                        'source': current_id,
                        'target': target_id,
                        'type': relation.relation_type
                    })
                
                elif relation.target_id == current_id and relation.relation_type == 'parent':
                    source_id = relation.source_id
                    if source_id not in visited:
                        visited.add(source_id)
                        queue.append((source_id, depth + 1))
                    
                    # Add link (reversed for parent relations)
                    links.append({
                        'source': source_id,
                        'target': current_id,
                        'type': 'parent'
                    })
        
        return {
            'nodes': related_people,
            'links': links
        }

# Create a singleton instance of the family tree
family_tree_data = FamilyTree()
