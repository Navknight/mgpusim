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

# Set a better grayscale-friendly style with high contrast
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['k', '0.3', '0.5', '0.7', '0.9']) 
# Define distinct line styles and markers for better black and white distinction
line_styles = ['-', '--', '-.', ':', '-']
marker_styles = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

# Function to get distinct visual elements for each dataset
def get_style_elements(index, num_elements):
    """
    Returns distinct style elements (color, line style, marker) for clear differentiation in black and white.
    """
    color_idx = index % 5  # We have 5 grayscale colors
    line_idx = index % len(line_styles)
    marker_idx = index % len(marker_styles)
    
    colors = ['k', '0.3', '0.5', '0.7', '0.9']
    return colors[color_idx], line_styles[line_idx], marker_styles[marker_idx]

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
    
    # Extract L1V cache latency
    # First try exact match for L1V cache latency
    l1v_latency_rows = df[(df['where'].str.contains('L1V')) & 
                          (df['what'].str.contains('req_average_latency'))]
    
    # If not found, try more general search for any vector cache latency
    if l1v_latency_rows.empty:
        l1v_latency_rows = df[(df['where'].str.contains('L1V') | df['where'].str.contains('VCache')) & 
                              (df['what'].str.contains('req_average_latency'))]
    
    metrics['l1v_latency'] = l1v_latency_rows['value'].iloc[0] if not l1v_latency_rows.empty else None
    
    # Extract L2 cache latency
    l2_latency_rows = df[(df['where'].str.contains('L2')) & 
                         (df['what'].str.contains('req_average_latency'))]
    
    metrics['l2_latency'] = l2_latency_rows['value'].iloc[0] if not l2_latency_rows.empty else None
    
    # Extract CPI Stack Idle
    cpi_idle_rows = df[(df['what'].str.contains('CPIStack.Idle', case=False))]
    
    # If not found with the exact pattern, try a more flexible search
    if cpi_idle_rows.empty:
        cpi_idle_rows = df[(df['what'].str.contains('CPI') & df['what'].str.contains('Idle', case=False))]
        
    metrics['cpi_stack_idle'] = cpi_idle_rows['value'].iloc[0] if not cpi_idle_rows.empty else None
    
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
    
    # Create combined throughput and miss reduction plot
    create_combined_throughput_miss_reduction_plot(df, all_results, output_folder)
    
    # Create a combined cache metrics plot
    create_combined_cache_metrics_plot(df, output_folder)
    
    # Create combined L1V and L2 cache latency plots (both normalized and absolute)
    create_combined_latency_plot(df, output_folder)
    create_combined_absolute_latency_plot(df, output_folder)
    
    # Create CPI Stack Idle plot
    create_cpi_stack_idle_plot(df, output_folder)

