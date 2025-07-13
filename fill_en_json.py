import json

def merge_json_data():
    """
    Reads data from EN.json and status_data.json, merges them based on a partial,
    case-insensitive match between 'name' and 'label' fields, and writes the
    result to en_filled.json.
    """
    try:
        with open('C:\\Home\\workplace\\python\\angular-selenium-scraper\\EN.json', 'r', encoding='utf-8') as f:
            en_data = json.load(f)
    except FileNotFoundError:
        print("Error: EN.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode EN.json. Make sure it is a valid JSON file.")
        return

    try:
        with open('C:\\Home\\workplace\\python\\angular-selenium-scraper\\status_data.json', 'r', encoding='utf-8') as f:
            status_data = json.load(f)
    except FileNotFoundError:
        print("Error: status_data.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode status_data.json. Make sure it is a valid JSON file.")
        return

    # Iterate through the English data and add the 'value' if a partial match is found
    for en_item in en_data:
        en_name = en_item.get('name')
        matched_value = None

        if en_name:
            # Find the best (longest) matching label from status_data
            best_match_len = 0
            for status_item in status_data:
                status_label = status_item.get('label')
                if status_label and status_label.lower() in en_name.lower():
                    if len(status_label) > best_match_len:
                        best_match_len = len(status_label)
                        matched_value = status_item.get('value')

        en_item['value'] = matched_value

    # Write the updated data to a new file
    try:
        with open('C:\\Home\\workplace\\python\\angular-selenium-scraper\\en_filled.json', 'w', encoding='utf-8') as f:
            json.dump(en_data, f, indent=4)
        print("Successfully merged data and created en_filled.json.")
    except IOError as e:
        print(f"Error writing to en_filled.json: {e}")

if __name__ == "__main__":
    merge_json_data()