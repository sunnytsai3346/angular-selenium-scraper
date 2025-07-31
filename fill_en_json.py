import json
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
        
    try:
        with open(status_data_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode {status_data_path}. Make sure it is a valid JSON file.")
        return {}

    return {item.get('name'): item.get('value') for item in status_data if item.get('name')}

def merge_json_data(en_json_path='context/EN.json', output_path='en_filled.json', status_lookup={}):
    """
    Reads data from en_json_path, merges it with data from status_lookup based on an exact name match,
    and writes the result to output_path.
    """
    try:
        with open(en_json_path, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {en_json_path} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode {en_json_path}. Make sure it is a valid JSON file.")
        return

    # Iterate through the English data and update the 'value' if a match is found
    for en_item in en_data:
        en_name = en_item.get('name')
        if en_name in status_lookup:
            en_item['value'] = status_lookup[en_name]
        elif 'value' not in en_item:
            en_item['value'] = None
        en_url = en_item.get('url')    
        if en_url:
            en_item['url'] = urljoin(BASE_URL, en_url)

    # Write the updated data to a new file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(en_data, f, indent=4)
        print(f"Successfully merged data and created {output_path}.")
    except IOError as e:
        print(f"Error writing to {output_path}: {e}")

def main():
    """
    Main function to run the script.
    """
    status_lookup = create_status_lookup()
    if status_lookup:
        merge_json_data(status_lookup=status_lookup)

if __name__ == "__main__":
    main()