def create_combined_throughput_miss_reduction_plot(df, all_results, output_folder):
    """
    Create a combined plot showing normalized throughput and miss reduction side by side.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        all_results (dict): Dictionary containing results for all benchmarks.
        output_folder (str): Path to save the output plot.
    """
    # ---------- Prepare throughput data ----------
    # Prepare the throughput data
    df['throughput_billions'] = df['throughput'] / 1e9
    
    # Create normalized throughput data for each benchmark
    throughput_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        if 0 not in benchmark_df['prefetch_degree'].values:
            print(f"Warning: No baseline (prefetch degree 0) found for benchmark '{benchmark}'. Skipping normalization.")
            continue
        
        # Get baseline values for this benchmark
        baseline_throughput = benchmark_df[benchmark_df['prefetch_degree'] == 0]['throughput_billions'].iloc[0]
        
        # Normalize all values by the baseline
        benchmark_df['normalized_throughput'] = benchmark_df['throughput_billions'] / baseline_throughput
        
        throughput_data.append(benchmark_df)
    
    if not throughput_data:
        print("Warning: No data available for normalized throughput plot.")
        return
    
    # Combine all normalized throughput data
    throughput_df = pd.concat(throughput_data)
    
    # ---------- Prepare miss reduction data ----------
    # Create miss reduction data
    reduction_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark]
        
        if 0 not in benchmark_df['prefetch_degree'].values:
            print(f"Warning: No baseline (prefetch degree 0) found for benchmark '{benchmark}'. Skipping calculations.")
            continue
        
        baseline_misses = benchmark_df[benchmark_df['prefetch_degree'] == 0]['read_miss'].iloc[0] if 'read_miss' in benchmark_df.columns else None
        
        if baseline_misses is None or pd.isna(baseline_misses) or baseline_misses == 0:
            continue
            
        for _, row in benchmark_df.iterrows():
            if row['prefetch_degree'] == 0:
                continue  # Skip baseline
            
            # Miss reduction calculation (if data available)
            if pd.notna(row['read_miss']):
                reduction = ((baseline_misses - row['read_miss']) / baseline_misses) * 100
                reduction_data.append({
                    'benchmark': benchmark,
                    'prefetch_degree': row['prefetch_degree'],
                    'miss_reduction': reduction
                })
    
    # Create DataFrame for miss reduction
    reduction_df = pd.DataFrame(reduction_data) if reduction_data else None
    
    if reduction_df is None:
        print("Warning: No data available for miss reduction plot.")
        return
    
    # ---------- Create the combined plot ----------
    # Create a 2-panel figure with improved spacing and dimensions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.subplots_adjust(wspace=0.25)  # Adjust space between panels
    
    # Get all unique benchmarks across both datasets
    all_benchmarks = sorted(set(list(throughput_df['benchmark'].unique()) + 
                         list(reduction_df['benchmark'].unique())))
    num_benchmarks = len(all_benchmarks)
    
    # Create uniform x-axis positions for throughput plot
    throughput_degrees = sorted(throughput_df['prefetch_degree'].unique())
    throughput_x_positions = list(range(len(throughput_degrees)))
    throughput_degree_to_position = dict(zip(throughput_degrees, throughput_x_positions))
    
    # Create uniform x-axis positions for miss reduction plot
    reduction_degrees = sorted(reduction_df['prefetch_degree'].unique())
    reduction_x_positions = list(range(len(reduction_degrees)))
    reduction_degree_to_position = dict(zip(reduction_degrees, reduction_x_positions))
    
    # ---------- Panel 1: Normalized Throughput ----------
    for i, benchmark in enumerate(all_benchmarks):
        benchmark_data = throughput_df[throughput_df['benchmark'] == benchmark]
        
        if benchmark_data.empty:
            continue
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [throughput_degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        # Get distinct visual elements for this benchmark
        color, line_style, marker = get_style_elements(i, num_benchmarks)
        
        ax1.plot(x_vals, benchmark_data['normalized_throughput'], 
                marker=marker, 
                linestyle=line_style,
                color=color,
                label=benchmark, 
                linewidth=2, 
                markersize=8,
                markerfacecolor='white',  # White fill for markers to enhance contrast
                markeredgewidth=1.5)      # Thicker marker edges
    
    ax1.set_title('Normalized Throughput', fontsize=16, pad=15)
    ax1.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax1.set_ylabel('Normalized Throughput', fontsize=14, labelpad=10)
    
    # Add a subtle grid for readability but not too distracting
    ax1.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Add a reference line at y=1 (baseline)
    ax1.axhline(y=1, color='k', linestyle='-', alpha=0.5, linewidth=1.5)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(throughput_x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in throughput_degrees], fontsize=12)
    
    # Improve Y-axis readability
    ax1.yaxis.set_major_locator(plt.MaxNLocator(6))  # Limit number of y-ticks
    ax1.tick_params(axis='y', labelsize=12)
    
    # ---------- Panel 2: Miss Reduction ----------
    for i, benchmark in enumerate(all_benchmarks):
        benchmark_data = reduction_df[reduction_df['benchmark'] == benchmark]
        
        if benchmark_data.empty:
            continue
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [reduction_degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        # Get distinct visual elements for this benchmark
        color, line_style, marker = get_style_elements(i, num_benchmarks)
        
        ax2.plot(x_vals, benchmark_data['miss_reduction'], 
                marker=marker,
                linestyle=line_style,
                color=color,
                label=benchmark, 
                linewidth=2, 
                markersize=8,
                markerfacecolor='white',
                markeredgewidth=1.5)
    
    ax2.set_title('Cache Miss Reduction', fontsize=16, pad=15)
    ax2.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax2.set_ylabel('Miss Reduction (%)', fontsize=14, labelpad=10)
    
    # Add a subtle grid for readability
    ax2.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Improve y-axis visibility
    ax2.yaxis.set_major_locator(plt.MaxNLocator(6))
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax2.set_xticks(reduction_x_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in reduction_degrees], fontsize=12)
    ax2.tick_params(axis='y', labelsize=12)
    
    # Create a single legend for both panels, positioned at the bottom
    handles, labels = ax1.get_legend_handles_labels()
    
    # For better black and white readability, use a horizontal legend below the plot with appropriate spacing
    legend = fig.legend(handles, labels, 
               loc='upper center', 
               bbox_to_anchor=(0.5, 0.1),  # Position at bottom center 
               fontsize=12, 
               frameon=True, 
               fancybox=False, 
               edgecolor='black',
               ncol=min(4, len(all_benchmarks)))
    
    # Make sure legend markers are visible in black and white
    if hasattr(legend, 'legendHandles'):
        for handle in legend.legendHandles:
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    else:
        # Alternative approach using get_lines()
        for handle in legend.get_lines():
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    
    # Adjust layout to make room for the legend
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    
    # Save as PNG with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_throughput_miss_reduction.png'), dpi=300, bbox_inches='tight', pad_inches=0.1)
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
    
    # Create a 2-panel figure with improved spacing and dimensions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.subplots_adjust(wspace=0.25)  # Adjust space between panels
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(normalized_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # Get prefetch degrees (excluding 0 for panel 2)
    prefetch_degrees = [d for d in distinct_degrees if d > 0]
    prefetch_positions = [degree_to_position[d] for d in prefetch_degrees]
    
    # Get sorted benchmarks
    benchmarks = sorted(normalized_df['benchmark'].unique())
    num_benchmarks = len(benchmarks)
    
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
            
            # Get distinct visual elements for this benchmark
            color, line_style, marker = get_style_elements(i, num_benchmarks)
            
            ax1.plot(x_vals, benchmark_data['normalized_hit_rate'], 
                    marker=marker,
                    linestyle=line_style,
                    color=color, 
                    label=benchmark, 
                    linewidth=2, 
                    markersize=8,
                    markerfacecolor='white',
                    markeredgewidth=1.5)
        
    ax1.set_title('Normalized Cache Hit Rate', fontsize=16, pad=15)
    ax1.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax1.set_ylabel('Normalized Hit Rate', fontsize=14, labelpad=10)
    ax1.grid(True, linestyle='--', alpha=0.3, color='gray')
    ax1.axhline(y=1, color='k', linestyle='-', alpha=0.5, linewidth=1.5)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=12)
    ax1.tick_params(axis='y', labelsize=12)
    
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
        
        # Get distinct visual elements for this benchmark
        color, line_style, marker = get_style_elements(i, num_benchmarks)
        
        ax2.plot(x_vals, benchmark_data['prefetch_accuracy'], 
                marker=marker,
                linestyle=line_style,
                color=color, 
                label=benchmark, 
                linewidth=2, 
                markersize=8,
                markerfacecolor='white',
                markeredgewidth=1.5)
    
    ax2.set_title('Prefetch Accuracy', fontsize=16, pad=15)
    ax2.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax2.set_ylabel('Prefetch Accuracy', fontsize=14, labelpad=10)
    ax2.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Set x-ticks for prefetch degrees (excluding 0 for panel 2)
    ax2.set_xticks(prefetch_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in prefetch_degrees], fontsize=12)
    ax2.tick_params(axis='y', labelsize=12)
    
    # Create a single legend for both panels, positioned at the bottom
    handles, labels = ax1.get_legend_handles_labels()
    
    # For better black and white readability, use a horizontal legend below the plot with appropriate spacing
    legend = fig.legend(handles, labels, 
               loc='upper center', 
               bbox_to_anchor=(0.5, 0.1),  # Position at bottom center 
               fontsize=12, 
               frameon=True, 
               fancybox=False, 
               edgecolor='black',
               ncol=min(4, len(benchmarks)))
    
    # Make sure legend markers are visible in black and white
    if hasattr(legend, 'legendHandles'):
        for handle in legend.legendHandles:
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    else:
        # Alternative approach using get_lines()
        for handle in legend.get_lines():
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    
    # Adjust layout to make room for the legend
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    
    # Save as PNG with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_cache_metrics.png'), dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()

