import json
import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

# --- CONFIGURATION ---
FLIGHT_DATA_FILE = 'flightData.txt'
MARRIOTT_DATA_FILE = 'marriottData.txt'
OUTPUT_FLIGHTS = 'flights.csv'
OUTPUT_HOTELS = 'hotels.csv'

# Same DB as app.py for consistency
AIRPORT_DB = {
    "DFW": [32.8998, -97.0403], "LGA": [40.7769, -73.8740], "JFK": [40.6413, -73.7781],
    "LHR": [51.4700, -0.4543], "ORD": [41.9742, -87.9073], "LAX": [33.9416, -118.4085],
    "MIA": [25.7959, -80.2870], "DCA": [38.8512, -77.0377], "SFO": [37.6213, -122.3790],
    "ATL": [33.6407, -84.4277], "DEN": [39.8561, -104.6737], "SEA": [47.4502, -122.3088],
    "DAL": [32.8471, -96.8517], "STL": [38.7487, -90.3700], "CLT": [35.2140, -80.9431],
    "PHX": [33.4343, -112.0116], "HEL": [60.3172, 24.9633], "AMS": [52.3081, 4.7661],
    "EWR": [40.6895, -74.1745]
}

geolocator = Nominatim(user_agent="travel_importer_2025")

def process_flights():
    print("--- Processing Flights ---")
    try:
        with open(FLIGHT_DATA_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {FLIGHT_DATA_FILE} not found.")
        return

    flights = []
    if 'activityCards' in data:
        for card in data['activityCards']:
            summary = card.get('summary', {})
            details = card.get('details', {}).get('flightInfo', {})
            
            # Filter: Keep Airlines/Awards, Skip Refunds
            activity_type = summary.get('activityType')
            desc = summary.get('transactionDescription', '').upper()
            
            if activity_type in ['Airline', 'Award Issuance'] and 'REFUND' not in desc:
                date_str = details.get('travelDate') or summary.get('activityDate')
                origin = (details.get('origin') or summary.get('origin') or '').upper()
                dest = (details.get('destination') or summary.get('destination') or '').upper()
                
                if date_str and origin and dest and origin != dest:
                    # Calculate Miles & Lat/Lon
                    miles = 0
                    olat, olon, dlat, dlon = 0.0, 0.0, 0.0, 0.0
                    
                    if origin in AIRPORT_DB and dest in AIRPORT_DB:
                        ostart = AIRPORT_DB[origin]
                        dend = AIRPORT_DB[dest]
                        miles = int(geodesic(ostart, dend).miles)
                        olat, olon = ostart
                        dlat, dlon = dend
                    
                    flights.append({
                        "Date": pd.to_datetime(date_str).strftime('%Y-%m-%d'),
                        "Airline": "American Airlines",
                        "Origin": origin,
                        "Destination": dest,
                        "Miles": miles,
                        "Origin_Lat": olat, "Origin_Lon": olon,
                        "Dest_Lat": dlat, "Dest_Lon": dlon
                    })
    
    df = pd.DataFrame(flights)
    df.drop_duplicates(inplace=True)
    df.to_csv(OUTPUT_FLIGHTS, index=False)
    print(f"✅ Success: Saved {len(df)} flights to {OUTPUT_FLIGHTS}")

def process_hotels():
    print("\n--- Processing Hotels ---")
    try:
        with open(MARRIOTT_DATA_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {MARRIOTT_DATA_FILE} not found.")
        return

    hotels = []
    if 'data' in data:
        edges = data['data']['customer']['loyaltyInformation']['accountActivity']['edges']
        for edge in edges:
            node = edge.get('node', {})
            if node.get('type', {}).get('code') == 'STAY':
                start = node.get('startDate')
                end = node.get('endDate')
                
                # Extract Name
                props = node.get('properties', [])
                if props:
                    name = props[0].get('basicInformation', {}).get('name')
                else:
                    name = node.get('description')
                
                # Calculate Nights
                try:
                    s = pd.to_datetime(start)
                    e = pd.to_datetime(end)
                    nights = (e - s).days
                except:
                    nights = 1
                
                print(f"Geocoding: {name}...")
                lat, lon, address, city = 0.0, 0.0, name, "Unknown"
                
                try:
                    location = geolocator.geocode(name, addressdetails=True)
                    if location:
                        lat = location.latitude
                        lon = location.longitude
                        address = location.address
                        raw = location.raw.get('address', {})
                        city = raw.get('city', raw.get('town', raw.get('village', 'Unknown')))
                        time.sleep(1) # Be nice to the API
                except Exception as e:
                    print(f"  Warning: Could not geocode {name} ({e})")

                hotels.append({
                    "Date": start,
                    "Name": name,
                    "City": city,
                    "Address": address,
                    "Nights": nights,
                    "Lat": lat, "Lon": lon
                })

    df = pd.DataFrame(hotels)
    df.to_csv(OUTPUT_HOTELS, index=False)
    print(f"✅ Success: Saved {len(df)} hotel stays to {OUTPUT_HOTELS}")

if __name__ == "__main__":
    process_flights()
    process_hotels()