import json
import xml.etree.ElementTree as ET
import os
from urllib.parse import urljoin

# The base URL for constructing the full URL
BASE_URL = "http://192.168.230.169/"

def create_status_lookup(status_data_path='status_data.json'):
    """
    Reads the status_data.json file and creates a dictionary
    mapping names to values for quick lookup.
    """
    if not os.path.exists(status_data_path):
        print(f"Error: {status_data_path} not found.")
        return {}
        
    with open(status_data_path, 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    status_lookup = {item.get('name'): item.get('value') for item in status_data}
    return status_lookup

def process_en_ts(ts_path='context/EN.ts', status_lookup={}):
    """
    Parses the EN.ts file and processes the messages.
    """
    if not os.path.exists(ts_path):
        print(f"Error: {ts_path} not found.")
        return []

    tree = ET.parse(ts_path)
    root = tree.getroot()
    
    processed_data = []

    for message in root.findall('.//message'):
        source_tag = message.find('source')
        extracomment_tag = message.find('extracomment')

        if source_tag is not None and extracomment_tag is not None:
            name = source_tag.text.strip() if source_tag.text else ""
            extracomment = extracomment_tag.text.strip() if extracomment_tag.text else ""
            
            # Default values
            user_level = None
            url = None

            # Parse extracomment
            if extracomment:
                parts = extracomment.split('-')
                if len(parts) > 1:
                    user_level_str = parts[0]
                    if user_level_str.isdigit():
                        user_level = user_level_str
                    
                    url_path = parts[1]
                    if url_path and url_path.strip() != '/':
                        url = urljoin(BASE_URL, url_path)

            # Get value from status_lookup
            value = status_lookup.get(name)

            processed_data.append({
                "name": name,
                "url": url,
                "userLevel": user_level,
                "extracomment": extracomment,
                "value": value
            })
            
    return processed_data

def main():
    """
    Main function to run the script.
    """
    status_lookup = create_status_lookup()
    processed_data = process_en_ts(status_lookup=status_lookup)
    
    output_path = 'en_ts_processed.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=4)
        
    print(f"Processing complete. Output written to {output_path}")

if __name__ == "__main__":
    main()
