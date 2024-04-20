import pandas as pd
import csv
import os
import zipfile
import zlib
import io
from fuzzywuzzy import process

# Constants
NUM_TOP_ROUTES_PROMPT = 20
NUM_WORLDWIDE_ROUTES = 100
NUM_RESULTS_TO_PICK = 500

PORTS_BY_REGION = pd.read_csv('PORTS_BY_REGION.csv')
'''
            Region                     Port
0          Britain                   London
1          Britain                 Plymouth
2          Britain                Edinburgh
3          Britain                   Dublin
4          Britain                  Bristol
..             ...                      ...
181  Landing Sites  Northeastern Baltic Sea
182  Landing Sites   Southern North America
183  Landing Sites    Western North America
184  Landing Sites        Galapagos Islands
185  Landing Sites    Eastern South America
'''

ITEMS_BY_PORT = pd.read_csv('ITEMS_BY_PORT.csv')
'''
              Item   Port Name  Price
0          Whiskey      London    810
1    Woolen Fabric      London   1260
2           Weapon      London   1620
3    England Tweed      London   1800
4             Wool      London    945
..             ...         ...    ...
545   Wood Carving  Valparaiso    810
546         Silver  Valparaiso   1800
547      Fish Meat     Copiapó    540
548        Quinine     Copiapó   1458
549        Tobacco     Copiapó   1890
'''

REGION_TRAVEL_MATRIX = pd.read_csv('REGION_TRAVEL_MATRIX.csv', index_col=0)
'''
REGION_TRAVEL_MATRIX:
         Persia  Arab  East Africa
Italy         2     2            2
Balkan        2     2            2
Britain       3     2            2
(note that this is only a subset for clarity, it is a matrix of every trade region as a column mapped
against every trade region as a row. Regions with no ports with stores (e.g. Oceania) are not present.
This is a matrix of the number of months of travel between regions.)
'''

ITEM_VALUE_BY_REGION = pd.read_csv('ITEM_VALUE_BY_REGION.csv', index_col=0)
'''
ITEM_VALUE_BY_REGION:
                East Asia  ...  South America West Coast
Name                       ...                          
Glass Ball           1650  ...                      2200
Folding Fan          1800  ...                      2400
Wood Carving          900  ...                       900
Pewterware           1500  ...                      1500
Glassware            2600  ...                      2600
...                   ...  ...                       ...
Velvet               6400  ...                      4800
Royal Purple         4160  ...                      3840
Viking Artware       7000  ...                      7000
Blended Alloy        4800  ...                      4800
Fine Gunpowder       4100  ...                      4100
'''


# ---- HELPERS ----

# Saving and loading compressed data, like the big global trade routes dataframe

def save_df_to_zip(df, zip_filename, csv_filename):
    # Save the dataframe to a plaintext CSV file
    csv_filename_temp = csv_filename.replace('.csv', '_temp.csv')
    df.to_csv(csv_filename_temp, index=False)

    # Compress the temporary CSV file
    with open(csv_filename_temp, 'rb') as f_in:
        with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zip_ref:
            zip_ref.write(csv_filename_temp, arcname=csv_filename)
    
    # Clean up the temporary CSV file
    os.remove(csv_filename_temp)

def load_df_from_zip(zip_filename, csv_filename):
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        with zip_ref.open(csv_filename) as file:
            return pd.read_csv(file)

# String matching with fuzzywuzzy, to accommodate typos or not being able to type special characters

def find_closest_match(input_str, valid_strings):
    closest_match, _ = process.extractOne(input_str, valid_strings)
    return closest_match

def find_closest_port(input_str):
    valid_ports = ITEMS_BY_PORT['Port Name'].unique().tolist()
    if input_str in valid_ports:
        return input_str
    else:
        return find_closest_match(input_str, valid_ports)

# ---- CALCULATIONS ----

