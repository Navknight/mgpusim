import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from collections import defaultdict
from matplotlib.ticker import MaxNLocator
import matplotlib

plt.rcParams['figure.figsize'] = [7, 5]  # Reduced size for better fit in Overleaf
plt.rcParams['savefig.bbox'] = 'tight'  # Minimize whitespace
plt.rcParams['savefig.pad_inches'] = 0.05  # Minimal padding - reduced further
plt.rcParams['figure.constrained_layout.use'] = True  # Better layout management

# Use standard fonts instead of LaTeX
plt.rcParams['font.family'] = 'serif'

# Increase font size for better readability in papers
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 12  # Increased legend font size

# Set a better grayscale-friendly style
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['k', '0.2', '0.4', '0.6', '0.8']) 
# Use different line styles and markers for better black and white distinction
line_styles = ['-', '--', '-.', ':', '-']
marker_styles = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

# Set style with minimal elements
sns.set_style("ticks")

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
    metrics['write_mshr_hit'] = extract_metric('write-mshr-hit')
    metrics['write_miss'] = extract_metric('write-miss')
    metrics['write_hit'] = extract_metric('write-hit')
    
    # Prefetch metrics
    metrics['prefetch_hits'] = extract_metric('prefetch-hits')
    metrics['total_prefetches'] = extract_metric('total-prefetches')
    metrics['successful_prefetches'] = extract_metric('successful-prefetches')
    
    # As per user feedback, utilization and accuracy are the same thing
    # Just get one of them (prefetch accuracy)
    metrics['prefetch_accuracy'] = extract_metric('prefetch-accuracy')
    
    # Calculate additional metrics
    if metrics['read_hit'] is not None and metrics['read_miss'] is not None:
        metrics['total_accesses'] = metrics['read_hit'] + metrics['read_miss'] + metrics['read_mshr_hit'] + metrics['write_mshr_hit'] + metrics['write_miss'] + metrics['write_hit']
        metrics['hit_rate'] = metrics['read_hit'] / metrics['total_accesses'] * 100
    
    return metrics

# Process all files for a single benchmark
def process_benchmark_files(benchmark_folder):
    """
    Process all CSV files from the specified benchmark folder and extract throughput and prefetch metrics.
    
    Args:
        benchmark_folder (str): Path to the benchmark folder containing CSV files.
        
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
        file_path = os.path.join(benchmark_folder, filename)
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} does not exist. Skipping prefetch degree {degree}...")
            continue
        
        print(f"Processing benchmark '{os.path.basename(benchmark_folder)}', prefetch degree {degree}...")
        
        try:
            df = parse_csv_file(file_path)
            throughput_results = calculate_throughput(df)
            print(f"Instructions: {throughput_results['total_instructions']}, Execution Time: {throughput_results['execution_time']}, Degree: {degree}")
            prefetch_metrics = analyze_prefetch_metrics(df)
            
            results[degree] = {**throughput_results, **prefetch_metrics}
        except Exception as e:
            print(f"Error processing prefetch degree {degree}: {str(e)}")
    
    return results

# Process all benchmarks
def process_all_benchmarks(parent_folder):
    """
    Process all benchmark folders within the parent folder.
    
    Args:
        parent_folder (str): Path to the parent folder containing benchmark folders.
        
    Returns:
        dict: A dictionary containing results for each benchmark and prefetch degree.
    """
    all_results = {}
    
    # Get all benchmark folders
    benchmark_folders = [f for f in os.listdir(parent_folder) 
                         if os.path.isdir(os.path.join(parent_folder, f))]
    
    if not benchmark_folders:
        print(f"No benchmark folders found in {parent_folder}")
        return all_results
    
    print(f"Found {len(benchmark_folders)} benchmark folders: {', '.join(benchmark_folders)}")
    
    for benchmark in benchmark_folders:
        benchmark_path = os.path.join(parent_folder, benchmark)
        print(f"\nProcessing benchmark: {benchmark}")
        
        # Process all files for this benchmark
        benchmark_results = process_benchmark_files(benchmark_path)
        
        if benchmark_results:
            all_results[benchmark] = benchmark_results
        else:
            print(f"No valid results found for benchmark: {benchmark}")
    
    return all_results

# Create comparison plots across benchmarks
def create_comparison_plots(all_results, output_folder):
    """
    Create and save comparison plots across all benchmarks.
    
    Args:
        all_results (dict): Dictionary containing results for all benchmarks.
        output_folder (str): Path to save the output plots.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # Create a DataFrame for easier plotting
    data_rows = []
    
    for benchmark, results in all_results.items():
        for degree, metrics in results.items():
            row = {
                'benchmark': benchmark,
                'prefetch_degree': degree,
                **metrics
            }
            data_rows.append(row)
    
    if not data_rows:
        print("No data to plot.")
        return
    
    df = pd.DataFrame(data_rows)
    
    # Create a combined performance metrics plot
    create_combined_performance_plot(df, output_folder)
    
    # Create a combined cache metrics plot
    create_combined_cache_metrics_plot(df, output_folder)
    
    # Create speedup and miss reduction in one plot
    create_speedup_miss_reduction_plot(df, all_results, output_folder)
    
    # Create summary data
    create_summary_data(df, output_folder)

