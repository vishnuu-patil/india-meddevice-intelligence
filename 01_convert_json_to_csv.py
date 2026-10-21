from pathlib import Path
# import the json library to read JSON files
import json

# import pandas to work with data tables
import pandas as pd

# define the path to the large JSON file
input_path = str(Path(__file__).resolve().parent / "Data" / "device-510k-0001-of-0001.json")

# define where to save the output CSV file
output_path = str(Path(__file__).resolve().parent / "Data" / "fda_510k.csv")

# tell the user the script has started
print("Reading JSON file... this will take 1-2 minutes due to file size")

# open and load the full JSON file into memory
with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# extract the list of device records from the results key
records = data["results"]

# tell the user how many records were found
print(f"Total records found: {len(records):,}")

# convert the list of records into a pandas dataframe
df = pd.DataFrame(records)

# select only the columns we need for the project
columns_to_keep = [
    "k_number",           # unique ID for each 510k application
    "applicant",          # company name that applied
    "device_name",        # name of the medical device
    "medical_specialty_description",  # which medical specialty it belongs to
    "device_class",       # class I, II or III risk level
    "decision_date",      # when FDA made the decision
    "date_received",      # when FDA received the application
    "decision_description", # approved or not approved
    "country_code",       # country of the applicant company
    "city",               # city of the applicant
    "state",              # state of the applicant
    "clearance_type",     # type of clearance pathway used
    "expedited_review_flag", # whether it was fast tracked
    "advisory_committee_description" # which FDA committee reviewed it
]

# keep only the columns that exist in the dataframe
columns_to_keep = [col for col in columns_to_keep if col in df.columns]

# filter the dataframe to only selected columns
df = df[columns_to_keep]

# convert decision_date to proper date format
df["decision_date"] = pd.to_datetime(df["decision_date"], errors="coerce")

# filter to only records from 2010 onwards to keep data relevant
df = df[df["decision_date"].dt.year >= 2010]

# tell the user how many records remain after filtering
print(f"Records from 2010 onwards: {len(df):,}")

# save the cleaned dataframe as a CSV file
df.to_csv(output_path, index=False)

# confirm the file has been saved
print(f"CSV saved successfully to: {output_path}")
print(f"Final shape: {df.shape}")