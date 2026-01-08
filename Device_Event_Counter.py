import requests
import csv
import time
import json

# Your FDA API key goes here (get one free at https://open.fda.gov/apis/authentication/)
# Leave blank to use default rate limits
API_KEY = ""

def get_k_numbers_from_recall_api(recall_number):
    """
    Given a recall number, looks up the associated 510(k) numbers from the FDA API.
    """
    base_url = "https://api.fda.gov/device/recall.json"
    k_numbers = []
    
    params = {
        'search': f'product_res_number:"{recall_number}"',
        'limit': 1
    }
    
    if API_KEY:
        params['api_key'] = API_KEY
    
    try:
        # Build the full URL for display
        if API_KEY:
            full_url = f"{base_url}?search={params['search']}&limit={params['limit']}&api_key={API_KEY}"
        else:
            full_url = f"{base_url}?search={params['search']}&limit={params['limit']}"
        print(f"Attempting API call: {full_url}")
        print(f"API Key being used: {'Yes' if API_KEY else 'No'}")
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        if not results:
            print(f"No recall details found for recall number {recall_number}.")
            return []
            
        k_numbers = results[0].get('k_numbers', [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching recall details for {recall_number}: {e}")
        return None
    except KeyError as e:
        print(f"Error parsing JSON: The 'k_numbers' key was not found in the response for {recall_number}. Error: {e}")
        return None
    
    return k_numbers

def get_events_by_k_numbers(k_numbers):
    """
    Queries OpenFDA for adverse events linked to the given 510(k) numbers.
    Handles pagination since the API caps results at 1000 per request.
    """
    if not k_numbers:
        return []
    
    base_url = "https://api.fda.gov/device/event.json"
    all_events = []
    
    print(f"Fetching events for {len(k_numbers)} 510(k) numbers...")
    
    for i, k_number in enumerate(k_numbers):
        print(f"\nProcessing 510(k) number {i+1}/{len(k_numbers)}: {k_number}")
        
        k_number_events = get_events_for_single_k_number(k_number)
        
        if k_number_events is None:
            print(f"Error occurred while fetching events for {k_number}")
            continue
        elif k_number_events:
            print(f"Found {len(k_number_events)} events for {k_number}")
            all_events.extend(k_number_events)
        else:
            print(f"No events found for {k_number}")
        if i < len(k_numbers) - 1:
            time.sleep(1)  # be nice to the API
    
    print(f"\nTotal events collected: {len(all_events)}")
    return all_events

def get_events_for_single_k_number(k_number):
    """
    Fetches all device events for one 510(k) number, paginating through results.
    """
    base_url = "https://api.fda.gov/device/event.json"
    events = []
    skip = 0
    limit = 1000  # API max
    
    while True:
        try:
            params = {
                'search': f'pma_pmn_number:{k_number}',
                'limit': limit,
                'skip': skip
            }
            
            if API_KEY:
                params['api_key'] = API_KEY
            if API_KEY:
                full_url = f"{base_url}?search=pma_pmn_number:{k_number}&limit={limit}&skip={skip}&api_key={API_KEY}"
            else:
                full_url = f"{base_url}?search=pma_pmn_number:{k_number}&limit={limit}&skip={skip}"
            
            print(f"  API call: {full_url}")
            print(f"  API Key being used: {'Yes' if API_KEY else 'No'}")
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            if not results:
                break
            
            events.extend(results)
            print(f"  Retrieved {len(results)} events (total so far: {len(events)})")
            
            # Check if we got everything
            total_available = data.get('meta', {}).get('results', {}).get('total', 0)
            if len(events) >= total_available:
                print(f"  Retrieved all {total_available} available events for {k_number}")
                break
            
            if len(results) < limit:
                print(f"  Retrieved final batch of {len(results)} events for {k_number}")
                break
            
            skip += limit
            time.sleep(0.5)  # rate limiting
            
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching events for {k_number} (skip={skip}): {e}")
            return None
        except Exception as e:
            print(f"  Unexpected error for {k_number}: {e}")
            return None
    
    return events

def flatten_json(y):
    """
    Flattens nested JSON into a single-level dict so we can write it to CSV.
    """
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

def filter_events_by_date_range(flattened_events, start_date=None, end_date=None):
    """
    Keeps only events where date_received falls within the specified range.
    Dates should be strings in yyyymmdd format.
    """
    if not start_date and not end_date:
        return flattened_events
    
    filtered_events = []
    
    for event in flattened_events:
        # Find the date_received field (name varies after flattening)
        date_received = None
        for key in event:
            if key.endswith('date_received'):
                date_received = event[key]
                break
        
        if not date_received:
            continue
        
        date_str = str(date_received)
        
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
            
        filtered_events.append(event)
    
    return filtered_events

def generate_csv_from_events(events, filename, start_date=None, end_date=None):
    """
    Flattens the event data, applies date filtering if specified, and writes to CSV.
    """
    if not events:
        print("No events to write to CSV.")
        return
        
    flattened_events = [flatten_json(event) for event in events]
    
    if start_date or end_date:
        original_count = len(flattened_events)
        flattened_events = filter_events_by_date_range(flattened_events, start_date, end_date)
        print(f"Filtered from {original_count} to {len(flattened_events)} events based on date range.")
        
        if not flattened_events:
            print("No events remain after date filtering.")
            return
    
    fieldnames = set()
    for event in flattened_events:
        fieldnames.update(event.keys())
    
    fieldnames = sorted(list(fieldnames))
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_events)
        print(f"Successfully created {filename} with {len(flattened_events)} events.")
    except IOError as e:
        print(f"Error writing to CSV file {filename}: {e}")

def main():
    """
    Interactive menu for searching OpenFDA by recall number or K number.
    """
    print("\nDevice Event Counter - OpenFDA Medical Device Event Search Tool")
    print("----------------------------------------------------")
    print("1. Search by recall number")
    print("2. Search directly by K number")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        recall_number = input("Enter the FDA recall number (e.g., 'Z-1234-2023'): ").strip()
        if not recall_number:
            print("Recall number cannot be empty.")
            return
            
        filename = f"fda_events_for_{recall_number}.csv"
        
        date_filter = input("\nIf you'd like to filter by date received, enter date range (yyyymmdd-yyyymmdd). Otherwise press enter: ").strip()
        
        start_date, end_date, filename = process_date_filter(date_filter, filename)
        if start_date is None and end_date is None and date_filter:
            return
            
        print(f"Searching for recall details for recall number: {recall_number}...")
        k_numbers = get_k_numbers_from_recall_api(recall_number)
            
        if not k_numbers:
            print(f"No 510(k) numbers found for recall number {recall_number}.")
            return
            
        print(f"Found 510(k) numbers: {k_numbers}")
        
        print("Fetching device events for these 510(k) numbers...")
        events = get_events_by_k_numbers(k_numbers)
        
    elif choice == "2":
        k_number = input("Enter the K number (e.g., 'K123456'): ").strip()
        if not k_number:
            print("K number cannot be empty.")
            return
        
        # Basic format check
        if not (k_number.upper().startswith('K') and k_number[1:].isdigit()):
            print("Warning: K number format might be incorrect. Should be K followed by digits.")
            proceed = input("Do you want to continue anyway? (y/n): ").strip().lower()
            if proceed != 'y':
                return
                
        k_number = k_number.upper()
        filename = f"fda_events_for_{k_number}.csv"
        
        date_filter = input("\nIf you'd like to filter by date received, enter date range (yyyymmdd-yyyymmdd). Otherwise press enter: ").strip()
        
        start_date, end_date, filename = process_date_filter(date_filter, filename)
        if start_date is None and end_date is None and date_filter:
            return
            
        print(f"Fetching device events for K number: {k_number}...")
        events = get_events_by_k_numbers([k_number])
        
    else:
        print("Invalid choice. Please run the program again and select 1 or 2.")
        return
    
    if events is None:
        return
    
    if not events:
        print("No events found associated with the provided number(s).")
        return
        
    generate_csv_from_events(events, filename, start_date, end_date)

def process_date_filter(date_filter, filename):
    """
    Parses the date range input. Accepts yyyymmdd-yyyymmdd or just yyyy-yyyy.
    """
    start_date = None
    end_date = None
    
    if date_filter:
        try:
            date_parts = date_filter.split('-')
            if len(date_parts) != 2:
                raise ValueError("Date range must be in format yyyymmdd-yyyymmdd or yyyy-yyyy")
                
            start_date, end_date = date_parts
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # Year-only shorthand: 2020-2023 becomes 20200101-20231231
            if len(start_date) == 4 and len(end_date) == 4 and start_date.isdigit() and end_date.isdigit():
                start_date = f"{start_date}0101"
                end_date = f"{end_date}1231"
                print(f"Interpreted year range as {start_date} to {end_date}")
            elif len(start_date) != 8 or len(end_date) != 8 or not start_date.isdigit() or not end_date.isdigit():
                raise ValueError("Dates must be in format yyyymmdd or yyyy")
                
            print(f"Will filter events between {start_date} and {end_date}")
            filename = filename.replace('.csv', f'_{start_date}_to_{end_date}.csv')
            
        except ValueError as e:
            print(f"Invalid date format: {e}")
            proceed = input("Do you want to continue without date filtering? (y/n): ").strip().lower()
            if proceed != 'y':
                return None, None, filename
            start_date = None
            end_date = None
    
    return start_date, end_date, filename

if __name__ == "__main__":
    main()