def create_combined_latency_plot(df, output_folder):
    """
    Create a combined plot showing L1V and L2 cache request average latency side by side.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output plot.
    """
    # Check if latency data is available
    if ('l1v_latency' not in df.columns or df['l1v_latency'].isna().all()) and \
       ('l2_latency' not in df.columns or df['l2_latency'].isna().all()):
        print("Warning: Neither L1V nor L2 cache latency data available for plotting.")
        return
    
    # Create normalized data for each benchmark
    normalized_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        # Skip benchmarks with insufficient data for both L1V and L2
        if benchmark_df.empty or \
           (benchmark_df['l1v_latency'].isna().all() and benchmark_df['l2_latency'].isna().all()):
            continue
        
        # Normalize L1V latency if baseline exists
        if 0 in benchmark_df['prefetch_degree'].values and 'l1v_latency' in benchmark_df.columns:
            baseline_l1v = benchmark_df[benchmark_df['prefetch_degree'] == 0]['l1v_latency'].iloc[0]
            if baseline_l1v is not None and baseline_l1v > 0:
                benchmark_df['normalized_l1v_latency'] = benchmark_df['l1v_latency'] / baseline_l1v
        
        # Normalize L2 latency if baseline exists
        if 0 in benchmark_df['prefetch_degree'].values and 'l2_latency' in benchmark_df.columns:
            baseline_l2 = benchmark_df[benchmark_df['prefetch_degree'] == 0]['l2_latency'].iloc[0]
            if baseline_l2 is not None and baseline_l2 > 0:
                benchmark_df['normalized_l2_latency'] = benchmark_df['l2_latency'] / baseline_l2
        
        # Only add if we have at least one normalized latency
        if 'normalized_l1v_latency' in benchmark_df.columns or 'normalized_l2_latency' in benchmark_df.columns:
            normalized_data.append(benchmark_df)
    
    if not normalized_data:
        print("Warning: No data available for normalized latency plot.")
        return
    
    # Combine all normalized data
    normalized_df = pd.concat(normalized_data)
    
    # Create a 2-panel figure with improved spacing and dimensions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.subplots_adjust(wspace=0.25)  # Adjust space between panels
    
    # Get all unique benchmarks
    all_benchmarks = sorted(normalized_df['benchmark'].unique())
    num_benchmarks = len(all_benchmarks)
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(normalized_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # ---------- Panel 1: Normalized L1V Latency ----------
    if 'normalized_l1v_latency' in normalized_df.columns:
        for i, benchmark in enumerate(all_benchmarks):
            benchmark_data = normalized_df[(normalized_df['benchmark'] == benchmark) & 
                                         (~normalized_df['normalized_l1v_latency'].isna())]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            # Get distinct visual elements for this benchmark
            color, line_style, marker = get_style_elements(i, num_benchmarks)
            
            ax1.plot(x_vals, benchmark_data['normalized_l1v_latency'], 
                    marker=marker,
                    linestyle=line_style,
                    color=color, 
                    label=benchmark, 
                    linewidth=2, 
                    markersize=8,
                    markerfacecolor='white',
                    markeredgewidth=1.5)
    
    ax1.set_title('Normalized L1V Cache Request Latency', fontsize=16, pad=15)
    ax1.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax1.set_ylabel('Normalized Latency', fontsize=14, labelpad=10)
    ax1.grid(True, linestyle='--', alpha=0.3, color='gray')
    ax1.axhline(y=1, color='k', linestyle='-', alpha=0.5, linewidth=1.5)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=12)
    ax1.tick_params(axis='y', labelsize=12)
    
    # Improve Y-axis readability
    ax1.yaxis.set_major_locator(plt.MaxNLocator(6))
    
    # ---------- Panel 2: Normalized L2 Latency ----------
    if 'normalized_l2_latency' in normalized_df.columns:
        for i, benchmark in enumerate(all_benchmarks):
            benchmark_data = normalized_df[(normalized_df['benchmark'] == benchmark) & 
                                         (~normalized_df['normalized_l2_latency'].isna())]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            # Get distinct visual elements for this benchmark
            color, line_style, marker = get_style_elements(i, num_benchmarks)
            
            ax2.plot(x_vals, benchmark_data['normalized_l2_latency'], 
                    marker=marker,
                    linestyle=line_style,
                    color=color, 
                    label=benchmark, 
                    linewidth=2, 
                    markersize=8,
                    markerfacecolor='white',
                    markeredgewidth=1.5)
    
    ax2.set_title('Normalized L2 Cache Request Latency', fontsize=16, pad=15)
    ax2.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax2.set_ylabel('Normalized Latency', fontsize=14, labelpad=10)
    ax2.grid(True, linestyle='--', alpha=0.3, color='gray')
    ax2.axhline(y=1, color='k', linestyle='-', alpha=0.5, linewidth=1.5)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=12)
    ax2.tick_params(axis='y', labelsize=12)
    
    # Improve Y-axis readability
    ax2.yaxis.set_major_locator(plt.MaxNLocator(6))
    
    # Create a single legend for both panels, positioned at the bottom
    handles, labels = ax1.get_legend_handles_labels()
    if not handles:
        handles, labels = ax2.get_legend_handles_labels()
    
    # For better black and white readability, use a horizontal legend below the plot with appropriate spacing
    legend = fig.legend(handles, labels, 
               loc='upper center', 
               bbox_to_anchor=(0.5, 0.1),  # Position at bottom center 
               fontsize=12, 
               frameon=True, 
               fancybox=False, 
               edgecolor='black',
               ncol=min(4, len(all_benchmarks)))
    
    # Make sure legend markers are visible in black and white
    if hasattr(legend, 'legendHandles'):
        for handle in legend.legendHandles:
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    else:
        # Alternative approach using get_lines()
        for handle in legend.get_lines():
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    
    # Adjust layout to make room for the legend
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    
    # Save as PNG with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_normalized_latency.png'), dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()

