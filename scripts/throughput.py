import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from collections import defaultdict

# Set the figure size and style for better visualization
plt.rcParams['figure.figsize'] = [12, 8]
sns.set_style("whitegrid")

# Function to parse CSV files
def parse_csv_file(file_path):
    """
    Parse a CSV file and clean up column names.
    
    Args:
        file_path (str): Path to the CSV file.
        
    Returns:
        pandas.DataFrame: The parsed CSV data.
    """
    df = pd.read_csv(file_path)
    # Clean up column names
    df.columns = [col.strip() for col in df.columns]
    return df

# Function to calculate throughput
def calculate_throughput(df):
    """
    Calculate throughput from a dataframe based on CU instruction counts and kernel time.
    Throughput = Total instructions / Total execution time
    
    Args:
        df (pandas.DataFrame): The parsed CSV data.
        
    Returns:
        dict: A dictionary containing throughput, total instructions, and execution time.
    """
    # Get CU instruction counts
    cu_instr_counts = df[(df['where'].str.contains('CU')) & 
                         (df['what'].str.contains('cu_inst_count'))]
    
    # Get kernel time
    kernel_time = df[(df['where'].str.contains('Driver')) & 
                     (df['what'].str.contains('kernel_time'))]
    
    if kernel_time.empty or cu_instr_counts.empty:
        return {'throughput': 0, 'total_instructions': 0, 'execution_time': 0}
    
    # Calculate throughput
    total_instructions = cu_instr_counts['value'].sum()
    execution_time = kernel_time['value'].iloc[0]
    throughput = total_instructions / execution_time
    
    return {
        'throughput': throughput,
        'total_instructions': total_instructions,
        'execution_time': execution_time
    }

# Function to analyze prefetch metrics
def analyze_prefetch_metrics(df):
    """
    Extract and calculate prefetch-related metrics from the dataframe.
    
    Args:
        df (pandas.DataFrame): The parsed CSV data.
        
    Returns:
        dict: A dictionary containing prefetch metrics.
    """
    metrics = {}
    
    # Create a function to safely extract a metric
    def extract_metric(pattern):
        rows = df[df['what'].str.contains(pattern, regex=False)]
        return rows['value'].iloc[0] if not rows.empty else None
    
    # Cache access metrics
    metrics['read_hit'] = extract_metric('read-hit')
    metrics['read_miss'] = extract_metric('read-miss')
    metrics['read_mshr_hit'] = extract_metric('read-mshr-hit')
    
    # Prefetch metrics
    metrics['prefetch_hits'] = extract_metric('prefetch-hits')
    metrics['total_prefetches'] = extract_metric('total-prefetches')
    metrics['successful_prefetches'] = extract_metric('successful-prefetches')
    metrics['prefetch_accuracy'] = extract_metric('prefetch-accuracy')
    metrics['prefetch_utilization'] = extract_metric('prefetch-utilization')
    
    # Calculate additional metrics
    if metrics['read_hit'] is not None and metrics['read_miss'] is not None:
        metrics['total_accesses'] = metrics['read_hit'] + metrics['read_miss']
        metrics['hit_rate'] = metrics['read_hit'] / metrics['total_accesses'] * 100
    
    return metrics

# Process all files
def process_all_files(folder_path):
    """
    Process all CSV files from the specified folder path and extract throughput and prefetch metrics.
    
    Args:
        folder_path (str): Path to the folder containing CSV files.
        
    Returns:
        dict: A dictionary containing results for each prefetch degree.
    """
    # List of prefetch degrees and corresponding files
    prefetch_files = {
        0: 'metrics.csv',  # baseline (no prefetching)
        1: '1.csv',
        2: '2.csv',
        4: '4.csv',
        8: '8.csv',
        16: '16.csv',
        32: '32.csv'
    }
    
    results = {}
    
    for degree, filename in prefetch_files.items():
        file_path = os.path.join(folder_path, filename)
        print(f"Processing prefetch degree {degree} from {file_path}...")
        
        try:
            df = parse_csv_file(file_path)
            throughput_results = calculate_throughput(df)
            prefetch_metrics = analyze_prefetch_metrics(df)
            
            results[degree] = {**throughput_results, **prefetch_metrics}
        except Exception as e:
            print(f"Error processing prefetch degree {degree}: {str(e)}")
    
    return results