def create_combined_performance_plot(df, output_folder):
    """
    Create a combined plot showing normalized throughput and execution time.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output plot.
    """
    # Prepare the data
    df['throughput_billions'] = df['throughput'] / 1e9
    df['execution_time_ms'] = df['execution_time'] * 1000
    
    # Create normalized data for each benchmark
    normalized_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        if 0 not in benchmark_df['prefetch_degree'].values:
            print(f"Warning: No baseline (prefetch degree 0) found for benchmark '{benchmark}'. Skipping normalization.")
            continue
        
        # Get baseline values for this benchmark
        baseline_throughput = benchmark_df[benchmark_df['prefetch_degree'] == 0]['throughput_billions'].iloc[0]
        baseline_time = benchmark_df[benchmark_df['prefetch_degree'] == 0]['execution_time_ms'].iloc[0]
        
        # Normalize all values by the baseline
        benchmark_df['normalized_throughput'] = benchmark_df['throughput_billions'] / baseline_throughput
        benchmark_df['normalized_execution_time'] = benchmark_df['execution_time_ms'] / baseline_time
        
        normalized_data.append(benchmark_df)
    
    if not normalized_data:
        print("Warning: No data available for normalized plot.")
        return
    
    # Combine all normalized data
    normalized_df = pd.concat(normalized_data)
    
    # Create a figure with minimal margins
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), constrained_layout=True)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.25, wspace=0.2)
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(normalized_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # Prepare distinct markers and colors for different benchmarks
    benchmarks = normalized_df['benchmark'].unique()
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    # Add formula annotations using proper mathematical notation
    formula1 = r"$\text{Normalized Throughput} = \frac{\text{Throughput}_{\text{degree}}}{\text{Throughput}_{\text{baseline}}}$"
    formula2 = r"$\text{Normalized Exec. Time} = \frac{\text{Exec. Time}_{\text{degree}}}{\text{Exec. Time}_{\text{baseline}}}$"
    
    # Panel 1: Normalized Throughput
    for i, benchmark in enumerate(benchmarks):
        benchmark_data = normalized_df[normalized_df['benchmark'] == benchmark]
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        ax1.plot(x_vals, benchmark_data['normalized_throughput'], 
                marker=markers[i % len(markers)], 
                label=benchmark, 
                linewidth=1.5, 
                markersize=6)
    
    ax1.set_title('Normalized Throughput')
    ax1.set_xlabel('Prefetch Degree')
    ax1.set_ylabel('Normalized Throughput')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.axhline(y=1, color='r', linestyle='--', alpha=0.7)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax1.text(0.5, -0.35, formula1, transform=ax1.transAxes, 
             horizontalalignment='center', fontsize=10)
    
    # Panel 2: Normalized Execution Time
    for i, benchmark in enumerate(benchmarks):
        benchmark_data = normalized_df[normalized_df['benchmark'] == benchmark]
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        ax2.plot(x_vals, benchmark_data['normalized_execution_time'], 
                marker=markers[i % len(markers)], 
                label=benchmark, 
                linewidth=1.5, 
                markersize=6)
    
    ax2.set_title('Normalized Execution Time')
    ax2.set_xlabel('Prefetch Degree')
    ax2.set_ylabel('Normalized Execution Time')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.axhline(y=1, color='r', linestyle='--', alpha=0.7)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in distinct_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax2.text(0.5, -0.35, formula2, transform=ax2.transAxes, 
             horizontalalignment='center', fontsize=10)
    
    # Create a single legend for both panels positioned closer to the graph
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.3),
              fancybox=True, shadow=True, ncol=min(5, len(benchmarks)), fontsize=12)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    
    # Save as PNG only with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_performance_metrics.png'), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close()