def create_combined_absolute_latency_plot(df, output_folder):
    """
    Create a combined plot showing L1V and L2 cache absolute request latency side by side.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output plot.
    """
    # Check if latency data is available
    if ('l1v_latency' not in df.columns or df['l1v_latency'].isna().all()) and \
       ('l2_latency' not in df.columns or df['l2_latency'].isna().all()):
        print("Warning: Neither L1V nor L2 cache latency data available for plotting.")
        return
    
    # Create data for each benchmark with valid latency data
    valid_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        # Skip benchmarks with insufficient data for both L1V and L2
        if benchmark_df.empty or \
           (benchmark_df['l1v_latency'].isna().all() and benchmark_df['l2_latency'].isna().all()):
            continue
        
        valid_data.append(benchmark_df)
    
    if not valid_data:
        print("Warning: No data available for absolute latency plot.")
        return
    
    # Combine all valid data
    valid_df = pd.concat(valid_data)
    
    # Create a 2-panel figure with improved spacing and dimensions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.subplots_adjust(wspace=0.25)  # Adjust space between panels
    
    # Get all unique benchmarks
    all_benchmarks = sorted(valid_df['benchmark'].unique())
    num_benchmarks = len(all_benchmarks)
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(valid_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # ---------- Panel 1: Absolute L1V Latency ----------
    if 'l1v_latency' in valid_df.columns:
        for i, benchmark in enumerate(all_benchmarks):
            benchmark_data = valid_df[(valid_df['benchmark'] == benchmark) & 
                                    (~valid_df['l1v_latency'].isna())]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            # Get distinct visual elements for this benchmark
            color, line_style, marker = get_style_elements(i, num_benchmarks)
            
            ax1.plot(x_vals, benchmark_data['l1v_latency'], 
                    marker=marker,
                    linestyle=line_style,
                    color=color, 
                    label=benchmark, 
                    linewidth=2, 
                    markersize=8,
                    markerfacecolor='white',
                    markeredgewidth=1.5)
    
    ax1.set_title('L1V Cache Request Average Latency', fontsize=16, pad=15)
    ax1.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax1.set_ylabel('Latency (cycles)', fontsize=14, labelpad=10)
    ax1.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=12)
    ax1.tick_params(axis='y', labelsize=12)
    
    # Improve Y-axis readability
    ax1.yaxis.set_major_locator(plt.MaxNLocator(6))
    
    # ---------- Panel 2: Absolute L2 Latency ----------
    if 'l2_latency' in valid_df.columns:
        for i, benchmark in enumerate(all_benchmarks):
            benchmark_data = valid_df[(valid_df['benchmark'] == benchmark) & 
                                    (~valid_df['l2_latency'].isna())]
            
            if benchmark_data.empty:
                continue
            
            # Map degrees to positions for equal spacing
            benchmark_data = benchmark_data.sort_values('prefetch_degree')
            x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
            
            # Get distinct visual elements for this benchmark
            color, line_style, marker = get_style_elements(i, num_benchmarks)
            
            ax2.plot(x_vals, benchmark_data['l2_latency'], 
                    marker=marker,
                    linestyle=line_style,
                    color=color, 
                    label=benchmark, 
                    linewidth=2, 
                    markersize=8,
                    markerfacecolor='white',
                    markeredgewidth=1.5)
    
    ax2.set_title('L2 Cache Request Average Latency', fontsize=16, pad=15)
    ax2.set_xlabel('Prefetch Degree', fontsize=14, labelpad=10)
    ax2.set_ylabel('Latency (cycles)', fontsize=14, labelpad=10)
    ax2.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=12)
    ax2.tick_params(axis='y', labelsize=12)
    
    # Improve Y-axis readability
    ax2.yaxis.set_major_locator(plt.MaxNLocator(6))
    
    # Create a single legend for both panels, positioned at the bottom
    handles, labels = ax1.get_legend_handles_labels()
    if not handles:
        handles, labels = ax2.get_legend_handles_labels()
    
    # For better black and white readability, use a horizontal legend below the plot with appropriate spacing
    legend = fig.legend(handles, labels, 
               loc='upper center', 
               bbox_to_anchor=(0.5, 0.1),  # Position at bottom center 
               fontsize=12, 
               frameon=True, 
               fancybox=False, 
               edgecolor='black',
               ncol=min(4, len(all_benchmarks)))
    
    # Make sure legend markers are visible in black and white
    if hasattr(legend, 'legendHandles'):
        for handle in legend.legendHandles:
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    else:
        # Alternative approach using get_lines()
        for handle in legend.get_lines():
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1.5)
    
    # Adjust layout to make room for the legend
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    
    # Save as PNG with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'combined_absolute_latency.png'), dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()