def create_basic_performance_plots(df_results, output_folder):
    """
    Create and save basic performance plots.
    
    Args:
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output plots.
    """
    plt.figure(figsize=(12, 8))

    # 1. Throughput vs Prefetch Degree
    plt.subplot(2, 2, 1)
    plt.plot(df_results['prefetch_degree'], df_results['throughput'] / 1e9, marker='o')
    plt.xlabel('Prefetch Degree')
    plt.ylabel('Throughput (billion instr/s)')
    plt.title('Throughput vs Prefetch Degree')
    plt.grid(True)
    # Set x-ticks to exact prefetch degree values
    plt.xticks(df_results['prefetch_degree'], [str(int(degree)) for degree in df_results['prefetch_degree']])

    # 2. Execution Time vs Prefetch Degree
    plt.subplot(2, 2, 2)
    plt.plot(df_results['prefetch_degree'], df_results['execution_time'] * 1000, marker='o')  # Convert to ms
    plt.xlabel('Prefetch Degree')
    plt.ylabel('Execution Time (ms)')
    plt.title('Execution Time vs Prefetch Degree')
    plt.grid(True)
    # Set x-ticks to exact prefetch degree values
    plt.xticks(df_results['prefetch_degree'], [str(int(degree)) for degree in df_results['prefetch_degree']])

    # 3. Hit Rate vs Prefetch Degree
    plt.subplot(2, 2, 3)
    if 'hit_rate' in df_results.columns:
        plt.plot(df_results['prefetch_degree'], df_results['hit_rate'], marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Hit Rate (%)')
        plt.title('Hit Rate vs Prefetch Degree')
        plt.grid(True)
        # Set x-ticks to exact prefetch degree values
        plt.xticks(df_results['prefetch_degree'], [str(int(degree)) for degree in df_results['prefetch_degree']])

    # 4. Prefetch Utilization vs Prefetch Degree
    plt.subplot(2, 2, 4)
    if 'prefetch_utilization' in df_results.columns:
        # Get the exact prefetch degree values (excluding baseline with degree 0)
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        plt.plot(prefetch_degrees, df_results['prefetch_utilization'][1:], marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Prefetch Utilization (%)')
        plt.title('Prefetch Utilization vs Prefetch Degree')
        plt.grid(True)
        # Set x-ticks to exact prefetch degree values
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'prefetch_performance_metrics.png'))
    plt.close()

