import pandas as pd
import folium
from folium import DivIcon
import os
from math import radians, sin, cos, sqrt, atan2
from branca.element import Template, MacroElement

# Clear console
os.system('cls' if os.name == 'nt' else 'clear')

# Define your paths here
DATA_PATH = 'NFL.csv'
OUTPUT_PATH = '../index.html'

# Load data
nfl_df = pd.read_csv(DATA_PATH)

# Conference colors
Conference_colors = {
    'AFC': 'red',
    'NFC': 'blue'
}

MIN_DISTANCE_KM = 70 # minimum distance in km to avoid overlap
ITERATIONS = 2 # the higher, the more iterations for separation
DIV_FACTOR = 70 # the lower, the more separation

# Define custom separation directions for specific team pairs
# Format: ("team1", "team2"): (angle_in_degrees, relative_strength)
custom_directions = {    
    ("New York Jets", "New York Giants"): (-60 , 15),
    ("Washington Commanders", "Baltimore Ravens"): (-60 , 50),
    ("Los Angeles Rams", "Los Angeles Chargers"): (60 , 15),
} 

division_orders = {
    "AFC East": [
        "Miami Dolphins",
        "New England Patriots",
        "New York Jets",
        "Buffalo Bills",
    ],
    "NFC East": [
        "Dallas Cowboys",
        "Washington Commanders",
        "Philadelphia Eagles",
        "New York Giants",
    ],
    "AFC North": [
        "Baltimore Ravens",
        "Pittsburgh Steelers",
        "Cincinnati Bengals",
        "Pittsburgh Steelers",
        "Cleveland Browns",
    ],
    "NFC North": [
        "Minnesota Vikings",
        "Green Bay Packers",
        "Chicago Bears",
        "Detroit Lions",
    ],
    "AFC South": [
        "Houston Texans",
        "Tennessee Titans",
        "Indianapolis Colts",
        "Jacksonville Jaguars",
    ],
    "NFC South": [
        "Atlanta Falcons",
        "Carolina Panthers",
        "Atlanta Falcons",
        "New Orleans Saints",
        "Atlanta Falcons",
        "Tampa Bay Buccaneers"
    ],
    "AFC West": [
        "Kansas City Chiefs",
        "Denver Broncos",
        "Las Vegas Raiders",
        "Los Angeles Chargers"
    ],
    "NFC West": [
        "Arizona Cardinals",
        "Los Angeles Rams",
        "San Francisco 49ers",
        "Seattle Seahawks"
    ]
}


# Create map
map = folium.Map(location=[38, -97], zoom_start=4, tiles='CartoDB positron')

map.fit_bounds([[47, #47 zoom in, 48 zoom out
        -90],
                [25, 
                        -105]])


legend_html = """
{% macro html(this, kwargs) %}

<div style="
    position: fixed; 
    bottom: 30px; left: 30px; width: 180px; height: 160px; 
    border:2px solid grey; z-index:9999; font-size:14px;
    background-color: white; opacity: 0.85; padding: 10px;">
<b>Legend</b><br>
<i style="color:red;">&#8212;</i> American Conference <br>
<i style="color:blue;">&#8212;</i> National Conference <br>
<i style="background-color:rgba(100, 0, 255, 0.3); border: 1px solid grey;">&nbsp;&nbsp;&nbsp;</i> Western Region <br>
<i style="background-color:rgba(255, 255, 0, 0.3); border: 1px solid grey;">&nbsp;&nbsp;&nbsp;</i> North Region <br>
<i style="background-color:rgba(0, 255, 0, 0.3); border: 1px solid grey;">&nbsp;&nbsp;&nbsp;</i> South Region <br>
<i style="background-color:rgba(0, 255, 255, 0.3); border: 1px solid grey;">&nbsp;&nbsp;&nbsp;</i> Eastern Region <br>

</div>

{% endmacro %}
"""

legend = MacroElement()
legend._template = Template(legend_html)
map.get_root().add_child(legend)

