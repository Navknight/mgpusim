# Import necessary libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def categorize_components(df):
    """Categorize components by their type (L1VCache, L2, etc.)"""
    # Create a mapping of components by type
    component_types = {}
    
    # Handle column name variations
    where_col = None
    for col in df.columns:
        if col.strip() == 'where' or col == ' where':
            where_col = col
            break
    
    if where_col is None:
        print("Warning: Could not find 'where' column in the data")
        return {}
        
    # Process each row to categorize components
    for _, row in df.iterrows():
        if pd.notna(row[where_col]):
            component = str(row[where_col]).strip()
            
            # Extract component type based on naming patterns
            if 'L1VCache' in component:
                component_type = 'L1VCache'
            elif 'L1ICache' in component:
                component_type = 'L1ICache'
            elif 'L1SCache' in component:
                component_type = 'L1SCache'
            elif 'L2[' in component:
                component_type = 'L2'
            elif 'L1VTLB' in component:
                component_type = 'L1VTLB'
            elif 'L1STLB' in component:
                component_type = 'L1STLB'
            elif 'L1ITLB' in component:
                component_type = 'L1ITLB'
            elif 'L2TLB' in component:
                component_type = 'L2TLB'
            elif 'CU[' in component:
                component_type = 'CU'
            elif 'CommandProcessor' in component:
                component_type = 'CommandProcessor'
            elif 'Driver' in component:
                component_type = 'Driver'
            else:
                component_type = 'Other'
            
            # Add to the component type dictionary
            if component_type not in component_types:
                component_types[component_type] = set()
            component_types[component_type].add(component)
    
    # Convert sets to lists for easier handling
    for component_type in component_types:
        component_types[component_type] = list(component_types[component_type])
    
    return component_types

def get_metrics_for_component_type(df, component_type, components):
    """Get all metrics for a specific component type"""
    metrics = set()
    
    # Handle column name variations
    where_col = None
    what_col = None
    
    for col in df.columns:
        if col.strip() == 'where' or col == ' where':
            where_col = col
        if col.strip() == 'what' or col == ' what':
            what_col = col
    
    if where_col is None or what_col is None:
        print(f"Warning: Could not find required columns. Found columns: {df.columns.tolist()}")
        return []
    
    # Extract all metrics for the components of this type
    for component in components:
        component_data = df[df[where_col].astype(str).str.strip() == component]
        component_metrics = component_data[what_col].dropna().unique()
        for metric in component_metrics:
            if isinstance(metric, str):
                metrics.add(metric.strip())
            else:
                metrics.add(str(metric))
    
    return sorted(list(metrics))

def calculate_metric_stats(df, component_type, components, metric):
    """Calculate sum and average for a specific metric across all components of a type"""
    values = []
    
    # Handle column name variations
    where_col = None
    what_col = None
    value_col = None
    
    for col in df.columns:
        if col.strip() == 'where' or col == ' where':
            where_col = col
        if col.strip() == 'what' or col == ' what':
            what_col = col
        if col.strip() == 'value' or col == ' value':
            value_col = col
    
    if where_col is None or what_col is None or value_col is None:
        print(f"Warning: Could not find required columns. Found: {df.columns.tolist()}")
        return {
            'sum': 0,
            'average': 0,
            'count': 0,
            'min': 0,
            'max': 0
        }
    
    for component in components:
        # Filter data for this component and metric
        component_metric_data = df[
            (df[where_col].astype(str).str.strip() == component) & 
            (df[what_col].astype(str).str.strip() == metric)
        ]
        
        if not component_metric_data.empty:
            # Convert to numeric, handling any non-numeric values
            numeric_values = pd.to_numeric(component_metric_data[value_col], errors='coerce')
            # Filter out NaN values that result from conversion errors
            valid_values = numeric_values.dropna().tolist()
            values.extend(valid_values)
    
    # Calculate statistics
    if values:
        return {
            'sum': sum(values),
            'average': sum(values) / len(values),
            'count': len(values),
            'min': min(values),
            'max': max(values)
        }
    else:
        return {
            'sum': 0,
            'average': 0,
            'count': 0,
            'min': 0,
            'max': 0
        }

