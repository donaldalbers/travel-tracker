import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
from datetime import date, datetime
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# --- CONFIGURATION ---
st.set_page_config(page_title="TravelLog 2025", layout="wide")
FLIGHTS_FILE = "flights.csv"
HOTELS_FILE = "hotels.csv"
geolocator = Nominatim(user_agent="my_travel_tracker_2025")

# --- AIRPORT DB (Updated with your Travel Data) ---
AIRPORT_DB = {
    "DFW": [32.8998, -97.0403], "LGA": [40.7769, -73.8740], "JFK": [40.6413, -73.7781],
    "LHR": [51.4700, -0.4543], "ORD": [41.9742, -87.9073], "LAX": [33.9416, -118.4085],
    "MIA": [25.7959, -80.2870], "DCA": [38.8512, -77.0377], "SFO": [37.6213, -122.3790],
    "ATL": [33.6407, -84.4277], "DEN": [39.8561, -104.6737], "SEA": [47.4502, -122.3088],
    "DAL": [32.8471, -96.8517], "STL": [38.7487, -90.3700], "CLT": [35.2140, -80.9431],
    "PHX": [33.4343, -112.0116], "HEL": [60.3172, 24.9633], "AMS": [52.3081, 4.7661],
    "EWR": [40.6895, -74.1745]
}

# --- DATA FUNCTIONS ---
def load_data(file, columns):
    try:
        df = pd.read_csv(file)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

def calculate_distance(origin_code, dest_code):
    if origin_code in AIRPORT_DB and dest_code in AIRPORT_DB:
        start = AIRPORT_DB[origin_code]
        end = AIRPORT_DB[dest_code]
        return int(geodesic(start, end).miles)
    return 0

# --- TABS UI ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Analytics", "✈️ Log Flights", "🏨 Log Hotels"])

# ==========================================
# TAB 1: DASHBOARD
# ==========================================
with tab1:
    df_flights = load_data(FLIGHTS_FILE, ["Date", "Airline", "Origin", "Destination", "Miles", "Origin_Lat", "Origin_Lon", "Dest_Lat", "Dest_Lon"])
    df_hotels = load_data(HOTELS_FILE, ["Date", "Name", "City", "Address", "Nights", "Lat", "Lon"])

    st.title("🌍 2025 Travel Year in Review")

    if not df_flights.empty:
        # --- DATE FILTERS ---
        df_flights["Date"] = pd.to_datetime(df_flights["Date"])
        # Handle hotels date conversion safely
        if not df_hotels.empty:
            df_hotels["Date"] = pd.to_datetime(df_hotels["Date"])

        min_date = df_flights["Date"].min().date()
        max_date = df_flights["Date"].max().date()
        
        start_date, end_date = min_date, max_date
        if min_date < max_date:
            start_date, end_date = st.slider("Filter Date Range", min_date, max_date, (min_date, max_date))
        
        # Filter Flights
        mask_flights = (df_flights["Date"].dt.date >= start_date) & (df_flights["Date"].dt.date <= end_date)
        f_df = df_flights.loc[mask_flights].copy()

        # Filter Hotels
        h_df = pd.DataFrame()
        if not df_hotels.empty:
            mask_hotels = (df_hotels["Date"].dt.date >= start_date) & (df_hotels["Date"].dt.date <= end_date)
            h_df = df_hotels.loc[mask_hotels].copy()

        # --- SCOREBOARD ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Miles", f"{f_df['Miles'].sum():,}")
        c2.metric("Flights", len(f_df))
        c3.metric("Hotel Nights", h_df['Nights'].sum() if not h_df.empty else 0)
        c4.metric("Unique Cities", f_df['Destination'].nunique())

        # --- MAP ---
        # Flight Colors
        f_df["Route_ID"] = f_df.apply(lambda x: "-".join(sorted([x["Origin"], x["Destination"]])), axis=1)
        route_counts = f_df["Route_ID"].value_counts().to_dict()
        f_df["Frequency"] = f_df["Route_ID"].map(route_counts)

        def get_color(freq):
            if freq >= 5: return [255, 0, 0, 200]    # Red
            if freq >= 3: return [255, 165, 0, 200]  # Orange
            return [0, 128, 255, 150]                # Blue
        f_df["Color"] = f_df["Frequency"].apply(get_color)

        layers = []
        # Layer 1: Flights
        layers.append(pdk.Layer(
            "ArcLayer",
            data=f_df,
            get_source_position=["Origin_Lon", "Origin_Lat"],
            get_target_position=["Dest_Lon", "Dest_Lat"],
            get_width=3,
            get_tilt=15,
            get_source_color="Color",
            get_target_color="Color",
        ))
        
        # Layer 2: Hotels (Filtered by date)
        if not h_df.empty:
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=h_df,
                get_position=["Lon", "Lat"],
                get_color=[0, 200, 100, 255], # Bright Green
                get_radius=200, 
                pickable=True
            ))

        st.pydeck_chart(pdk.Deck(
            layers=layers,
            initial_view_state=pdk.ViewState(latitude=39.0, longitude=-98.0, zoom=3, pitch=40),
            tooltip={"text": "{Airline}: {Origin}-{Destination}\n{Name}"}
        ))

        # --- ANALYTICS DEEP DIVE ---
        st.divider()
        st.subheader("Analytics Deep Dive")
        
        col_charts_1, col_charts_2 = st.columns(2)
        
        with col_charts_1:
            st.markdown("**Monthly Miles Flown**")
            f_df['Month'] = f_df['Date'].dt.strftime('%Y-%m')
            chart_miles = alt.Chart(f_df).mark_bar().encode(
                x='Month',
                y='sum(Miles)',
                color=alt.value("#4c78a8"),
                tooltip=['Month', 'sum(Miles)']
            ).interactive()
            st.altair_chart(chart_miles, use_container_width=True)

        with col_charts_2:
            st.markdown("**Top Hotels (Nights)**")
            if not h_df.empty:
                chart_hotels = alt.Chart(h_df).mark_bar().encode(
                    x=alt.X('sum(Nights)', title='Total Nights'),
                    y=alt.Y('Name', sort='-x', title='Hotel Name'), # Sorted by most nights
                    color=alt.value("#00C864"), # Matching Map Pins
                    tooltip=['Name', 'sum(Nights)', 'City']
                )
                st.altair_chart(chart_hotels, use_container_width=True)
            else:
                st.info("No hotel data in this date range.")

        # Top Destinations Bar Chart
        st.markdown("**Most Visited Destinations**")
        chart_dest = alt.Chart(f_df).mark_bar().encode(
            x=alt.X('count()', title='Number of Visits'),
            y=alt.Y('Destination', sort='-x'),
            color=alt.value("#f58518"),
            tooltip=['Destination', 'count()']
        )
        st.altair_chart(chart_dest, use_container_width=True)

    else:
        st.info("No flights logged yet. Go to the 'Log' tabs to start!")