# This function calculates the profit from buying an item at a source port and selling it at the destination port.
# It does not consider price index (which should average to 100%) or trade distance, just the transfer itself.
# Verbose was mostly used for testing.
def calculate_profit(item_name, source_port, destination_port, verbose=False):
    if verbose:
        print(f"Calculating profit for item '{item_name}' bought in '{source_port}' and sold in '{destination_port}':\n")
    
    # Find buying price at source port
    source_item_row = ITEMS_BY_PORT[(ITEMS_BY_PORT['Port Name'] == source_port) & (ITEMS_BY_PORT['Item'] == item_name)]
    if source_item_row.empty:
        raise ValueError(f"The item '{item_name}' is not available at the source port '{source_port}'.")
    buying_price = source_item_row['Price'].values[0]
    if verbose:
        print(f"Buying price at '{source_port}': {buying_price}")
    
    # Find destination region
    destination_region_row = PORTS_BY_REGION[PORTS_BY_REGION['Port'] == destination_port]
    if destination_region_row.empty:
        raise ValueError(f"Destination port '{destination_port}' not found in the PORTS_BY_REGION table.")
    destination_region = destination_region_row['Region'].values[0]
    if verbose:
        print(f"Destination port '{destination_port}' belongs to region '{destination_region}'")
    
    # Find item value in destination region
    item_value_row = ITEM_VALUE_BY_REGION.loc[item_name, destination_region]
    if verbose:
        print(f"Value of '{item_name}' in region '{destination_region}': {item_value_row}")
    
    # Adjust sale price based on item availability in destination region
    sale_price = item_value_row
    other_ports_in_region = PORTS_BY_REGION[PORTS_BY_REGION['Region'] == destination_region]['Port'].tolist()
    other_ports_in_region.remove(destination_port)  # Exclude destination port from the list
    
    if item_name in ITEMS_BY_PORT[ITEMS_BY_PORT['Port Name'].isin(other_ports_in_region)]['Item'].tolist():
        # Sale price lowered by 10% if the item is available at any other port in the region
        sale_price *= 0.9
        if verbose:
            print("Item is available at other ports in the destination region. Sale price lowered by 10%.")
    elif item_name in ITEMS_BY_PORT[ITEMS_BY_PORT['Port Name'] == destination_port]['Item'].tolist():
        # Sale price drops by 80% if the item is sold at a port where it can be bought
        sale_price *= 0.2
        if verbose:
            print("Item is sold at a port where it can be bought. Sale price dropped by 80%.")
    
    # Calculate profit
    profit = sale_price - buying_price
    
    if verbose:
        print(f"\nProfit calculated: {profit}")
    return profit

def calculate_all_routes_between_two_ports(port_A, port_B, profit_threshold=0):
    # Ensure port1 and port2 are in alphabetical order
    port1, port2 = sorted([port_A, port_B])

    # Check if both ports exist in the travel matrix to determine range and viability of trade route
    region_A = PORTS_BY_REGION[PORTS_BY_REGION['Port'] == port1]['Region'].values[0]
    region_B = PORTS_BY_REGION[PORTS_BY_REGION['Port'] == port2]['Region'].values[0]

    if region_A not in REGION_TRAVEL_MATRIX.columns or region_B not in REGION_TRAVEL_MATRIX.columns:
        return pd.DataFrame()  # Return empty DataFrame if any port is not in the matrix

    # Determine the travel time (range) between the two regions
    travel_range = REGION_TRAVEL_MATRIX.loc[region_A, region_B]

    # Initialize an empty list to hold all profitable routes
    profitable_routes = []

    # Get all items available at port A and B
    items_A = ITEMS_BY_PORT[ITEMS_BY_PORT['Port Name'] == port1]
    items_B = ITEMS_BY_PORT[ITEMS_BY_PORT['Port Name'] == port2]

    # Store profits for all items at port A and port B in a dictionary to avoid redundant calculations
    profit_A_dict = {}
    profit_B_dict = {}
    for _, item_A in items_A.iterrows():
        try:
            profit_A_dict[item_A['Item']] = calculate_profit(item_A['Item'], port1, port2, verbose=False)
        except ValueError:
            profit_A_dict[item_A['Item']] = None

    for _, item_B in items_B.iterrows():
        try:
            profit_B_dict[item_B['Item']] = calculate_profit(item_B['Item'], port2, port1, verbose=False)
        except ValueError:
            profit_B_dict[item_B['Item']] = None

    # Evaluate all combinations using the stored profit values
    for item_A, profit_A_to_B in profit_A_dict.items():
        if profit_A_to_B is None:
            continue
        for item_B, profit_B_to_A in profit_B_dict.items():
            if profit_B_to_A is None:
                continue

            # Calculate total profit per month for profitable routes
            total_profit = profit_A_to_B + profit_B_to_A
            if total_profit <= profit_threshold:  # Only consider routes where the total profit is above the given threshold
                continue

            # The profit per month is the average of the two (sum divided by two), divided by the number of months it takes for a transit.
            total_profit_per_month = total_profit / (2 * travel_range)
            route = {
                "port1_name": port1,
                "port1_item": item_A,
                "port1_profit": profit_A_to_B,
                "port2_name": port2,
                "port2_item": item_B,
                "port2_profit": profit_B_to_A,
                "range": travel_range,
                "profit_per_month": total_profit_per_month
            }
            profitable_routes.append(route)

    # Convert the list of dictionaries to a DataFrame and return it
    return pd.DataFrame(profitable_routes)