def create_combined_cache_metrics_plot(df, output_folder):
    """
    Create a combined plot showing hit rate and prefetch accuracy.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output plot.
    """
    # Check if required metrics are available
    if ('hit_rate' not in df.columns or df['hit_rate'].isna().all() or
        'prefetch_accuracy' not in df.columns or df['prefetch_accuracy'].isna().all()):
        print("Warning: Cache metrics data not available for combined plot.")
        return
    
    # Create normalized data for each benchmark
    normalized_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        # Skip benchmarks with insufficient data
        if benchmark_df.empty or benchmark_df['hit_rate'].isna().all():
            continue
        
        # Normalize hit rate if baseline exists
        if 0 in benchmark_df['prefetch_degree'].values:
            baseline_hit_rate = benchmark_df[benchmark_df['prefetch_degree'] == 0]['hit_rate'].iloc[0]
            if baseline_hit_rate > 0:
                benchmark_df['normalized_hit_rate'] = benchmark_df['hit_rate'] / baseline_hit_rate
        
        # For prefetch accuracy, use the first available value (degree 1 typically)
        df_with_prefetch = benchmark_df[benchmark_df['prefetch_degree'] > 0]
        if not df_with_prefetch.empty and not df_with_prefetch['prefetch_accuracy'].isna().all():
            # Use the lowest degree with valid data as reference
            reference_degrees = sorted(df_with_prefetch['prefetch_degree'].unique())
            for degree in reference_degrees:
                reference_df = df_with_prefetch[df_with_prefetch['prefetch_degree'] == degree]
                if not reference_df['prefetch_accuracy'].isna().all():
                    reference_accuracy = reference_df['prefetch_accuracy'].iloc[0]
                    if reference_accuracy > 0:
                        benchmark_df['normalized_prefetch_accuracy'] = benchmark_df['prefetch_accuracy'] / reference_accuracy
                        break
        
        # Only add if we have at least one normalized metric
        if 'normalized_hit_rate' in benchmark_df.columns or 'normalized_prefetch_accuracy' in benchmark_df.columns:
            normalized_data.append(benchmark_df)
    
    if not normalized_data:
        print("Warning: No data available for normalized cache metrics plot.")
        return
    
    # Combine all normalized data
    normalized_df = pd.concat(normalized_data)
    
    # Create a 2-panel figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.25, wspace=0.2)
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(normalized_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # Get prefetch degrees (excluding 0 for panel 2)
    prefetch_degrees = [d for d in distinct_degrees if d > 0]
    prefetch_positions = [degree_to_position[d] for d in prefetch_degrees]
    
    # Prepare distinct markers and colors for different benchmarks
    benchmarks = normalized_df['benchmark'].unique()
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    # Add formula annotations with proper mathematical notation
    formula1 = r"$\text{Normalized Hit Rate} = \frac{\text{Hit Rate}_{\text{degree}}}{\text{Hit Rate}_{\text{baseline}}}$"
    formula2 = r"$\text{Prefetch Accuracy} = \frac{\text{Prefetch Hits}}{\text{Total Prefetches}}$"
    
    # Panel 1: Normalized Hit Rate
    if 'normalized_hit_rate' in normalized_df.columns:
        for i, benchmark in enumerate(benchmarks):
            benchmark_data = normalized_df[(normalized_df['benchmark'] == benchmark) & 
                                        (~normalized_df['normalized_hit_rate'].isna())]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            ax1.plot(x_vals, benchmark_data['normalized_hit_rate'], 
                    marker=markers[i % len(markers)], 
                    label=benchmark, 
                    linewidth=1.5, 
                    markersize=6)
        
    ax1.set_title('Normalized Cache Hit Rate')
    ax1.set_xlabel('Prefetch Degree')
    ax1.set_ylabel('Normalized Hit Rate')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.axhline(y=1, color='r', linestyle='--', alpha=0.7)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax1.text(0.5, -0.35, formula1, transform=ax1.transAxes, 
            horizontalalignment='center', fontsize=10)
    
    # Panel 2: Prefetch Accuracy (original values, not normalized)
    # Filter out degree 0 which has no prefetching
    df_with_prefetch = normalized_df[normalized_df['prefetch_degree'] > 0]
    
    for i, benchmark in enumerate(benchmarks):
        benchmark_data = df_with_prefetch[(df_with_prefetch['benchmark'] == benchmark) & 
                                      (~df_with_prefetch['prefetch_accuracy'].isna())]
        
        if benchmark_data.empty:
            continue
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        ax2.plot(x_vals, benchmark_data['prefetch_accuracy'], 
                marker=markers[i % len(markers)], 
                label=benchmark, 
                linewidth=1.5, 
                markersize=6)
    
    ax2.set_title('Prefetch Accuracy')
    ax2.set_xlabel('Prefetch Degree')
    ax2.set_ylabel('Prefetch Accuracy')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Set x-ticks for prefetch degrees (excluding 0 for panel 2)
    ax2.set_xticks(prefetch_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in prefetch_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax2.text(0.5, -0.35, formula2, transform=ax2.transAxes, 
            horizontalalignment='center', fontsize=10)
    
    # Create a single legend for both panels positioned closer to the graph
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.3),
              fancybox=True, shadow=True, ncol=min(5, len(benchmarks)))
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    
    # Save as PNG only with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_cache_metrics.png'), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close()

