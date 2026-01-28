import pandas as pd
import glob
import os

# Folder where all CSV files exist
DATA_FOLDER = r"E:\Manzil\eduvision_scraping\Data"

# Get all CSV files from Data folder
csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

print(f"Found {len(csv_files)} CSV files")

# List to store all dataframes
all_dfs = []

for file in csv_files:
    try:
        df = pd.read_csv(file)

        # Ensure correct column order (optional but safe)
        df = df[[
            "Institute",
            "City",
            "Degree",
            "Duration",
            "Fee",
            "Deadline",
            "Subject"
        ]]

        all_dfs.append(df)

    except Exception as e:
        print(f"❌ Error in file {file}: {e}")

# Merge all CSVs
merged_df = pd.concat(all_dfs, ignore_index=True)

# Save merged CSV
output_path = r"E:\Manzil\eduvision_scraping\merged_all_programs.csv"
merged_df.to_csv(output_path, index=False)

print("✅ All CSV files merged successfully!")
print(f"📁 Output saved at: {output_path}")
