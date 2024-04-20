import os
import requests
import re
import pandas as pd

def get_html(url):
    # Create cache folder if it doesn't exist
    if not os.path.exists('cache'):
        os.makedirs('cache')

    # Extract filename from URL
    filename = url.split('/')[-1]

    # Check if HTML file is cached
    cache_path = os.path.join('cache', filename)
    if os.path.exists(cache_path):
        # If cached, read and return HTML content
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # If not cached, download HTML content and save to cache folder
        response = requests.get(url)
        if response.status_code == 200:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return response.text
        else:
            print(f"Failed to retrieve HTML content from {url}")
            return None

def get_port_data(html_content):
    port_data = []
    pattern = r'<h1 class="toc-header" id="([^"]+)"><a href="#[^"]+" class="toc-anchor">[^<]+</a>(.*?)</h1>\s*<ul>(.*?)</ul>'
    matches = re.finditer(pattern, html_content, re.DOTALL)
    for match in matches:
        region = match.group(2).strip()
        ports = re.finditer(r'<a class="is-asset-link" href="([^"]+)">([^<]+)</a>', match.group(3))
        for port in ports:
            port_url = port.group(1)
            port_name = port.group(2)
            port_data.append((region, port_url, port_name))
    df = pd.DataFrame(port_data, columns=['Region', 'Port URL', 'Port Name'])
    return df

def get_port_goods(html_content):
    port_goods = []
    goods = re.finditer(r'<td><a class="is-asset-link" href="([^"]+)">([^<]+)</a></td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>', html_content)
    for good in goods:
        item_url = good.group(1)
        item_name = good.group(2)
        price = int(good.group(3))
        stock = int(good.group(4))
        port_goods.append((item_name, item_url, price, stock))
    return port_goods

def collate_port_data(port_data, max_ports=99999):
    master_port_list = []
    master_item_list = []

    for index, row in port_data.iterrows():
        if index >= max_ports:
            break
        url = 'https://sailingera.wiki' + row['Port URL']
        html_content = get_html(url)
        port_goods = get_port_goods(html_content)
        for item_name, item_url, price, stock in port_goods:
            master_port_list.append((row['Port Name'], item_name, price, stock))
            master_item_list.append((item_name, item_url))

    master_port_df = pd.DataFrame(master_port_list, columns=['Port Name', 'Item', 'Price', 'Stock'])
    master_item_df = pd.DataFrame(master_item_list, columns=['Item', 'Item URL'])
    
    return master_port_df, master_item_df

def get_item_value(html_content):
    # Find the value of the item (Baseline)
    baseline_value = re.search(r'Value:\s*(\d+)', html_content)
    if baseline_value:
        baseline_value = int(baseline_value.group(1))
    else:
        baseline_value = None

    # Find item prices in different ports
    port_prices = []
    pattern = r'<tr>\s*<td><a class="is-asset-link" href="../port/\d+">([^<]+)</a></td>\s*<td>(\d+)</td>'
    matches = re.finditer(pattern, html_content)
    for match in matches:
        port_name = match.group(1)
        price = int(match.group(2))
        port_prices.append((port_name, price))

    return baseline_value, port_prices

def compile_value_table(master_item_df):
    value_table = []

    for index, row in master_item_df.iterrows():
        url = 'https://sailingera.wiki/en' + row['Item URL']
        html_content = get_html(url)
        item_name = row['Item']
        baseline_value, port_prices = get_item_value(html_content)
        
        # Append baseline value if available
        if baseline_value is not None:
            value_table.append((item_name, 'Baseline', baseline_value))

        # Append port prices
        for port_name, price in port_prices:
            value_table.append((item_name, port_name, price))

    value_df = pd.DataFrame(value_table, columns=['Item', 'Port', 'Price'])
    return value_df

def add_specialty_indicator(master_item_df, specialty_goods, non_specialty_goods):
    specialty_goods = [good.strip() for good in specialty_goods.split(',')]
    non_specialty_goods = [good.strip() for good in non_specialty_goods.split(',')]
    missing_goods = []

    # Add is_specialty column and set default to False
    master_item_df['is_specialty'] = False

    # Iterate through all items in the dataframe
    for index, row in master_item_df.iterrows():
        item_name = row['Item']

        # Check if the item is in the list of specialty goods
        if item_name in specialty_goods:
            master_item_df.at[index, 'is_specialty'] = True

        # Check if the item is in the list of non-specialty goods
        elif item_name in non_specialty_goods:
            master_item_df.at[index, 'is_specialty'] = False

        # If not found in either list, add it to the list of missing items
        else:
            missing_goods.append(item_name)

    return master_item_df, missing_goods