# ==========================================
# TAB 2: FLIGHTS (Add & Edit)
# ==========================================
with tab2:
    st.subheader("Add New Flight")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_date = st.date_input("Date", date.today())
    with c2: f_air = st.selectbox("Airline", ["American Airlines", "Delta", "United", "Other"])
    with c3: f_org = st.text_input("Origin (Code)").upper()
    with c4: f_dst = st.text_input("Dest (Code)").upper()
    
    st.caption("Leave 'Miles' as 0 to auto-calculate.")
    f_miles = st.number_input("Miles", value=0)

    if st.button("Save Flight"):
        if f_org in AIRPORT_DB and f_dst in AIRPORT_DB:
            if f_miles == 0: f_miles = calculate_distance(f_org, f_dst)
            olat, olon = AIRPORT_DB[f_org]
            dlat, dlon = AIRPORT_DB[f_dst]

            new_row = pd.DataFrame([{
                "Date": f_date, "Airline": f_air, "Origin": f_org, "Destination": f_dst,
                "Miles": f_miles, "Origin_Lat": olat, "Origin_Lon": olon,
                "Dest_Lat": dlat, "Dest_Lon": dlon
            }])
            df_curr = load_data(FLIGHTS_FILE, new_row.columns)
            save_data(pd.concat([df_curr, new_row], ignore_index=True), FLIGHTS_FILE)
            st.success(f"Added {f_org}->{f_dst}")
            st.rerun()
        else:
            st.error("Unknown Airport Code.")

    st.divider()
    st.subheader("Manage Flights")
    df_editor = load_data(FLIGHTS_FILE, [])
    if not df_editor.empty:
        edited_df = st.data_editor(df_editor, num_rows="dynamic", key="flight_editor")
        if st.button("Save Flight Changes"):
            save_data(edited_df, FLIGHTS_FILE)
            st.success("Changes saved!")
            st.rerun()

# ==========================================
# TAB 3: HOTELS (Advanced Search)
# ==========================================
with tab3:
    st.subheader("Log Hotel Stay")
    
    # 1. SEARCH
    search_query = st.text_input("Search Hotel (e.g. 'Le Meridien Clayton')")
    if st.button("Search Location"):
        if search_query:
            try:
                # We ask for 'addressdetails' to parse City/Name better
                location = geolocator.geocode(search_query, addressdetails=True)
                if location:
                    st.session_state['hotel_found'] = location
                    st.success(f"Found: {location.address}")
                else:
                    st.error("Location not found.")
            except Exception as e:
                st.error(f"Error: {e}")

    # 2. AUTO-POPULATE LOGIC
    found = st.session_state.get('hotel_found', None)
    
    default_name = ""
    default_city = ""
    default_addr = ""
    
    if found:
        raw = found.raw.get('address', {})
        default_name = raw.get('hotel', raw.get('tourism', found.address.split(',')[0]))
        default_city = raw.get('city', raw.get('town', raw.get('village', raw.get('county', ''))))
        default_addr = found.address

    # 3. FORM
    with st.form("hotel_form"):
        h_date = st.date_input("Check-in Date", date.today())
        h_name = st.text_input("Hotel Name", value=default_name) 
        h_city = st.text_input("City", value=default_city)
        h_addr = st.text_input("Full Address", value=default_addr)
        h_nights = st.number_input("Nights", min_value=1, value=1)
        
        submitted = st.form_submit_button("Log Hotel")
        
        if submitted:
            lat = found.latitude if found else 0.0
            lon = found.longitude if found else 0.0
            
            new_hotel = pd.DataFrame([{
                "Date": h_date, "Name": h_name, "City": h_city, "Address": h_addr,
                "Nights": h_nights, "Lat": lat, "Lon": lon
            }])
            
            df_h = load_data(HOTELS_FILE, new_hotel.columns)
            save_data(pd.concat([df_h, new_hotel], ignore_index=True), HOTELS_FILE)
            st.success("Hotel Saved!")
            st.rerun()

    st.divider()
    st.subheader("Manage Hotels")
    df_h_editor = load_data(HOTELS_FILE, [])
    if not df_h_editor.empty:
        edited_h_df = st.data_editor(df_h_editor, num_rows="dynamic", key="hotel_editor")
        if st.button("Save Hotel Changes"):
            save_data(edited_h_df, HOTELS_FILE)
            st.success("Changes saved!")
            st.rerun()