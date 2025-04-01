"""
Wikidata API module for retrieving genealogy data.

This module provides functions to:
1. Search for people in Wikidata
2. Get detailed information about a person
3. Get family relations for a person
"""
import requests
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Wikidata API endpoints
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

def search_person(query, page=1, limit=10):
    """
    Search for people in Wikidata based on a query string.
    
    Args:
        query (str): The search query
        page (int): Page number for pagination
        limit (int): Number of results per page
        
    Returns:
        dict: Search results with pagination information
    """
    try:
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Parameters for search
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "type": "item",
            "search": query,
            "limit": limit,
            "continue": offset
        }
        
        # Make the request
        response = requests.get(WIKIDATA_API_URL, params=params)
        data = response.json()
        
        # Check if search was successful
        if 'search' not in data:
            logger.warning(f"Search failed for query: {query}")
            return {
                "results": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "pages": 0
            }
            
        # Get results and format them
        results = []
        for item in data['search']:
            result = {
                "id": item['id'],
                "label": item.get('label', 'Unknown'),
                "description": item.get('description', '')
            }
            results.append(result)
            
        # Calculate pagination info
        search_continue = data.get('search-continue', offset + len(results))
        total_results = search_continue + (0 if len(results) < limit else 1)  # Estimate total if more results exist
        total_pages = (total_results + limit - 1) // limit
        
        # Return formatted results
        return {
            "results": results,
            "total": total_results,
            "page": page,
            "limit": limit,
            "pages": total_pages
        }
        
    except Exception as e:
        logger.error(f"Error searching Wikidata: {str(e)}")
        return {
            "results": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "pages": 0,
            "error": str(e)
        }

