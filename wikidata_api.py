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
        # Helper method to execute SPARQL query and parse results
        def execute_wikidata_query(query):
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
            return response.json().get('results', {}).get('bindings', [])
            
        # Helper method to process a binding into a relation object
        def process_binding(binding, relation_type):
            relation_uri = binding.get('relation', {}).get('value', '')
            if not relation_uri:
                return None
                
            # Extract Q-ID from URI (e.g., http://www.wikidata.org/entity/Q123 -> Q123)
            relation_id = relation_uri.split('/')[-1]
            
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
                
            return relation
            
        # Create simpler individual queries for each relationship type
        
        # Parents query (mother + father)
        parents_query = f"""
        SELECT ?relation ?relationLabel ?relationBirth ?relationDeath ?relationGender ?relationDescription WHERE {{
          # Parents
          {{ wd:{entity_id} wdt:P22 ?relation }} UNION {{ wd:{entity_id} wdt:P25 ?relation }}
          
          # Get additional details about the relation
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
        
        # Children query
        children_query = f"""
        SELECT ?relation ?relationLabel ?relationBirth ?relationDeath ?relationGender ?relationDescription WHERE {{
          # Children
          ?relation wdt:P40 wd:{entity_id} .
          
          # Get additional details about the relation
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
        
        # Spouses query
        spouses_query = f"""
        SELECT ?relation ?relationLabel ?relationBirth ?relationDeath ?relationGender ?relationDescription WHERE {{
          # Spouses (bi-directional)
          {{ wd:{entity_id} wdt:P26 ?relation }} UNION {{ ?relation wdt:P26 wd:{entity_id} }}
          
          # Get additional details about the relation
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
        
        # Siblings query
        siblings_query = f"""
        SELECT ?relation ?relationLabel ?relationBirth ?relationDeath ?relationGender ?relationDescription WHERE {{
          # Siblings (bi-directional)
          {{ wd:{entity_id} wdt:P3373 ?relation }} UNION {{ ?relation wdt:P3373 wd:{entity_id} }}
          
          # Get additional details about the relation
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
        
        # Execute the queries separately and combine results
        parents_results = execute_wikidata_query(parents_query)
        children_results = execute_wikidata_query(children_query)
        spouses_results = execute_wikidata_query(spouses_query)
        siblings_results = execute_wikidata_query(siblings_query)
        
        # Initialize the result dictionary
        relations = {
            'parents': [],
            'children': [],
            'spouses': [],
            'siblings': []
        }
        
        # Process parents
        seen_parent_ids = set()
        for binding in parents_results:
            relation = process_binding(binding, 'parent')
            if relation and relation['id'] not in seen_parent_ids:
                seen_parent_ids.add(relation['id'])
                relations['parents'].append(relation)
        
        # Process children
        seen_child_ids = set()
        for binding in children_results:
            relation = process_binding(binding, 'child')
            if relation and relation['id'] not in seen_child_ids:
                seen_child_ids.add(relation['id'])
                relations['children'].append(relation)
        
        # Process spouses
        seen_spouse_ids = set()
        for binding in spouses_results:
            relation = process_binding(binding, 'spouse')
            if relation and relation['id'] not in seen_spouse_ids:
                seen_spouse_ids.add(relation['id'])
                relations['spouses'].append(relation)
        
        # Process siblings
        seen_sibling_ids = set()
        for binding in siblings_results:
            relation = process_binding(binding, 'sibling')
            if relation and relation['id'] not in seen_sibling_ids:
                seen_sibling_ids.add(relation['id'])
                relations['siblings'].append(relation)
        
        return relations
        
    except Exception as e:
        logger.error(f"Error getting family relations from Wikidata: {str(e)}")
        raise
