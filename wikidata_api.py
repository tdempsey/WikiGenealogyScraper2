import requests
import logging
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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
        # Calculate offset based on page number
        offset = (page - 1) * limit
        
        # Search for entities that are instances of human (Q5)
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': 'en',
            'search': query,
            'type': 'item',
            'limit': limit,
            'continue': offset
        }
        
        response = requests.get(WIKIDATA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Post-process search results to filter for humans
        for item in data.get('search', []):
            entity_id = item.get('id')
            
            # Basic information
            person = {
                'id': entity_id,
                'name': item.get('label', 'Unknown'),
                'description': item.get('description', '')
            }
            
            results.append(person)
        
        # The structure of Wikidata API response sometimes varies
        # The 'total' might be in 'search-continue' or directly in 'searchinfo'
        total_results = len(results)
        search_continue = data.get('search-continue')
        if search_continue and isinstance(search_continue, dict):
            total_results = search_continue.get('total', total_results)
        elif data.get('searchinfo') and isinstance(data.get('searchinfo'), dict):
            total_results = data.get('searchinfo').get('totalhits', total_results)
            
        return {
            'results': results,
            'total': total_results,
            'page': page,
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"Error searching Wikidata: {str(e)}")
        raise

def get_person_details(entity_id):
    """
    Get detailed information about a person from Wikidata.
    
    Args:
        entity_id (str): The Wikidata entity ID (e.g., Q5)
        
    Returns:
        dict: Person details
    """
    try:
        # Get entity data from Wikidata API
        params = {
            'action': 'wbgetentities',
            'format': 'json',
            'ids': entity_id,
            'languages': 'en',
            'props': 'labels|descriptions|claims|sitelinks'
        }
        
        response = requests.get(WIKIDATA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract entity data
        entity_data = data.get('entities', {}).get(entity_id, {})
        
        if not entity_data:
            return {'error': 'Person not found'}
        
        # Get basic information
        labels = entity_data.get('labels', {})
        descriptions = entity_data.get('descriptions', {})
        claims = entity_data.get('claims', {})
        
        # Extract commonly needed data
        person = {
            'id': entity_id,
            'name': labels.get('en', {}).get('value', 'Unknown'),
            'description': descriptions.get('en', {}).get('value', '')
        }
        
        # Extract birth date (P569)
        if 'P569' in claims:
            try:
                time_value = claims['P569'][0]['mainsnak']['datavalue']['value']['time']
                # Format: +YYYY-MM-DDT00:00:00Z
                # Remove the + and the time part
                if time_value.startswith('+'):
                    time_value = time_value[1:]
                person['birth_date'] = time_value.split('T')[0]
            except (KeyError, IndexError):
                person['birth_date'] = None
        
        # Extract death date (P570)
        if 'P570' in claims:
            try:
                time_value = claims['P570'][0]['mainsnak']['datavalue']['value']['time']
                if time_value.startswith('+'):
                    time_value = time_value[1:]
                person['death_date'] = time_value.split('T')[0]
            except (KeyError, IndexError):
                person['death_date'] = None
        
        # Extract gender (P21)
        if 'P21' in claims:
            try:
                gender_id = claims['P21'][0]['mainsnak']['datavalue']['value']['id']
                if gender_id == 'Q6581097':
                    person['gender'] = 'male'
                elif gender_id == 'Q6581072':
                    person['gender'] = 'female'
                else:
                    person['gender'] = 'other'
            except (KeyError, IndexError):
                person['gender'] = None
        
        # Extract image (P18)
        if 'P18' in claims:
            try:
                image_filename = claims['P18'][0]['mainsnak']['datavalue']['value']
                # Convert filename to Wikimedia Commons URL
                image_filename = image_filename.replace(' ', '_')
                # Calculate MD5 hash prefix for Commons URL structure
                import hashlib
                md5_hash = hashlib.md5(image_filename.encode('utf-8')).hexdigest()
                person['image_url'] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_filename}"
            except (KeyError, IndexError):
                person['image_url'] = None
        
        # Extract place of birth (P19)
        if 'P19' in claims:
            try:
                birth_place_id = claims['P19'][0]['mainsnak']['datavalue']['value']['id']
                place_params = {
                    'action': 'wbgetentities',
                    'format': 'json',
                    'ids': birth_place_id,
                    'languages': 'en',
                    'props': 'labels'
                }
                place_response = requests.get(WIKIDATA_API_URL, params=place_params)
                place_data = place_response.json()
                person['birth_place'] = place_data.get('entities', {}).get(birth_place_id, {}).get('labels', {}).get('en', {}).get('value')
            except (KeyError, IndexError, Exception):
                person['birth_place'] = None
        
        # Extract occupations (P106)
        if 'P106' in claims:
            try:
                occupation_ids = [claim['mainsnak']['datavalue']['value']['id'] for claim in claims['P106'] if 'datavalue' in claim['mainsnak']]
                occupations = []
                
                if occupation_ids:
                    # Get occupation labels in batches
                    occ_params = {
                        'action': 'wbgetentities',
                        'format': 'json',
                        'ids': '|'.join(occupation_ids[:50]),  # Limit to 50 IDs per request
                        'languages': 'en',
                        'props': 'labels'
                    }
                    occ_response = requests.get(WIKIDATA_API_URL, params=occ_params)
                    occ_data = occ_response.json()
                    
                    for occ_id in occupation_ids:
                        occ_label = occ_data.get('entities', {}).get(occ_id, {}).get('labels', {}).get('en', {}).get('value')
                        if occ_label:
                            occupations.append(occ_label)
                
                person['occupations'] = occupations
            except (KeyError, Exception):
                person['occupations'] = []
        
        return person
    
    except Exception as e:
        logger.error(f"Error getting person details from Wikidata: {str(e)}")
        raise

def get_family_relations(entity_id):
    """
    Get family relations for a person from Wikidata.
    
    Args:
        entity_id (str): The Wikidata entity ID (e.g., Q5)
        
    Returns:
        dict: Family relations categorized by type
    """
    try:
        # Use SPARQL to query for family relations
        # Define relationship property IDs
        parent_props = ['P22', 'P25']  # father, mother
        child_props = ['P40']  # child
        spouse_props = ['P26']  # spouse
        sibling_props = ['P3373']  # sibling
        
        # Create SPARQL query for all relations
        # Note: Must use 'wdt:' prefix for properties in the query (direct statements)
        query = f"""
        SELECT DISTINCT ?relation ?relationLabel ?relationType ?relationBirth ?relationDeath ?relationGender ?relationDescription WHERE {{
          # Parents
          {{
            VALUES ?relationType {{ "parent" }}
            # Father
            {{ wd:{entity_id} wdt:P22 ?relation }}
            # Mother
            UNION {{ wd:{entity_id} wdt:P25 ?relation }}
          }} UNION {{
            # Children
            VALUES ?relationType {{ "child" }}
            ?relation wdt:P40 wd:{entity_id} .
          }} UNION {{
            # Spouses
            VALUES ?relationType {{ "spouse" }}
            {{ wd:{entity_id} wdt:P26 ?relation }} UNION {{ ?relation wdt:P26 wd:{entity_id} }}
          }} UNION {{
            # Siblings
            VALUES ?relationType {{ "sibling" }}
            {{ wd:{entity_id} wdt:P3373 ?relation }} UNION {{ ?relation wdt:P3373 wd:{entity_id} }}
          }}
          OPTIONAL {{ ?relation wdt:P569 ?relationBirth . }}
          OPTIONAL {{ ?relation wdt:P570 ?relationDeath . }}
          OPTIONAL {{ ?relation wdt:P21 ?genderEntity .
                     ?genderEntity rdfs:label ?relationGender . 
                     FILTER(LANG(?relationGender) = "en") }}
          OPTIONAL {{ ?relation schema:description ?relationDescription . 
                     FILTER(LANG(?relationDescription) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        """
        
        # Make the SPARQL request
        headers = {
            'Accept': 'application/sparql-results+json',
            'User-Agent': 'WikidataGenealogyApp/1.0'
        }
        
        params = {
            'query': query,
            'format': 'json'
        }
        
        response = requests.get(WIKIDATA_SPARQL_URL, headers=headers, params=params)
        response.raise_for_status()
        results = response.json()
        
        # Process results
        relations = {
            'parents': [],
            'children': [],
            'spouses': [],
            'siblings': []
        }
        
        processed_ids = set()  # To avoid duplicates
        
        for binding in results.get('results', {}).get('bindings', []):
            relation_uri = binding.get('relation', {}).get('value', '')
            if not relation_uri:
                continue
                
            # Extract Q-ID from URI (e.g., http://www.wikidata.org/entity/Q123 -> Q123)
            relation_id = relation_uri.split('/')[-1]
            
            # Skip if we've already processed this relation
            relation_type = binding.get('relationType', {}).get('value')
            relation_key = f"{relation_id}_{relation_type}"
            if relation_key in processed_ids:
                continue
            processed_ids.add(relation_key)
            
            # Create relation object
            relation = {
                'id': relation_id,
                'name': binding.get('relationLabel', {}).get('value', 'Unknown'),
                'type': relation_type,
            }
            
            # Add optional attributes if available
            if 'relationBirth' in binding:
                birth_date = binding['relationBirth']['value']
                if birth_date.startswith('+'):
                    birth_date = birth_date[1:]
                relation['birth_date'] = birth_date.split('T')[0]
                
            if 'relationDeath' in binding:
                death_date = binding['relationDeath']['value']
                if death_date.startswith('+'):
                    death_date = death_date[1:]
                relation['death_date'] = death_date.split('T')[0]
                
            if 'relationGender' in binding:
                relation['gender'] = binding['relationGender']['value'].lower()
                
            if 'relationDescription' in binding:
                relation['description'] = binding['relationDescription']['value']
            
            # Add to appropriate category
            if relation_type == 'parent':
                relations['parents'].append(relation)
            elif relation_type == 'child':
                relations['children'].append(relation)
            elif relation_type == 'spouse':
                relations['spouses'].append(relation)
            elif relation_type == 'sibling':
                relations['siblings'].append(relation)
        
        return relations
        
    except Exception as e:
        logger.error(f"Error getting family relations from Wikidata: {str(e)}")
        raise