def direct_analysis(df1, df2, file1_name, file2_name):
    """Non-widget based analysis function using direct input"""
    # Categorize components
    component_types1 = categorize_components(df1)
    component_types2 = categorize_components(df2)
    
    # Get all component types
    all_component_types = sorted(list(set(list(component_types1.keys()) + list(component_types2.keys()))))
    
    while True:
        # Print available component types
        print("\nAvailable component types:")
        for i, comp_type in enumerate(all_component_types):
            print(f"{i+1}. {comp_type}")
        
        try:
            # Get component type selection
            comp_idx = int(input("\nEnter the number of the component type to analyze (or 0 to exit): ")) - 1
            
            if comp_idx == -1:  # User entered 0
                print("Exiting analysis.")
                break
                
            selected_type = all_component_types[comp_idx]
            
            # Get metrics for the selected component
            metrics1 = set()
            metrics2 = set()
            
            if selected_type in component_types1:
                metrics1 = set(get_metrics_for_component_type(
                    df1, selected_type, component_types1[selected_type]))
                    
            if selected_type in component_types2:
                metrics2 = set(get_metrics_for_component_type(
                    df2, selected_type, component_types2[selected_type]))
            
            all_metrics = sorted(list(metrics1.union(metrics2)))
            
            if not all_metrics:
                print(f"No metrics found for {selected_type} in either file.")
                continue
            
            # Print available metrics
            print(f"\nAvailable metrics for {selected_type}:")
            for i, metric in enumerate(all_metrics):
                print(f"{i+1}. {metric}")
            
            # Get metric selection
            metric_idx = int(input("\nEnter the number of the metric to analyze: ")) - 1
            selected_metric = all_metrics[metric_idx]
            
            # Perform analysis
            # Check if the component type exists in each file
            has_type_in_file1 = selected_type in component_types1
            has_type_in_file2 = selected_type in component_types2
            
            # Initialize results for both files
            stats1 = None
            stats2 = None
            
            # Calculate statistics for file 1 if component type exists
            if has_type_in_file1:
                components1 = component_types1[selected_type]
                stats1 = calculate_metric_stats(df1, selected_type, components1, selected_metric)
            
            # Calculate statistics for file 2 if component type exists
            if has_type_in_file2:
                components2 = component_types2[selected_type]
                stats2 = calculate_metric_stats(df2, selected_type, components2, selected_metric)
            
            # Display results
            print(f"\nAnalysis for Component: {selected_type}, Metric: {selected_metric}\n")
            
            # Create comparison table
            headers = ["Statistic", f"File 1: {os.path.basename(file1_name)}", 
                      f"File 2: {os.path.basename(file2_name)}", "Difference", "% Change"]
            rows = []
            
            for stat in ['count', 'sum', 'average', 'min', 'max']:
                val1 = stats1[stat] if stats1 else "N/A"
                val2 = stats2[stat] if stats2 else "N/A"
                
                # Calculate difference and percent change if both values are numeric
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    diff = val2 - val1
                    
                    if val1 != 0:
                        pct_change = (diff / val1) * 100
                        pct_change_str = f"{pct_change:.2f}%"
                    else:
                        pct_change_str = "N/A (div by 0)"
                else:
                    diff = "N/A"
                    pct_change_str = "N/A"
                
                rows.append([stat.capitalize(), val1, val2, diff, pct_change_str])
            
            # Format and display the table
            col_widths = [15, 25, 25, 15, 15]
            
            # Print header
            header_row = ""
            for i, header in enumerate(headers):
                header_row += f"{header:{col_widths[i]}}"
            print(header_row)
            print("-" * sum(col_widths))
            
            # Print rows
            for row in rows:
                row_str = ""
                for i, cell in enumerate(row):
                    if isinstance(cell, float):
                        cell_str = f"{cell:.6g}"
                    else:
                        cell_str = str(cell)
                    row_str += f"{cell_str:{col_widths[i]}}"
                print(row_str)
            
            # If we have data from both files, display a visualization
            if stats1 and stats2:
                # Ask user if they want to see visualization
                show_plot = input("\nDo you want to see visualization? (y/n): ").lower().strip()
                if show_plot == 'y':
                    # Create a comparison bar chart for the sum and average
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
                    
                    # Data for plotting
                    labels = [os.path.basename(file1_name), os.path.basename(file2_name)]
                    sum_values = [stats1['sum'], stats2['sum']]
                    avg_values = [stats1['average'], stats2['average']]
                    
                    # Sum plot
                    ax1.bar(labels, sum_values, color=['blue', 'orange'])
                    ax1.set_title(f'Sum of {selected_metric} for {selected_type}')
                    ax1.set_ylabel('Sum')
                    
                    # Add values on bars
                    for i, v in enumerate(sum_values):
                        ax1.text(i, v * 1.01, f"{v:.4g}", ha='center')
                    
                    # Average plot
                    ax2.bar(labels, avg_values, color=['blue', 'orange'])
                    ax2.set_title(f'Average of {selected_metric} for {selected_type}')
                    ax2.set_ylabel('Average')
                    
                    # Add values on bars
                    for i, v in enumerate(avg_values):
                        ax2.text(i, v * 1.01, f"{v:.4g}", ha='center')
                    
                    plt.tight_layout()
                    
                    # Ask user if they want to save the plot
                    save_plot = input("\nDo you want to save the plot? (y/n): ").lower().strip()
                    if save_plot == 'y':
                        filename = f"{selected_type}_{selected_metric}_comparison.png"
                        plt.savefig(filename)
                        print(f"Plot saved as {filename}")
                    
                    plt.show()
                    
            # Ask if user wants to continue with another analysis
            continue_analysis = input("\nDo you want to analyze another component/metric? (y/n): ").lower().strip()
            if continue_analysis != 'y':
                print("Exiting analysis.")
                break
                
        except (ValueError, IndexError) as e:
            print(f"Invalid input. Please try again. Error: {str(e)}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def load_files_by_path(file1_path, file2_path):
    """Load CSV files from paths specified directly"""
    try:
        # Read CSV files with robust error handling
        print(f"Loading files:\n1. {file1_path}\n2. {file2_path}")
        
        try:
            # First attempt with standard options and whitespace handling
            df1 = pd.read_csv(file1_path, skipinitialspace=True)
            df2 = pd.read_csv(file2_path, skipinitialspace=True)
        except Exception as e:
            print(f"Standard loading failed: {str(e)}\nTrying alternative loading method...")
            # Second attempt with more flexible parsing
            df1 = pd.read_csv(file1_path, sep=None, engine='python')
            df2 = pd.read_csv(file2_path, sep=None, engine='python')
        
        # Print column information for verification
        print(f"\nFile 1 columns: {df1.columns.tolist()}")
        print(f"File 2 columns: {df2.columns.tolist()}")
        
        # Clean up column names (removing extra spaces)
        df1.columns = [col.strip() if isinstance(col, str) else col for col in df1.columns]
        df2.columns = [col.strip() if isinstance(col, str) else col for col in df2.columns]
        
        print(f"\nFiles loaded successfully. Starting analysis...")
        
        # Process the data using direct input rather than widgets
        direct_analysis(df1, df2, file1_path, file2_path)
        
    except Exception as e:
        print(f"Error loading files: {str(e)}")
        print("\nPlease check that the file paths are correct and that the files exist.")

# Set the paths to your CSV files here
file1_path = "/home/abhinav/btp/mgpusim/scripts/normal/stencil2d/metrics.csv"  # Replace if needed
file2_path = "/home/abhinav/btp/mgpusim/scripts/normal/stencil2d/8.csv"  # Replace if needed

# Run the analysis
load_files_by_path(file1_path, file2_path)