def create_speedup_miss_reduction_plot(df, all_results, output_folder):
    """
    Create a combined plot showing speedup and miss reduction.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        all_results (dict): Dictionary containing results for all benchmarks.
        output_folder (str): Path to save the output plot.
    """
    # Create speedup data
    speedup_data = []
    reduction_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark]
        
        if 0 not in benchmark_df['prefetch_degree'].values:
            print(f"Warning: No baseline (prefetch degree 0) found for benchmark '{benchmark}'. Skipping calculations.")
            continue
        
        baseline_time = benchmark_df[benchmark_df['prefetch_degree'] == 0]['execution_time'].iloc[0]
        baseline_misses = benchmark_df[benchmark_df['prefetch_degree'] == 0]['read_miss'].iloc[0] if 'read_miss' in benchmark_df.columns else None
        
        for _, row in benchmark_df.iterrows():
            if row['prefetch_degree'] == 0:
                continue  # Skip baseline
            
            # Speedup calculation
            speedup = baseline_time / row['execution_time']
            speedup_data.append({
                'benchmark': benchmark,
                'prefetch_degree': row['prefetch_degree'],
                'speedup': speedup
            })
            
            # Miss reduction calculation (if data available)
            if baseline_misses is not None and pd.notna(row['read_miss']) and baseline_misses > 0:
                reduction = ((baseline_misses - row['read_miss']) / baseline_misses) * 100
                reduction_data.append({
                    'benchmark': benchmark,
                    'prefetch_degree': row['prefetch_degree'],
                    'miss_reduction': reduction
                })
    
    # Create DataFrames
    speedup_df = pd.DataFrame(speedup_data) if speedup_data else None
    reduction_df = pd.DataFrame(reduction_data) if reduction_data else None
    
    if speedup_df is None and reduction_df is None:
        print("Warning: No data available for speedup/miss reduction plot.")
        return
    
    # Create a 2-panel figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.25, wspace=0.2)
    
    # Get all unique prefetch degrees across both metrics
    all_degrees = set()
    if speedup_df is not None:
        all_degrees.update(speedup_df['prefetch_degree'].unique())
    if reduction_df is not None:
        all_degrees.update(reduction_df['prefetch_degree'].unique())
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(all_degrees)
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # Get all unique benchmarks
    all_benchmarks = set()
    if speedup_df is not None:
        all_benchmarks.update(speedup_df['benchmark'].unique())
    if reduction_df is not None:
        all_benchmarks.update(reduction_df['benchmark'].unique())
    
    benchmarks = sorted(all_benchmarks)
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    # Add formula annotations with proper mathematical notation
    formula1 = r"$\text{Speedup} = \frac{\text{Exec. Time}_{\text{baseline}}}{\text{Exec. Time}_{\text{degree}}}$"
    formula2 = r"$\text{Miss Reduction(\%)} = \frac{\text{Misses}_{\text{baseline}} - \text{Misses}_{\text{degree}}}{\text{Misses}_{\text{baseline}}} \times 100$"
    
    # Panel 1: Speedup
    if speedup_df is not None:
        for i, benchmark in enumerate(benchmarks):
            benchmark_data = speedup_df[speedup_df['benchmark'] == benchmark]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            ax1.plot(x_vals, benchmark_data['speedup'], 
                    marker=markers[i % len(markers)], 
                    label=benchmark, 
                    linewidth=1.5, 
                    markersize=6)
        
    ax1.set_title('Speedup')
    ax1.set_xlabel('Prefetch Degree')
    ax1.set_ylabel('Speedup (X)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.axhline(y=1, color='r', linestyle='--', alpha=0.7)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax1.text(0.5, -0.35, formula1, transform=ax1.transAxes, 
            horizontalalignment='center', fontsize=10)
    
    # Panel 2: Miss Reduction
    if reduction_df is not None:
        for i, benchmark in enumerate(benchmarks):
            benchmark_data = reduction_df[reduction_df['benchmark'] == benchmark]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            ax2.plot(x_vals, benchmark_data['miss_reduction'], 
                    marker=markers[i % len(markers)], 
                    label=benchmark, 
                    linewidth=1.5, 
                    markersize=6)
    
    ax2.set_title('Cache Miss Reduction')
    ax2.set_xlabel('Prefetch Degree')
    ax2.set_ylabel('Miss Reduction (%)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in distinct_degrees])
    
    # Add formula annotation with proper math notation and more space
    ax2.text(0.5, -0.35, formula2, transform=ax2.transAxes, 
            horizontalalignment='center', fontsize=10)
    
    # Create a single legend for both panels positioned closer to the graph
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.3),
              fancybox=True, shadow=True, ncol=min(5, len(benchmarks)))
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    
    # Save as PNG only with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'speedup_miss_reduction.png'), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close()

