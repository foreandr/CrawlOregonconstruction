import pandas as pd
import os
'''
HE WANTED AS CSV SO IM JUST GUNNA CONVERT THE JSON TO CSV IN THE END
'''
def update_csv_with_json(new_data, csv_path='./logs/data.csv'):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    # Create the CSV file if it does not exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w') as f:
            f.write('')
    
    # Ensure new_data is a list
    if isinstance(new_data, dict):
        new_data = [new_data]
    
    # Load the current CSV data if it exists
    try:
        existing_df = pd.read_csv(csv_path)
        # Check if the file is empty (no columns)
        if existing_df.empty or existing_df.columns.size == 0:
            existing_df = pd.DataFrame()  # Reset to an empty DataFrame
    except (FileNotFoundError, pd.errors.EmptyDataError):
        existing_df = pd.DataFrame()

    # Flatten the incoming JSON data into a DataFrame
    new_df = pd.json_normalize(new_data)
    new_df = new_df.dropna(how='all', axis=1)  # Drop all-NA columns

    # Ensure existing DataFrame has all columns from the new data
    for col in new_df.columns:
        if col not in existing_df.columns:
            existing_df[col] = pd.NA

    # If the CSV is not empty, check for duplicates based on 'current_url'
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates(subset='current_url', keep='first')
    else:
        combined_df = new_df

    # Ensure 'expiration_date' column exists in the DataFrame
    if 'expiration_date' not in combined_df.columns:
        combined_df['expiration_date'] = pd.NA

    # Convert 'expiration_date' to datetime, handling errors and missing values
    combined_df['expiration_date'] = pd.to_datetime(combined_df['expiration_date'], errors='coerce')

    # Sort by 'expiration_date' with NaT values at the bottom
    combined_df = combined_df.sort_values(by='expiration_date', ascending=False, na_position='last')

    # Write the updated DataFrame back to the CSV, overwriting existing content
    combined_df.to_csv(csv_path, index=False, mode='w')