def get_global_trade_routes(profit_threshold=0):
    output_file = "global_trade_routes.zip"

    # Check if the local zip file exists
    if os.path.exists(output_file):
        print(f"Loading global trade routes from '{output_file}'... (to perform all calculations fresh, delete this zip file before running the script)")
        return load_df_from_zip(output_file, "global_trade_routes.csv")

    print(f"Performing one-time calculation of all global trade routes and saving to '{output_file}'. Please stand by, this may take some time.")

    all_ports = sorted(ITEMS_BY_PORT['Port Name'].unique())  # Alphabetize port names

    total_ports = len(all_ports)
    all_routes = []

    for i, port1 in enumerate(all_ports):
        print(f"Calculating trade routes for port {port1} ({i+1}/{total_ports})...")
        for j, port2 in enumerate(all_ports[i + 1:], start=i + 1):
            routes = calculate_all_routes_between_two_ports(port1, port2, profit_threshold)
            all_routes.append(routes)

    # Concatenate the list of dataframes into a single dataframe
    all_routes_df = pd.concat(all_routes, ignore_index=True)

    # Rename columns to match the desired output
    all_routes_df.rename(columns={'port1_port': 'port1_name', 'port2_port': 'port2_name'}, inplace=True)

    # Save the dataframe to a zip file
    save_df_to_zip(all_routes_df, output_file, "global_trade_routes.csv")

    print(f"\nGlobal trade routes calculated and saved to '{output_file}'")

    return all_routes_df

def pick_best_trade_routes(routes_df, num_results=10, specific_port=None, short_range_only=False):
    # Apply filters based on parameters
    filtered_routes = routes_df.copy()

    if specific_port:
        filtered_routes = filtered_routes[(filtered_routes['port1_name'] == specific_port) | (filtered_routes['port2_name'] == specific_port)]

    if short_range_only:
        filtered_routes = filtered_routes[filtered_routes['range'] == 1]

    # Sort routes by profit_per_month in descending order, then alphabetically on port1_name and port2_name
    filtered_routes = filtered_routes.sort_values(by=['profit_per_month', 'port1_name', 'port2_name'], ascending=[False, True, True])

    # Return the top num_results routes
    return filtered_routes.head(num_results)


def print_routes(routes, num_to_display=10):
    # Check if the dataframe is empty
    if routes.empty:
        print("  There are no records to display.")
        return

    # Ensure items are in alphabetical order by swapping positions if necessary
    routes['port1_name'], routes['port2_name'] = zip(*routes.apply(lambda row: (row['port2_name'], row['port1_name']) 
                                                                      if row['port1_item'] > row['port2_item'] 
                                                                      else (row['port1_name'], row['port2_name']), 
                                                                   axis=1))
    routes['port1_item'], routes['port2_item'] = zip(*routes.apply(lambda row: (row['port2_item'], row['port1_item']) 
                                                                      if row['port1_item'] > row['port2_item'] 
                                                                      else (row['port1_item'], row['port2_item']), 
                                                                   axis=1))

    # Sort the routes by profit_per_month in descending order
    routes = routes.sort_values(by=['profit_per_month', 'port1_name', 'port2_name'], ascending=False)

    # Group the routes and make city names distinct
    grouped_routes = routes.groupby(['port1_item', 'port2_item', 'profit_per_month']).agg({
        'port1_name': lambda x: "/".join(sorted(set(x))),
        'port2_name': lambda x: "/".join(sorted(set(x))),
        'range': 'first'
    }).reset_index()
    
    # Sort grouped routes by profit_per_month in descending order
    grouped_routes = grouped_routes.sort_values(by='profit_per_month', ascending=False)
    
    # Track printed ports
    printed_ports = set()
    
    # Track number of printed rows
    printed_rows = 0

    for _, row in grouped_routes.iterrows():
        if printed_rows >= num_to_display:
            break
        
        port1_names = row['port1_name']
        port2_names = row['port2_name']
        
        # Check if all ports are already printed
        if all(port in printed_ports for port in port1_names.split('/')) and \
           all(port in printed_ports for port in port2_names.split('/')):
            continue

        printed_ports.update(port1_names.split('/'))
        printed_ports.update(port2_names.split('/'))
        
        profit = round(row['profit_per_month'], 1)
        range_value = row.get('range', 0)
        range_info = f" [range={range_value}]" if range_value > 1 else ''
        print(f"  {port1_names} ({row['port1_item']}), {port2_names} ({row['port2_item']}), {profit}{range_info}")
        
        printed_rows += 1

    print()