# Haversine distance calculation
def haversine_distance(p1, p2):
    lat1, lon1 = radians(p1[0]), radians(p1[1])
    lat2, lon2 = radians(p2[0]), radians(p2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return 6371 * c  # Earth radius in km

# Improved function to calculate offset positions for nearby markers
def calculate_offsets(teams_df, min_distance_km=MIN_DISTANCE_KM):
    """
    Calculate offsets for markers that are too close to each other.
    Returns a dictionary with team names as keys and offset coordinates as values.
    """
    offsets = {}
    team_coords = {}
    
    # Get all team coordinates and initialize offsets
    for _, row in teams_df.iterrows():
        team_coords[row['Team']] = (row['Latitude'], row['Longitude'])
        offsets[row['Team']] = (0, 0)  # Initialize with no offset
    
    # Create list of teams for iteration
    team_names = list(team_coords.keys())
    
    # Multiple iterations for better separation
    for iteration in range(ITERATIONS):  # Run multiple passes for better results
        for i in range(len(team_names)):
            team1 = team_names[i]
            coord1 = team_coords[team1]
            
            for j in range(i+1, len(team_names)):
                team2 = team_names[j]
                coord2 = team_coords[team2]
                    
                distance = haversine_distance(coord1, coord2)
                
                if distance < min_distance_km:
                    # Check if we have a custom direction for this pair
                    custom_key1 = (team1, team2)
                    custom_key2 = (team2, team1)
                    
                    if custom_key1 in custom_directions:
                        angle_degrees, strength_multiplier = custom_directions[custom_key1]
                    elif custom_key2 in custom_directions:
                        angle_degrees, strength_multiplier = custom_directions[custom_key2]
                    else:
                        # Default behavior: push directly away from each other
                        dx = coord2[1] - coord1[1]
                        dy = coord2[0] - coord1[0]
                        
                        # Normalize the direction (avoid division by zero)
                        magnitude = max(sqrt(dx*dx + dy*dy), 0.0001)
                        dx /= magnitude
                        dy /= magnitude
                        
                        # Calculate push force
                        push_force = (min_distance_km - distance) / DIV_FACTOR

                        # Apply push in opposite directions
                        offsets[team1] = (offsets[team1][0] - dy * push_force, 
                                         offsets[team1][1] - dx * push_force)
                        offsets[team2] = (offsets[team2][0] + dy * push_force, 
                                         offsets[team2][1] + dx * push_force)
                        continue
                    
                    # Use custom direction
                    angle_radians = radians(angle_degrees)
                    
                    # Calculate push force with custom strength
                    push_force = (min_distance_km - distance) / 20 * strength_multiplier
                    
                    # Convert to degrees (approx 111 km per degree)
                    lat_offset = push_force * cos(angle_radians) / 111
                    lon_offset = push_force * sin(angle_radians) / (111 * cos(radians(coord1[0])))
                    
                    # Apply custom offset (team1 gets the defined direction, team2 gets opposite)
                    offsets[team1] = (offsets[team1][0] + lat_offset, 
                                     offsets[team1][1] + lon_offset)
                    offsets[team2] = (offsets[team2][0] - lat_offset, 
                                     offsets[team2][1] - lon_offset)
    
    return offsets

# Calculate offsets for all teams
marker_offsets = calculate_offsets(nfl_df)

# Add team markers with offsets
for _, row in nfl_df.iterrows():
    color = Conference_colors.get(row['Conference'], 'gray')
    popup_text = f"<b>{row['Team']}</b><br>{row['Division']}"
    
    # Apply offset if needed
    offset = marker_offsets.get(row['Team'], (0, 0))
    lat = row['Latitude'] + offset[0]
    lon = row['Longitude'] + offset[1]
    
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=3,
        color='black',
        fill=True,
        fillColor='black',
        fillOpacity=0.8,
        weight=1,
        tooltip=f"Original location: {row['Team']}"
    ).add_to(map)

    logo_icon = folium.CustomIcon(
        icon_image=row['LogoURL'],
        icon_size=(30, 30),
        icon_anchor=(15, 15),
        popup_anchor=(0, -15)
    )
    
    folium.Marker(
        location=[lat, lon],
        popup=popup_text,
        tooltip=row['Team'],
        icon=logo_icon
    ).add_to(map)

