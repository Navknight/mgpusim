import pandas as pd
import os
import glob

def merge_csv_files(input_pattern, output_file):
    """
    Merge multiple CSV files into a single CSV file.

    Args:
        input_pattern (str): Glob pattern to match CSV files
        output_file (str): Name of the output file
    """
    # Get all CSV files matching the pattern
    csv_files = glob.glob(input_pattern)

    if not csv_files:
        print(f"No files found matching pattern: {input_pattern}")
        return

    print(f"Found {len(csv_files)} files to merge: {csv_files}")

    # Create an empty list to store dataframes
    dfs = []

    # Read each CSV file and append to the list
    for file in csv_files:
        try:
            # Add a new column with the source filename
            df = pd.read_csv(file)
            df['OriginalFile'] = os.path.basename(file)
            dfs.append(df)
            print(f"Processed: {file} with {len(df)} rows")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")

    # Concatenate all dataframes
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)

        # Sort the combined dataframe by the Time column
        combined_df = combined_df.sort_values(by='Time')

        # Save to output file
        combined_df.to_csv(output_file, index=False)
        print(f"Merged data saved to {output_file}")
        print(f"Total rows in merged file: {len(combined_df)}")
        print(f"Data sorted by Time column")
    else:
        print("No data to merge.")


if __name__ == "__main__":
    inp = input("Enter file pattern (e.g., 'GPU_*.csv'): ")
    merge_csv_files(inp+"/GPU_*.csv", inp+"/merged.csv")