def create_detailed_prefetch_plots(df_results, output_folder):
    """
    Create and save detailed prefetch metric plots.
    
    Args:
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output plots.
    """
    plt.figure(figsize=(15, 10))

    # 1. Prefetch Hits vs Prefetch Degree
    plt.subplot(2, 2, 1)
    if 'prefetch_hits' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        plt.plot(prefetch_degrees, df_results['prefetch_hits'][1:], marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Prefetch Hits')
        plt.title('Prefetch Hits vs Prefetch Degree')
        plt.grid(True)
        # Set x-ticks to exact prefetch degree values
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    # 2. Total Prefetches vs Prefetch Degree
    plt.subplot(2, 2, 2)
    if 'total_prefetches' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        plt.plot(prefetch_degrees, df_results['total_prefetches'][1:], marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Total Prefetches')
        plt.title('Total Prefetches vs Prefetch Degree')
        plt.grid(True)
        # Set x-ticks to exact prefetch degree values
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    # 3. Successful Prefetches vs Prefetch Degree
    plt.subplot(2, 2, 3)
    if 'successful_prefetches' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        plt.plot(prefetch_degrees, df_results['successful_prefetches'][1:], marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Successful Prefetches')
        plt.title('Successful Prefetches vs Prefetch Degree')
        plt.grid(True)
        # Set x-ticks to exact prefetch degree values
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    # 4. Prefetch Accuracy vs Prefetch Degree (using the provided metric)
    plt.subplot(2, 2, 4)
    if 'prefetch_accuracy' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        prefetch_accuracy = df_results['prefetch_accuracy'][1:].values
        
        plt.plot(prefetch_degrees, prefetch_accuracy, marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Accuracy')
        plt.title('Prefetch Accuracy vs Prefetch Degree')
        plt.grid(True)
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'prefetch_detailed_metrics.png'))
    plt.close()

def create_comparative_prefetch_plots(df_results, output_folder):
    """
    Create and save comparative prefetch metric plots.
    
    Args:
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output plots.
    """
    plt.figure(figsize=(15, 10))

    # 1. Prefetch Hits and Misses
    plt.subplot(2, 2, 1)
    if 'prefetch_hits' in df_results.columns and 'total_prefetches' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        prefetch_hits = df_results['prefetch_hits'][1:].values
        total_prefetches = df_results['total_prefetches'][1:].values
        prefetch_misses = total_prefetches - prefetch_hits
        
        width = 0.35
        x = np.arange(len(prefetch_degrees))
        
        plt.bar(x - width/2, prefetch_hits, width, label='Prefetch Hits')
        plt.bar(x + width/2, prefetch_misses, width, label='Prefetch Misses')
        
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Count')
        plt.title('Prefetch Hits vs Misses')
        plt.xticks(x, [str(int(degree)) for degree in prefetch_degrees])
        plt.legend()
        plt.grid(True, axis='y')

    # # 2. Prefetch Hits to Cache Hits Ratio
    # plt.subplot(2, 2, 2)
    # if 'prefetch_hits' in df_results.columns and 'read_hit' in df_results.columns:
    #     prefetch_degrees = df_results['prefetch_degree'][1:].values
    #     prefetch_hits = df_results['prefetch_hits'][1:].values
    #     read_hits = df_results['read_hit'][1:].values
        
    #     # Calculate ratio of prefetch hits to all cache hits
    #     prefetch_hit_ratio = prefetch_hits / read_hits * 100
        
    #     plt.plot(prefetch_degrees, prefetch_hit_ratio, marker='o')
    #     plt.xlabel('Prefetch Degree')
    #     plt.ylabel('Percentage (%)')
    #     plt.title('Prefetch Hits to Total Cache Hits Ratio')
    #     plt.grid(True)
    #     plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    # 3. Prefetch Impact on Cache Miss Reduction
    plt.subplot(2, 2, 2)
    if 'read_miss' in df_results.columns:
        miss_reduction = []
        baseline_misses = df_results[df_results['prefetch_degree'] == 0]['read_miss'].values[0]
        
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        for degree in prefetch_degrees:
            current_misses = df_results[df_results['prefetch_degree'] == degree]['read_miss'].values[0]
            reduction = (baseline_misses - current_misses) / baseline_misses * 100
            miss_reduction.append(reduction)
        
        plt.plot(prefetch_degrees, miss_reduction, marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Miss Reduction (%)')
        plt.title('Cache Miss Reduction vs Prefetch Degree')
        plt.grid(True)
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    # 4. Prefetch Success Rate vs Prefetch Degree
    plt.subplot(2, 2, 3)
    if 'successful_prefetches' in df_results.columns and 'total_prefetches' in df_results.columns:
        prefetch_degrees = df_results['prefetch_degree'][1:].values
        successful_prefetches = df_results['successful_prefetches'][1:].values
        total_prefetches = df_results['total_prefetches'][1:].values
        
        # Calculate success rate
        success_rate = successful_prefetches / total_prefetches * 100
        
        plt.plot(prefetch_degrees, success_rate, marker='o')
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Success Rate (%)')
        plt.title('Prefetch Success Rate vs Prefetch Degree')
        plt.grid(True)
        plt.xticks(prefetch_degrees, [str(int(degree)) for degree in prefetch_degrees])

    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'prefetch_comparative_metrics.png'))
    plt.close()

def create_performance_improvement_plots(results, df_results, output_folder):
    """
    Create and save performance improvement plots.
    
    Args:
        results (dict): Dictionary containing the results.
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output plots.
    """
    baseline = results[0]
    if baseline:
        # Calculate improvements for each prefetch degree
        improvements = []
        for degree in sorted(results.keys()):
            if degree == 0:
                continue  # Skip baseline
            
            result = results[degree]
            throughput_improvement = ((result['throughput'] - baseline['throughput']) / baseline['throughput']) * 100
            time_reduction = ((baseline['execution_time'] - result['execution_time']) / baseline['execution_time']) * 100
            hit_rate_improvement = None
            
            if 'hit_rate' in result and 'hit_rate' in baseline:
                hit_rate_improvement = result['hit_rate'] - baseline['hit_rate']
            
            improvements.append({
                'prefetch_degree': degree,
                'throughput_improvement': throughput_improvement,
                'time_reduction': time_reduction,
                'hit_rate_improvement': hit_rate_improvement
            })
        
        df_improvements = pd.DataFrame(improvements)
        
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 3, 1)
        plt.bar(range(len(df_improvements)), df_improvements['throughput_improvement'])
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Improvement (%)')
        plt.title('Throughput Improvement vs Baseline')
        plt.grid(True, axis='y')
        plt.xticks(range(len(df_improvements)), [str(int(degree)) for degree in df_improvements['prefetch_degree']])
        
        plt.subplot(1, 3, 2)
        plt.bar(range(len(df_improvements)), df_improvements['time_reduction'])
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Reduction (%)')
        plt.title('Execution Time Reduction vs Baseline')
        plt.grid(True, axis='y')
        plt.xticks(range(len(df_improvements)), [str(int(degree)) for degree in df_improvements['prefetch_degree']])
        
        if 'hit_rate_improvement' in df_improvements.columns and df_improvements['hit_rate_improvement'].notna().any():
            plt.subplot(1, 3, 3)
            plt.bar(range(len(df_improvements)), df_improvements['hit_rate_improvement'])
            plt.xlabel('Prefetch Degree')
            plt.ylabel('Improvement (% points)')
            plt.title('Hit Rate Improvement vs Baseline')
            plt.grid(True, axis='y')
            plt.xticks(range(len(df_improvements)), [str(int(degree)) for degree in df_improvements['prefetch_degree']])
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, 'performance_improvements.png'))
        plt.close()