def create_summary_data(df, output_folder):
    """
    Create and save summary data as CSV files.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output data.
    """
    # 1. Best prefetch degree for each benchmark
    best_prefetch_degrees = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark]
        
        if benchmark_df.empty:
            continue
        
        # Best throughput
        if 'throughput' in benchmark_df.columns and not benchmark_df['throughput'].isna().all():
            max_throughput_row = benchmark_df.loc[benchmark_df['throughput'].idxmax()]
            best_prefetch_degrees.append({
                'benchmark': benchmark,
                'metric': 'throughput',
                'best_prefetch_degree': max_throughput_row['prefetch_degree'],
                'value': max_throughput_row['throughput'] / 1e9  # Convert to billions
            })
        
        # Best execution time (minimum)
        if 'execution_time' in benchmark_df.columns and not benchmark_df['execution_time'].isna().all():
            min_time_row = benchmark_df.loc[benchmark_df['execution_time'].idxmin()]
            best_prefetch_degrees.append({
                'benchmark': benchmark,
                'metric': 'execution_time',
                'best_prefetch_degree': min_time_row['prefetch_degree'],
                'value': min_time_row['execution_time'] * 1000  # Convert to ms
            })
        
        # Best hit rate
        if 'hit_rate' in benchmark_df.columns and not benchmark_df['hit_rate'].isna().all():
            max_hit_rate_row = benchmark_df.loc[benchmark_df['hit_rate'].idxmax()]
            best_prefetch_degrees.append({
                'benchmark': benchmark,
                'metric': 'hit_rate',
                'best_prefetch_degree': max_hit_rate_row['prefetch_degree'],
                'value': max_hit_rate_row['hit_rate']
            })
    
    if best_prefetch_degrees:
        best_df = pd.DataFrame(best_prefetch_degrees)
        best_df.to_csv(os.path.join(output_folder, 'best_prefetch_degrees.csv'), index=False)
        
        # Create a text summary of best prefetch degrees
        with open(os.path.join(output_folder, 'best_prefetch_degrees_summary.txt'), 'w') as f:
            f.write('Best Prefetch Degrees by Benchmark and Metric\n')
            f.write('==============================================\n\n')
            
            # Write header
            f.write(f"{'Benchmark':<15} {'Metric':<20} {'Best Degree':<12} {'Value':<15}\n")
            f.write('-' * 65 + '\n')
            
            for _, row in best_df.iterrows():
                metric_name = row['metric'].replace('_', ' ').title()
                value_str = f"{row['value']:.2f}"
                if row['metric'] == 'throughput':
                    value_str += " B instr/s"
                elif row['metric'] == 'execution_time':
                    value_str += " ms"
                elif row['metric'] == 'hit_rate':
                    value_str += "%"
                    
                f.write(f"{row['benchmark']:<15} {metric_name:<20} {int(row['best_prefetch_degree']):<12} {value_str:<15}\n")
    
    # 2. Performance improvement summary
    improvement_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark]
        
        if 0 not in benchmark_df['prefetch_degree'].values:
            print(f"Warning: No baseline (prefetch degree 0) found for benchmark '{benchmark}'. Skipping improvement calculation.")
            continue
        
        baseline_row = benchmark_df[benchmark_df['prefetch_degree'] == 0].iloc[0]
        baseline_throughput = baseline_row['throughput']
        baseline_time = baseline_row['execution_time']
        
        for prefetch_degree in sorted(benchmark_df['prefetch_degree'].unique()):
            if prefetch_degree == 0:
                continue  # Skip baseline
            
            degree_row = benchmark_df[benchmark_df['prefetch_degree'] == prefetch_degree].iloc[0]
            
            throughput_improvement = ((degree_row['throughput'] - baseline_throughput) / baseline_throughput) * 100
            time_reduction = ((baseline_time - degree_row['execution_time']) / baseline_time) * 100
            
            improvement_data.append({
                'benchmark': benchmark,
                'prefetch_degree': prefetch_degree,
                'throughput_improvement_percent': throughput_improvement,
                'execution_time_reduction_percent': time_reduction
            })
    
    if improvement_data:
        improvement_df = pd.DataFrame(improvement_data)
        improvement_df.to_csv(os.path.join(output_folder, 'performance_improvements.csv'), index=False)
    
    # 3. Overall summary table
    df_summary = df.copy()
    df_summary['throughput'] = df_summary['throughput'] / 1e9  # Convert to billions
    df_summary['execution_time'] = df_summary['execution_time'] * 1000  # Convert to ms
    
    # Rename columns for clearer understanding
    summary_columns = {
        'benchmark': 'Benchmark',
        'prefetch_degree': 'Prefetch_Degree',
        'throughput': 'Throughput_billion_instr_per_s',
        'execution_time': 'Execution_Time_ms',
        'hit_rate': 'Hit_Rate_percent',
        'total_instructions': 'Total_Instructions',
        'prefetch_hits': 'Prefetch_Hits',
        'total_prefetches': 'Total_Prefetches',
        'successful_prefetches': 'Successful_Prefetches',
        'prefetch_accuracy': 'Prefetch_Accuracy',
        'prefetch_utilization': 'Prefetch_Utilization_percent'
    }
    
    # Select only columns that exist in the DataFrame
    existing_columns = [col for col in summary_columns.keys() if col in df_summary.columns]
    
    df_summary = df_summary[existing_columns].rename(columns={col: summary_columns[col] for col in existing_columns})
    df_summary.to_csv(os.path.join(output_folder, 'overall_summary.csv'), index=False)