# Create division paths
nfl_df['FullDivision'] = nfl_df['Conference'] + ' ' + nfl_df['Division']


# Create a dictionary for team coordinates with offsets
team_offset_coords = {}
for _, row in nfl_df.iterrows():
    offset = marker_offsets.get(row['Team'], (0, 0))
    team_offset_coords[row['Team']] = (
        row['Latitude'] + offset[0], 
        row['Longitude'] + offset[1]
    )

for division in nfl_df['FullDivision'].unique():
    division_teams = nfl_df[nfl_df['FullDivision'] == division]

    if len(division_teams) < 2:
        continue
        
    # Get Conference color
    Conference = division_teams['Conference'].iloc[0]
    line_color = Conference_colors.get(Conference, 'black')
    
    # Check if custom order is defined
    custom_order = division_orders.get(division, [])
    path = []
    
    if custom_order:
        # If a custom order is defined, use it but verify teams exist
        for team in custom_order:
            if team in team_offset_coords:
                path.append(team_offset_coords[team])
            else:
                print(f"Warning: Team '{team}' not found in division '{division}'")
    else:
        # Default case: use the original order from the CSV with offsets
        for _, team in division_teams.iterrows():
            if team['Team'] in team_offset_coords:
                path.append(team_offset_coords[team['Team']])

    # Add path to map only if we have at least 2 points
    if len(path) >= 2:
        folium.PolyLine(locations=path, color=line_color, weight=2.5, opacity=0.8).add_to(map)
    else:
        print(f"Warning: Not enough valid points for division '{division}' to draw a line")

# WEST
a = (32, -110)
polygon_coords = [
    (49, -125),     # 1
    (49, -95),      # 2
    (40.5, -95),   # 3
    (40.5, -92.5), # 4
    (38, -92.5),   # 5
    a,              # 6
    (32, -125)     # 7
]
folium.Polygon(
    locations=polygon_coords,
    color='purple',          # Border color
    fill_color='purple',     # Fill color
    fill_opacity=0.3,     # Transparency (0.0 to 1.0)
    weight=1              # Border thickness
).add_to(map)

# DEBUGGER
# for i, coord in enumerate(polygon_coords, start=1):
#     folium.Marker(
#         location=coord,
#         tooltip=f"Vertex {i}: {coord}",
#         icon=DivIcon(
#             icon_size=(150,36),
#             icon_anchor=(7,20),
#             html=f'<div style="font-size: 12pt; font-weight: bold; color: black; text-shadow: 1px 1px #FFFFFF;">{i}</div>',
#         )
#     ).add_to(map)
#     folium.CircleMarker(
#             location=coord,
#             radius=5,                   # Marker size in pixels
#             color='blue',               # Circle border color
#             fill=True,
#             fill_color='blue',
#             fill_opacity=0.7,
#             tooltip=str(coord)          # Show coordinates on hover
#         ).add_to(map)

NE = (42.5, -81.5)
NE2 = (39.2, -75.8)
NE3 = (38.7, -84)

# NORTH
polygon_coords = [
    (49, -95),
    NE,
    NE2,
    NE3,      # 3 Ravens - Bengals
    (38.7, -85),      # 5
    (40.5, -85),
    (40.5, -95),
]
folium.Polygon(
    locations=polygon_coords,
    color='yellow',          # Border color
    fill_color='yellow',     # Fill color
    fill_opacity=0.3,     # Transparency (0.0 to 1.0)
    weight=1              # Border thickness
).add_to(map)