def create_read_hits_misses_plot(df_results, output_folder):
    """
    Create and save read hits vs misses plot.
    
    Args:
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output plots.
    """
    if 'read_hit' in df_results.columns and 'read_miss' in df_results.columns:
        plt.figure(figsize=(10, 6))
        
        x = np.arange(len(df_results))
        width = 0.35
        
        plt.bar(x - width/2, df_results['read_hit'], width, label='Read Hits')
        plt.bar(x + width/2, df_results['read_miss'], width, label='Read Misses')
        
        plt.xlabel('Prefetch Degree')
        plt.ylabel('Count')
        plt.title('Read Hits vs Misses by Prefetch Degree')
        plt.xticks(x, [str(int(degree)) for degree in df_results['prefetch_degree']])
        plt.legend()
        plt.grid(True, axis='y')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, 'read_hits_misses.png'))
        plt.close()

def create_summary_tables(results, df_results, output_folder):
    """
    Create and save summary tables as CSV files.
    
    Args:
        results (dict): Dictionary containing the results.
        df_results (pandas.DataFrame): DataFrame containing the results.
        output_folder (str): Path to save the output tables.
    """
    # Create a summary table with key metrics
    summary_metrics = df_results[['prefetch_degree', 'throughput', 'execution_time', 'hit_rate']].copy()
    summary_metrics['throughput'] = summary_metrics['throughput'] / 1e9  # Convert to billions
    summary_metrics['execution_time'] = summary_metrics['execution_time'] * 1000  # Convert to ms

    # Rename columns for better display
    summary_metrics.columns = ['Prefetch_Degree', 'Throughput_billion_instr_per_s', 'Execution_Time_ms', 'Hit_Rate_percent']

    # Calculate improvement columns
    if len(summary_metrics) > 1:
        base_throughput = summary_metrics.iloc[0]['Throughput_billion_instr_per_s']
        base_time = summary_metrics.iloc[0]['Execution_Time_ms']
        base_hit_rate = summary_metrics.iloc[0]['Hit_Rate_percent']
        
        summary_metrics['Throughput_Improvement_percent'] = 0.0
        summary_metrics['Time_Reduction_percent'] = 0.0
        summary_metrics['Hit_Rate_Improvement_percent_points'] = 0.0
        
        for i in range(1, len(summary_metrics)):
            summary_metrics.loc[i, 'Throughput_Improvement_percent'] = \
                ((summary_metrics.iloc[i]['Throughput_billion_instr_per_s'] - base_throughput) / base_throughput) * 100
                
            summary_metrics.loc[i, 'Time_Reduction_percent'] = \
                ((base_time - summary_metrics.iloc[i]['Execution_Time_ms']) / base_time) * 100
                
            summary_metrics.loc[i, 'Hit_Rate_Improvement_percent_points'] = \
                summary_metrics.iloc[i]['Hit_Rate_percent'] - base_hit_rate

    # Create a summary table for prefetch metrics
    prefetch_metrics = df_results[['prefetch_degree', 'prefetch_hits', 'total_prefetches', 
                                  'successful_prefetches', 'prefetch_accuracy']].copy()

    # Rename columns for better display
    prefetch_metrics.columns = ['Prefetch_Degree', 'Prefetch_Hits', 'Total_Prefetches', 
                               'Successful_Prefetches', 'Prefetch_Accuracy']

    # Save the summary tables as CSV files
    summary_metrics.to_csv(os.path.join(output_folder, 'performance_summary.csv'), index=False)
    prefetch_metrics.to_csv(os.path.join(output_folder, 'prefetch_metrics_summary.csv'), index=False)
    
    # Also save the full results DataFrame
    df_results.to_csv(os.path.join(output_folder, 'full_results.csv'), index=False)

