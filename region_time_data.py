import pandas as pd

# Define the raw data and labels
region_distances_raw = [
    '111111222224434444444333',
    '111111222224434444444333',
    '111111222224434444444333',
    '111111222224434444444333',
    '111111111123333334444333',
    '111111111123333334444333',
    '222211111123323333333223',
    '222211111112222223333223',
    '222211111112222222222223',
    '222211111112212222222222',
    '222222211111111112222212',
    '444433322211111111112223',
    '444433322211112112222233',
    '333333222111111111111222',
    '444433322211211111111233',
    '444433322211111111111223',
    '444433322211111111112223',
    '444444332221211111111233',
    '444444332221211111111233',
    '444444332221211111111233',
    '444444332222211121111233',
    '333333222222222222222111',
    '333333222212323223333111',
    '333333333223323333333111'
]

region_distances_labels = [
    'Ming Empire', 'Korean', 'Japan',
    'East Asia', 'Southeast Asia', 'Central South Peninsula',
    'India', 'Persia', 'Arab',
    'East Africa', 'West Africa', 'North Africa', 
    'Turkey', 'Iberia', 'France',
    'Italy', 'Balkan', 'Britain',
    'Netherlands', 'Germany', 'Northern Europe',
    'Caribbean', 'Central and South America', 'South America West Coast',
]

# Convert raw data into a 2D list
region_distances_table = [[int(digit) for digit in row] for row in region_distances_raw]

# Create DataFrame
df = pd.DataFrame(region_distances_table, columns=region_distances_labels, index=region_distances_labels)

# Print DataFrame
print(df)

df.to_csv('region_travel_matrix.csv')


# Print a subset of the "region_travel_matrix" DataFrame
print("Subset of region_travel_matrix:")
print(df.iloc[[15, 16, 17], [7, 8, 9]])  # Select rows 9, 10, 11 and columns 0 (Region), 4, 5, 6