# DEBUGGER
# for i, coord in enumerate(polygon_coords, start=1):
#     folium.Marker(
#         location=coord,
#         tooltip=f"Vertex {i}: {coord}",
#         icon=DivIcon(
#             icon_size=(150,36),
#             icon_anchor=(7,20),
#             html=f'<div style="font-size: 12pt; font-weight: bold; color: black; text-shadow: 1px 1px #FFFFFF;">{i}</div>',
#         )
#     ).add_to(map)
#     folium.CircleMarker(
#             location=coord,
#             radius=5,                   # Marker size in pixels
#             color='blue',               # Circle border color
#             fill=True,
#             fill_color='blue',
#             fill_opacity=0.7,
#             tooltip=str(coord)          # Show coordinates on hover
#         ).add_to(map)


# EAST
polygon_coords = [
    NE,             # 1
    (43.5, -79),    # 2
    (43.5, -69.5),    # 3
    (25.5, -79),      # 4
    (25.5, -81.5),    # 5
    (37.8, -75),        # 6
    (31.9, -98),        # 7
    (32.8, -98),       # 8
    (36.5, -84),     # 9
    NE3,             # 10
    NE2              # Final point
]
folium.Polygon(
    locations=polygon_coords,
    color='green',          # Border color
    fill_color='green',     # Fill color
    fill_opacity=0.3,     # Transparency (0.0 to 1.0)
    weight=1              # Border thickness
).add_to(map)

# DEBUGGER
# for i, coord in enumerate(polygon_coords, start=1):
#     folium.Marker(
#         location=coord,
#         tooltip=f"Vertex {i}: {coord}",
#         icon=DivIcon(
#             icon_size=(150,36),
#             icon_anchor=(7,20),
#             html=f'<div style="font-size: 12pt; font-weight: bold; color: black; text-shadow: 1px 1px #FFFFFF;">{i}</div>',
#         )
#     ).add_to(map)
#     folium.CircleMarker(
#             location=coord,
#             radius=5,                   # Marker size in pixels
#             color='blue',               # Circle border color
#             fill=True,
#             fill_color='blue',
#             fill_opacity=0.7,
#             tooltip=str(coord)          # Show coordinates on hover
#         ).add_to(map)


# SOUTH
polygon_coords = [
    (40.5, -92.5),
    (40.5, -85),
    (38.7, -85),
    NE3,
    (36.5, -84),
    (32.8, -98),
    (31.9, -98),
    (37.8, -75),
    (25.5, -81.5),
    a,
    (38, -92.5),
    (40.5, -92.5),
]
folium.Polygon(
    locations=polygon_coords,
    color='cyan',          # Border color
    fill_color='cyan',     # Fill color
    fill_opacity=0.3,     # Transparency (0.0 to 1.0)
    weight=1              # Border thickness
).add_to(map)

# DEBUGGER
# for i, coord in enumerate(polygon_coords, start=1):
#     folium.Marker(
#         location=coord,
#         tooltip=f"Vertex {i}: {coord}",
#         icon=DivIcon(
#             icon_size=(150,36),
#             icon_anchor=(7,20),
#             html=f'<div style="font-size: 12pt; font-weight: bold; color: black; text-shadow: 1px 1px #FFFFFF;">{i}</div>',
#         )
#     ).add_to(map)
#     folium.CircleMarker(
#             location=coord,
#             radius=5,                   # Marker size in pixels
#             color='blue',               # Circle border color
#             fill=True,
#             fill_color='blue',
#             fill_opacity=0.7,
#             tooltip=str(coord)          # Show coordinates on hover
#         ).add_to(map)


# Save map
map.save(OUTPUT_PATH)
print(f"Success! Map has been saved to '{OUTPUT_PATH}'")
print("Custom separations applied for:")
for pair, (angle, strength) in custom_directions.items():
    print(f"  {pair[0]} ↔ {pair[1]}: {angle}° direction, {strength}x strength")