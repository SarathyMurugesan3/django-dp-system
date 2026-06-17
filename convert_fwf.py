import pandas as pd
import argparse
import sys
import json
import csv

def convert_text_to_csv_with_lengths(txt_file, layout_csv, output_csv):
   
    col_names = []
    col_widths = []
    
    try:
        if str(layout_csv).lower().endswith('.xlsx') or str(layout_csv).lower().endswith('.xls'):
            layout_df = pd.read_excel(layout_csv)
        else:
            layout_df = pd.read_csv(layout_csv)
            
        name_col = next((col for col in layout_df.columns if 'name' in str(col).lower() or 'field' in str(col).lower()), None)
        length_col = next((col for col in layout_df.columns if 'length' in str(col).lower()), None)
        
        if not name_col or not length_col:
            print("Error: Layout file must contain a column for 'Name' and 'Length'.")
            sys.exit(1)
            
        for index, row in layout_df.iterrows():
            if pd.isna(row[name_col]) or pd.isna(row[length_col]):
                continue
            name = str(row[name_col]).strip()
            try:
                length = int(float(str(row[length_col]).strip()))
                col_names.append(name)
                col_widths.append(length)
            except ValueError:
                continue
                
        print(f"Loaded layout: {len(col_names)} columns found.")
        
        print(f"Reading {txt_file}...")
        df = pd.read_fwf(
            txt_file, 
            widths=col_widths, 
            names=col_names,
            dtype=str,
            header=None
        )
        
        print(f"Saving to {output_csv}...")
        df.to_csv(output_csv, index=False)
        print(f"Successfully converted! Total rows: {len(df)}")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert fixed-width text to CSV based on a layout.")
    parser.add_argument("txt_file", help="Path to the fixed-width text file (.txt)")
    parser.add_argument("layout_csv", help="Path to the layout configuration file (.csv)")
    parser.add_argument("output_csv", help="Path for the output CSV file")
    
    args = parser.parse_args()
    convert_text_to_csv_with_lengths(args.txt_file, args.layout_csv, args.output_csv)