def create_cpi_stack_idle_plot(df, output_folder):
    """
    Create a compact plot showing normalized CPI Stack Idle across prefetch degrees.
    
    Args:
        df (pandas.DataFrame): DataFrame containing results.
        output_folder (str): Path to save the output plot.
    """
    # Check if CPI Stack Idle data is available
    if 'cpi_stack_idle' not in df.columns or df['cpi_stack_idle'].isna().all():
        print("Warning: CPI Stack Idle data not available for plotting.")
        return
    
    # Create normalized data for each benchmark
    normalized_data = []
    
    for benchmark in df['benchmark'].unique():
        benchmark_df = df[df['benchmark'] == benchmark].copy()
        
        # Skip benchmarks with insufficient data
        if benchmark_df.empty or benchmark_df['cpi_stack_idle'].isna().all():
            continue
        
        # Normalize CPI Stack Idle if baseline exists
        if 0 in benchmark_df['prefetch_degree'].values:
            baseline_cpi = benchmark_df[benchmark_df['prefetch_degree'] == 0]['cpi_stack_idle'].iloc[0]
            if baseline_cpi is not None and baseline_cpi > 0:
                benchmark_df['normalized_cpi_idle'] = benchmark_df['cpi_stack_idle'] / baseline_cpi
        
        # Only add if we have normalized data
        if 'normalized_cpi_idle' in benchmark_df.columns:
            normalized_data.append(benchmark_df)
    
    if not normalized_data:
        print("Warning: No data available for normalized CPI Stack Idle plot.")
        return
    
    # Combine all normalized data
    normalized_df = pd.concat(normalized_data)
    
    # Create a compact figure
    fig, ax = plt.subplots(figsize=(6, 4))  # Smaller size for compactness
    
    # Create uniform x-axis positions
    distinct_degrees = sorted(normalized_df['prefetch_degree'].unique())
    x_positions = list(range(len(distinct_degrees)))
    degree_to_position = dict(zip(distinct_degrees, x_positions))
    
    # Get benchmarks and prepare for plotting
    benchmarks = sorted(normalized_df['benchmark'].unique())
    num_benchmarks = len(benchmarks)
    
    # Create a line for each benchmark with distinct styles
    for i, benchmark in enumerate(benchmarks):
        benchmark_data = normalized_df[normalized_df['benchmark'] == benchmark]
        
        # Map degrees to positions for equal spacing
        benchmark_data = benchmark_data.sort_values('prefetch_degree')
        x_vals = [degree_to_position[degree] for degree in benchmark_data['prefetch_degree']]
        
        # Get distinct visual elements for this benchmark
        color, line_style, marker = get_style_elements(i, num_benchmarks)
        
        ax.plot(x_vals, benchmark_data['normalized_cpi_idle'], 
                marker=marker, 
                linestyle=line_style,
                color=color,
                label=benchmark, 
                linewidth=1.5,  # Slightly thinner lines for compact plot
                markersize=6,   # Smaller markers for compact plot
                markerfacecolor='white',
                markeredgewidth=1)
    
    ax.set_title('Normalized CPI Stack Idle', fontsize=14)
    ax.set_xlabel('Prefetch Degree', fontsize=12)
    ax.set_ylabel('Normalized Value', fontsize=12)
    
    # Add a subtle grid for readability
    ax.grid(True, linestyle='--', alpha=0.2, color='gray')
    
    # Add a reference line at y=1 (baseline)
    ax.axhline(y=1, color='k', linestyle='-', alpha=0.3, linewidth=1)
    
    # Set x-ticks to use evenly spaced positions with degree labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(int(degree)) for degree in distinct_degrees], fontsize=10)
    
    # Improve Y-axis readability
    ax.yaxis.set_major_locator(plt.MaxNLocator(5))  # Fewer ticks for compactness
    ax.tick_params(axis='y', labelsize=10)
    
    # Create a compact legend - if many benchmarks, put it outside to save space
    if num_benchmarks <= 3:
        # For few benchmarks, place legend inside the plot to save space
        legend = ax.legend(loc='best',
                         fontsize=9, 
                         frameon=True, 
                         fancybox=False, 
                         edgecolor='black', 
                         ncol=1)
    else:
        # For many benchmarks, use horizontal layout at bottom
        legend = ax.legend(loc='upper center', 
                         bbox_to_anchor=(0.5, -0.2),
                         fontsize=9, 
                         frameon=True, 
                         fancybox=False, 
                         edgecolor='black', 
                         ncol=min(4, num_benchmarks))
    
    # Make sure legend markers are visible in black and white
    if hasattr(legend, 'legendHandles'):
        for handle in legend.legendHandles:
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1)
    else:
        # Alternative approach using get_lines()
        for handle in legend.get_lines():
            handle.set_markerfacecolor('white')
            handle.set_markeredgewidth(1)
    
    # Tighter layout for compactness
    if num_benchmarks <= 3:
        plt.tight_layout()
    else:
        plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    
    # Save as PNG with high DPI for quality
    plt.savefig(os.path.join(output_folder, 'normalized_cpi_idle.png'), dpi=300, bbox_inches='tight', pad_inches=0.05)
    plt.close()

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
    
    print(f"\nAnalysis complete. Plot images saved to {output_folder}/")

if __name__ == "__main__":
    main()