def get_person_details(entity_id):
    """
    Get detailed information about a person from Wikidata.
    
    Args:
        entity_id (str): The Wikidata entity ID (e.g., Q5)
        
    Returns:
        dict: Person details
    """
    try:
        # Parameters for getting entity data
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": entity_id,
            "languages": "en"
        }
        
        # Make the request
        response = requests.get(WIKIDATA_API_URL, params=params)
        data = response.json()
        
        # Check if entity was found
        if 'entities' not in data or entity_id not in data['entities']:
            logger.warning(f"Entity not found: {entity_id}")
            return None
            
        entity = data['entities'][entity_id]
        
        # Property IDs for person data
        PROP_INSTANCE_OF = "P31"
        PROP_HUMAN = "Q5"
        PROP_NAME = "labels"
        PROP_DESCRIPTION = "descriptions"
        PROP_BIRTH_DATE = "P569"
        PROP_DEATH_DATE = "P570"
        PROP_GENDER = "P21"
        PROP_IMAGE = "P18"
        PROP_BIRTH_PLACE = "P19"
        PROP_OCCUPATION = "P106"
        
        # Check if entity is a person
        is_human = False
        if PROP_INSTANCE_OF in entity.get('claims', {}):
            for claim in entity['claims'][PROP_INSTANCE_OF]:
                if claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == PROP_HUMAN:
                    is_human = True
                    break
        
        if not is_human:
            logger.warning(f"Entity is not a human: {entity_id}")
            # Continue anyway, might be a person even if not explicitly marked as such
        
        # Extract person data
        person = {
            "id": entity_id,
            "name": entity.get(PROP_NAME, {}).get('en', {}).get('value', 'Unknown'),
            "bio": entity.get(PROP_DESCRIPTION, {}).get('en', {}).get('value', ''),
            "birth_date": None,
            "death_date": None,
            "gender": None,
            "image_url": None,
            "birth_place": None,
            "occupations": []
        }
        
        # Extract claims data
        claims = entity.get('claims', {})
        
        # Birth date
        if PROP_BIRTH_DATE in claims:
            birth_date = claims[PROP_BIRTH_DATE][0].get('mainsnak', {}).get('datavalue', {}).get('value', {})
            if birth_date and 'time' in birth_date:
                # Format: +1936-10-15T00:00:00Z
                time_str = birth_date['time']
                # Remove + or - at the beginning and Z at the end
                time_str = time_str[1:] if time_str.startswith('+') else time_str
                time_str = time_str.replace('Z', '')
                try:
                    person['birth_date'] = time_str
                except ValueError:
                    logger.warning(f"Cannot parse birth date: {time_str}")
        
        # Death date
        if PROP_DEATH_DATE in claims:
            death_date = claims[PROP_DEATH_DATE][0].get('mainsnak', {}).get('datavalue', {}).get('value', {})
            if death_date and 'time' in death_date:
                # Format: +1936-10-15T00:00:00Z
                time_str = death_date['time']
                # Remove + or - at the beginning and Z at the end
                time_str = time_str[1:] if time_str.startswith('+') else time_str
                time_str = time_str.replace('Z', '')
                try:
                    person['death_date'] = time_str
                except ValueError:
                    logger.warning(f"Cannot parse death date: {time_str}")
        
        # Gender
        if PROP_GENDER in claims:
            gender_id = claims[PROP_GENDER][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
            if gender_id:
                # Q6581097: male, Q6581072: female
                if gender_id == 'Q6581097':
                    person['gender'] = 'male'
                elif gender_id == 'Q6581072':
                    person['gender'] = 'female'
                else:
                    person['gender'] = 'other'
        
        # Image
        if PROP_IMAGE in claims:
            image_filename = claims[PROP_IMAGE][0].get('mainsnak', {}).get('datavalue', {}).get('value')
            if image_filename:
                # Convert filename to URL using Wikimedia Commons API
                image_filename = image_filename.replace(' ', '_')
                
                # Create an MD5 hash and use it to construct the URL
                import hashlib
                md5_hash = hashlib.md5(image_filename.encode('utf-8')).hexdigest()
                
                # Format: https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Example.jpg/200px-Example.jpg
                prefix = md5_hash[0]
                prefix2 = md5_hash[0:2]
                image_url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{prefix}/{prefix2}/{image_filename}/200px-{image_filename}"
                person['image_url'] = image_url
        
        # Birth place
        if PROP_BIRTH_PLACE in claims:
            birth_place_id = claims[PROP_BIRTH_PLACE][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
            if birth_place_id:
                # Get place name
                place_params = {
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": birth_place_id,
                    "languages": "en"
                }
                
                place_response = requests.get(WIKIDATA_API_URL, params=place_params)
                place_data = place_response.json()
                
                if 'entities' in place_data and birth_place_id in place_data['entities']:
                    place_entity = place_data['entities'][birth_place_id]
                    person['birth_place'] = place_entity.get('labels', {}).get('en', {}).get('value')
        
        # Occupations
        if PROP_OCCUPATION in claims:
            for occupation_claim in claims[PROP_OCCUPATION]:
                occupation_id = occupation_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
                if occupation_id:
                    # Get occupation name
                    occupation_params = {
                        "action": "wbgetentities",
                        "format": "json",
                        "ids": occupation_id,
                        "languages": "en"
                    }
                    
                    occupation_response = requests.get(WIKIDATA_API_URL, params=occupation_params)
                    occupation_data = occupation_response.json()
                    
                    if 'entities' in occupation_data and occupation_id in occupation_data['entities']:
                        occupation_entity = occupation_data['entities'][occupation_id]
                        occupation_name = occupation_entity.get('labels', {}).get('en', {}).get('value')
                        if occupation_name and occupation_name not in person['occupations']:
                            person['occupations'].append(occupation_name)
        
        return person
        
    except Exception as e:
        logger.error(f"Error getting person details: {str(e)}")
        return None

def get_family_relations(entity_id):
    """
    Get family relations for a person from Wikidata.
    
    Args:
        entity_id (str): The Wikidata entity ID (e.g., Q5)
        
    Returns:
        dict: Family relations categorized by type
    """
    try:
        # Initialize result
        family_relations = {
            "parents": [],
            "children": [],
            "spouses": [],
            "siblings": []
        }
        
        # Helper functions
        def execute_wikidata_query(query):
            """Execute a SPARQL query on Wikidata and return results."""
            params = {
                "format": "json",
                "query": query
            }
            headers = {
                "Accept": "application/sparql-results+json",
                "User-Agent": "GenealogyResearchTool/1.0"
            }
            
            response = requests.get(WIKIDATA_SPARQL_URL, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"SPARQL query failed with status {response.status_code}: {response.text}")
                return None
                
            return response.json()
        
        def process_binding(binding, relation_type):
            """Process a SPARQL binding to extract relation data."""
            if 'person' not in binding or 'personLabel' not in binding:
                return None
                
            person_uri = binding['person']['value']
            person_label = binding.get('personLabel', {}).get('value', 'Unknown')
            
            # Extract entity ID from URI (format: http://www.wikidata.org/entity/Q123)
            entity_id = person_uri.split('/')[-1]
            
            # Extract birth and death dates if available
            birth_date = binding.get('birth', {}).get('value') if 'birth' in binding else None
            death_date = binding.get('death', {}).get('value') if 'death' in binding else None
            image_url = binding.get('image', {}).get('value') if 'image' in binding else None
            
            # Format dates if present
            if birth_date:
                try:
                    birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00')).isoformat()
                except ValueError:
                    birth_date = None
                    
            if death_date:
                try:
                    death_date = datetime.fromisoformat(death_date.replace('Z', '+00:00')).isoformat()
                except ValueError:
                    death_date = None
            
            return {
                "id": entity_id,
                "name": person_label,
                "birth_date": birth_date,
                "death_date": death_date,
                "image_url": image_url
            }
        
        # --- Parents ---
        parents_query = f"""
        SELECT ?person ?personLabel ?birth ?death ?image WHERE {{
          wd:{entity_id} wdt:P22|wdt:P25 ?person .
          OPTIONAL {{ ?person wdt:P569 ?birth . }}
          OPTIONAL {{ ?person wdt:P570 ?death . }}
          OPTIONAL {{ ?person wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        """
        
        parents_data = execute_wikidata_query(parents_query)
        if parents_data and 'results' in parents_data and 'bindings' in parents_data['results']:
            for binding in parents_data['results']['bindings']:
                parent = process_binding(binding, 'parent')
                if parent:
                    family_relations["parents"].append(parent)
        
        # --- Children ---
        children_query = f"""
        SELECT ?person ?personLabel ?birth ?death ?image WHERE {{
          ?person wdt:P22|wdt:P25 wd:{entity_id} .
          OPTIONAL {{ ?person wdt:P569 ?birth . }}
          OPTIONAL {{ ?person wdt:P570 ?death . }}
          OPTIONAL {{ ?person wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        """
        
        children_data = execute_wikidata_query(children_query)
        if children_data and 'results' in children_data and 'bindings' in children_data['results']:
            for binding in children_data['results']['bindings']:
                child = process_binding(binding, 'child')
                if child:
                    family_relations["children"].append(child)
        
        # --- Spouses ---
        spouses_query = f"""
        SELECT ?person ?personLabel ?birth ?death ?image WHERE {{
          wd:{entity_id} wdt:P26 ?person .
          OPTIONAL {{ ?person wdt:P569 ?birth . }}
          OPTIONAL {{ ?person wdt:P570 ?death . }}
          OPTIONAL {{ ?person wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        """
        
        spouses_data = execute_wikidata_query(spouses_query)
        if spouses_data and 'results' in spouses_data and 'bindings' in spouses_data['results']:
            for binding in spouses_data['results']['bindings']:
                spouse = process_binding(binding, 'spouse')
                if spouse:
                    family_relations["spouses"].append(spouse)
        
        # --- Siblings ---
        siblings_query = f"""
        SELECT ?person ?personLabel ?birth ?death ?image WHERE {{
          ?parent wdt:P22|wdt:P25 wd:{entity_id} .
          ?parent wdt:P22|wdt:P25 ?person .
          FILTER(?person != wd:{entity_id})
          OPTIONAL {{ ?person wdt:P569 ?birth . }}
          OPTIONAL {{ ?person wdt:P570 ?death . }}
          OPTIONAL {{ ?person wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        """
        
        siblings_data = execute_wikidata_query(siblings_query)
        if siblings_data and 'results' in siblings_data and 'bindings' in siblings_data['results']:
            for binding in siblings_data['results']['bindings']:
                sibling = process_binding(binding, 'sibling')
                if sibling:
                    family_relations["siblings"].append(sibling)
        
        return family_relations
        
    except Exception as e:
        logger.error(f"Error getting family relations: {str(e)}")
        return {
            "parents": [],
            "children": [],
            "spouses": [],
            "siblings": []
        }