def main():
    # Get the folder path from command line arguments or use current directory
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = '.'
    
    # Validate that the folder exists
    if not os.path.exists(folder_path):
        print(f"Error: The path '{folder_path}' does not exist.")
        sys.exit(1)
    
    print(f"Using CSV files from: {os.path.abspath(folder_path)}")
    
    # Check if all required CSV files exist
    required_files = ['metrics.csv', '1.csv', '2.csv', '4.csv', '8.csv', '16.csv', '32.csv']
    missing_files = []
    
    for file in required_files:
        file_path = os.path.join(folder_path, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        print(f"Warning: The following required files are missing: {', '.join(missing_files)}")
        proceed = input("Do you want to proceed anyway? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(0)
    else:
        print("All required CSV files found.")
    
    # Create output folder for results
    output_folder = os.path.join(folder_path, 'analysis_results')
    os.makedirs(output_folder, exist_ok=True)
    print(f"Results will be saved to: {output_folder}")
    
    # Process all files and get results
    results = process_all_files(folder_path)
    
    # Convert results to DataFrame for easier analysis
    df_results = pd.DataFrame.from_dict(results, orient='index')
    df_results.index.name = 'prefetch_degree'
    df_results.reset_index(inplace=True)
    
    # Print basic results
    print("\n=== Throughput Analysis ===")
    print(df_results[['prefetch_degree', 'throughput', 'execution_time', 'total_instructions']])
    
    # Calculate improvement compared to baseline
    baseline = results.get(0)
    if baseline:
        print("\n=== Performance Improvement vs Baseline ===")
        for degree in sorted(results.keys()):
            if degree == 0:
                continue  # Skip baseline
            
            result = results[degree]
            throughput_improvement = ((result['throughput'] - baseline['throughput']) / baseline['throughput']) * 100
            time_reduction = ((baseline['execution_time'] - result['execution_time']) / baseline['execution_time']) * 100
            
            print(f"\nPrefetch Degree {degree}:")
            print(f"  Throughput Improvement: {throughput_improvement:.2f}%")
            print(f"  Execution Time Reduction: {time_reduction:.2f}%")
    
    # Create visualizations
    create_basic_performance_plots(df_results, output_folder)
    create_detailed_prefetch_plots(df_results, output_folder)
    create_comparative_prefetch_plots(df_results, output_folder)
    create_performance_improvement_plots(results, df_results, output_folder)
    create_read_hits_misses_plot(df_results, output_folder)
    
    # Create summary tables
    create_summary_tables(results, df_results, output_folder)
    
    print(f"\nAnalysis complete. Results saved to {output_folder}/")

if __name__ == "__main__":
    main()