specialty_goods = "Ginseng, Myrrh, Chamomile, Rhino Horn, Maca, Oregano, Port Wine, Sherry, Brandy, Rum, Sake, Yellow Rice Wine, Beer, Gin, Aquavit, Natural Silk, Lace, Silk, England Tweed, Velvet, Turkish Rug, Indian Calico, Royal Purple, Carmine, Celadon, White Porcelain, Blue and White Porcelain, Laquerware, Folding Fan, Oil Painting, Glass Ball, Marble Statue, Blue Porcelain, Ancient Fine Art, Papyrus Painting, Tulip Bulb, Soap, Pottery, Armor, Firearm, Peach Wood, Oak, Musk, Wootz Steel, Damascus Knife, Katana, Teak, Red Sandalwood, Ebony Wood, Sisal, Amber, Gold, Lapis Lazuli, Emerald, Ivory, Jadeite, Diamond, Ruby, Sapphire, Blue Eye, Desert Rose, Tobacco, Cocoa, Tea Leaf, Coffee, Mate, Date Palm, Agarwood, Frankincense, White Sandalwood, Black Pepper, Nutmeg, Mace, Vanilla, Rosemary, Argan Oil, Saffron, Egyptian Essence, Cinnamon, Clove, Whiskey, Turmeric, Tequila, Quinine, Lacquerware, Rhodochrosite"
non_specialty_goods = "Rice, Wheat, Corn, Potato, Cheese, Sausage, Coconut, Banana, White Sugar, Salt, Butter, Honey, Olive Oil, Rye, Fish Meat, Wine, Cotton, Fur, Cotton Fabric, Woolen Fabric, Pewterware, Glassware, Silver Artware, Golden Artware, Glass Artware, Wood Carving, Jewelry, Copper Ore, Iron Ore, Tin Ore, Marble, Niter, Wood, Beeswax, Weapon, Lead, Coral, Turquoise, Gunpowder, Parchment, Zinc Ore, Cedar Wood, Korean Pine Wood, Linen, Charcoal, Ship Spike, Potassium Alum, Brass, Quartz, Silver, Pearl, Tortoise Shell, Agate, Ambergris, Wool, Sweet Potato"

# MAIN

url = 'https://sailingera.wiki/en/port'
html_content = get_html(url)
regions_df = get_port_data(html_content)
print(regions_df)

master_port_df, master_item_df = collate_port_data(regions_df)
print("Master Port List:")
print(master_port_df)

print("\nMaster Item List:")
print(master_item_df)

master_item_df, missing_goods = add_specialty_indicator(master_item_df, specialty_goods, non_specialty_goods)

# Print the list of missing items
print("\nMissing Items that need to be specified as specialty or non-specialty:")
print(missing_goods)

value_table = compile_value_table(master_item_df)
print("Value Table:")
print(value_table)

#Massage the data for output


# Rename the column 'Port Name' to 'Port' in ports_by_region table
ports_by_region = regions_df.rename(columns={'Port Name': 'Port'})[['Region', 'Port']]
print("ports_by_region:")
print(ports_by_region)

# Items by port table
items_by_port = master_port_df[['Item', 'Port Name', 'Price']]
print("items_by_port:")
print(items_by_port)

# Item data table
baseline_prices = value_table[value_table['Port'] == 'Baseline']
item_data = master_item_df.merge(baseline_prices, on='Item', suffixes=('', '_baseline'))[['Item', 'is_specialty', 'Price']]
item_data.rename(columns={'Price': 'Value'}, inplace=True)
item_data = item_data.drop_duplicates(subset=['Item', 'Value'])

# Remove the special case of Agate with the outlier baseline price
item_data = item_data[~((item_data['Item'] == 'Agate') & (item_data['Value'] == 1050))]
print("item_data:")
print(item_data)

# Export data tables to files
ports_by_region.to_csv('ports_by_region.csv', index=False)
items_by_port.to_csv('items_by_port.csv', index=False)
item_data.to_csv('item_data.csv', index=False)