def main():
    # Clear the screen
    os.system('cls' if os.name == 'nt' else 'clear')
    # Get global trade routes
    global_routes = get_global_trade_routes()
    print(" ")

    while True:
        # Prompt user for input
        port_input = input(f"- Enter a port to get the top {NUM_TOP_ROUTES_PROMPT} trade routes from that port,\n"
                            f"- Leave blank for the top {NUM_WORLDWIDE_ROUTES} trade routes worldwide \n"
                            f"- Add an asterisk (*) to only show short range routes (no Charting Office)\n"
                            f"- Your spelling does not have to be exact, it will guess the port you meant.\n"
                            f"- Type 'exit' to exit.\n"
                            f"> ")

        # Check for short range option
        if port_input.endswith('*'):
            port_input = port_input.rstrip('*')
            short_range_only = True
        else:
            short_range_only = False

        if port_input == 'exit':
            break

        # Clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')

        if port_input:
            port_input = find_closest_port(port_input)

        # Determine the number of results to display
        if port_input:
            num_to_display = NUM_TOP_ROUTES_PROMPT
            description = f"Showing the top {NUM_TOP_ROUTES_PROMPT} trade routes for port '{port_input}':"
        else:
            num_to_display = NUM_WORLDWIDE_ROUTES
            description = f"Showing all {NUM_WORLDWIDE_ROUTES} trade routes globally:"

        if short_range_only:
            description += " (Short Range Only)"

        print(description)

        # Pick the best trade routes
        best_routes = pick_best_trade_routes(global_routes, num_results=NUM_RESULTS_TO_PICK, specific_port=port_input,
                                             short_range_only=short_range_only)

        # Print the routes
        print_routes(best_routes, num_to_display=num_to_display)

if __name__ == "__main__":
    main()




# TEST STUFF 
#pd.set_option('display.max_columns', None)  # Ensure all columns are shown
#pd.set_option('display.expand_frame_repr', False)  # Prevent DataFrame wrapping
#pd.set_option('display.max_colwidth', None)  # Display full content of each column
#pd.set_option('display.width', 1000)  # Set the display width for very wide DataFrames

#profits1 = calculate_profit("Glass Ball", "Amsterdam", "St. George", verbose=True)
    #Buying price at 'Amsterdam': 495
    #Destination port 'St. George' belongs to region 'West Africa'
    #Value of 'Glass Ball' in region 'West Africa': 2750
    #Profit calculated: 2255

#profits2 = calculate_profit("Gold", "St. George", "Amsterdam", verbose=False)
    #Buying price at 'St. George': 4050
    #Destination port 'Amsterdam' belongs to region 'Netherlands'
    #Value of 'Gold' in region 'Netherlands': 9000

#profit_calculations = calculate_all_routes_between_two_ports("Veracruz", "Amsterdam", profit_threshold=-10000)
#print(profit_calculations)
'''
       port1_name     port1_item  port1_profit  port2_name  port2_item  port2_profit  range  profit_per_month
    0   Amsterdam            Gin           420  St. George      Cotton            80      2            125.00
    1   Amsterdam            Gin           420  St. George  Copper Ore           150      2            142.50
    2   Amsterdam            Gin           420  St. George       Agate           165      2            146.25
    3   Amsterdam            Gin           420  St. George        Gold          4950      2           1342.50
    4   Amsterdam            Gin           420  St. George       Ivory          2700      2            780.00
    5   Amsterdam     Glass Ball          2255  St. George      Cotton            80      2            583.75
    6   Amsterdam     Glass Ball          2255  St. George  Copper Ore           150      2            601.25
'''


#print(get_global_trade_routes())
'''
           port1_name port1_item  port1_profit port2_name    port2_item  port2_profit  range  profit_per_month
    0         Abidjan    Coconut          56.0   Acapulco          Wood           0.0      2             14.00
    1         Abidjan    Coconut          56.0   Acapulco  Sweet Potato          48.0      2             26.00
    2         Abidjan    Coconut          56.0   Acapulco        Silver         200.0      2             64.00
    3         Abidjan      Ivory        1500.0   Acapulco          Wood           0.0      2            375.00
    4         Abidjan      Ivory        1500.0   Acapulco  Sweet Potato          48.0      2            387.00
    ...           ...        ...           ...        ...           ...           ...    ...               ...
    129851   Zanzibar    Emerald        4235.0  Zhangzhou       Celadon        3740.0      2           1993.75
    129852   Zanzibar    Emerald        4235.0  Zhangzhou          Silk        3105.0      2           1835.00
    129853   Zanzibar    Emerald        4235.0  Zhangzhou      Tea Leaf        1650.0      2           1471.25
    129854   Zanzibar    Emerald        4235.0  Zhangzhou      Iron Ore         120.0      2           1088.75
    129855   Zanzibar    Emerald        4235.0  Zhangzhou          Musk        2915.0      2           1787.50
'''

#GLOBAL_ROUTES = get_global_trade_routes()
#best_routes = pick_best_trade_routes(GLOBAL_ROUTES, num_results=500)
#print_routes(best_routes,num_to_display=50)