def main():
    # Get the parent folder path from command line arguments or use current directory
    if len(sys.argv) > 1:
        parent_folder = sys.argv[1]
    else:
        parent_folder = 'normal'  # Default folder with benchmark subdirectories
    
    # Validate that the folder exists
    if not os.path.exists(parent_folder):
        print(f"Error: The path '{parent_folder}' does not exist.")
        sys.exit(1)
    
    print(f"Using benchmark folders from: {os.path.abspath(parent_folder)}")
    
    # Create output folder for results
    output_folder = os.path.join(parent_folder, 'overleaf_ready_results')
    os.makedirs(output_folder, exist_ok=True)
    print(f"Results will be saved to: {output_folder}")
    
    # Process all benchmarks and get results
    all_results = process_all_benchmarks(parent_folder)
    
    if not all_results:
        print("No valid benchmark results found.")
        sys.exit(1)
    
    # Print basic information about the benchmarks processed
    print("\n=== Benchmarks Processed ===")
    for benchmark, results in all_results.items():
        prefetch_degrees = sorted(results.keys())
        print(f"Benchmark: {benchmark}")
        print(f"  Prefetch degrees: {prefetch_degrees}")
        print(f"  Number of data points: {len(results)}")
    
    # Create comparison plots
    print("\n=== Creating Comparison Plots ===")
    create_comparison_plots(all_results, output_folder)
    
    print(f"\nAnalysis complete. Overleaf-ready results saved to {output_folder}/")

if __name__ == "__main__":
    main()