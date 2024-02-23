import pandas as pd

# Input data from the image provided
data = {
    'Factor': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
    'Value': [120, 1, 2, 3, 100, 4, 5, 6]
}

# Create a DataFrame
df = pd.DataFrame(data)

# Calculate the initial ratio (t0) and the subsequent ratio (t1)
ratio_t0 = df.loc[df['Factor'] == 'a', 'Value'].values[0] / df.loc[df['Factor'] == 'e', 'Value'].values[0]
ratio_t1 = df.loc[df['Factor'].isin(['a', 'b', 'c', 'd']), 'Value'].sum() / df.loc[
    df['Factor'].isin(['e', 'f', 'g', 'h']), 'Value'].sum()

# Attribution of each factor's impact on the ratio change
# We will calculate the impact by changing one factor at a time while keeping others constant
attributions = {}

# Calculate the ratio without changing each factor (b, c, d, f, g, h)
for factor in ['b', 'c', 'd', 'f', 'g', 'h']:
    # Temporarily change the factor value to 0 to see the impact on the ratio
    temp_df = df.copy()
    temp_df.loc[temp_df['Factor'] == factor, 'Value'] = 0
    ratio_without_factor = temp_df.loc[temp_df['Factor'].isin(['a', 'b', 'c', 'd']), 'Value'].sum() / temp_df.loc[
        temp_df['Factor'].isin(['e', 'f', 'g', 'h']), 'Value'].sum()

    # The impact is the difference in the new ratio and the original ratio t1
    attributions[factor] = ratio_t1 - ratio_without_factor

# Output the initial ratio, subsequent ratio, and attributions
print(ratio_t0, ratio_t1, attributions)
