import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

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
        return None
    print(f"Found {len(csv_files)} files to merge: {csv_files}")
    
    # Create an empty list to store dataframes
    dfs = []
    
    # Read each CSV file and append to the list
    for file in csv_files:
        try:
            # Add a new column with the source filename
            df = pd.read_csv(file, skip_blank_lines=True)
            # Additional filtering to remove rows that might contain only NaN or whitespace
            df = df.dropna(how='all')
            # Add source filename column with just the basename
            df['OriginalFile'] = os.path.basename(file)
            # Extract benchmark name from the file path
            # Path format is normal/{benchmark}/GPU_*.csv
            benchmark_path = os.path.dirname(file)  # Gets normal/{benchmark}
            benchmark_name = os.path.basename(benchmark_path)  # Gets {benchmark}
            df['Benchmark'] = benchmark_name
            
            dfs.append(df)
            print(f"Processed: {file} with {len(df)} rows from benchmark {benchmark_name}")
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
        print("Data sorted by Time column")
        return combined_df
    else:
        print("No data to merge.")
        return None

def analyze_eviction_patterns(combined_df):
    """
    Analyze eviction patterns from the combined dataframe.
    Assumes there's an 'Eviction' or similar column in the dataframe.
    
    Args:
        combined_df (DataFrame): The combined dataframe
    
    Returns:
        DataFrame: Summary of eviction statistics by benchmark
    """
    # Identify the eviction column (might be named differently)
    eviction_columns = [col for col in combined_df.columns if 'evict' in col.lower()]
    
    if not eviction_columns:
        print("No eviction-related columns found!")
        return None
        
    eviction_col = eviction_columns[0]
    print(f"Using '{eviction_col}' as the eviction indicator column")
    
    # Extract benchmark name from the original file
    combined_df['Benchmark'] = combined_df['OriginalFile'].apply(
        lambda x: x.split('_')[0] if '_' in x else os.path.splitext(x)[0]
    )
    
    # Calculate eviction statistics per benchmark
    eviction_stats = combined_df.groupby('Benchmark').agg({
        eviction_col: ['count', 'sum', 'mean'],
        'Time': ['min', 'max']
    })
    
    # Flatten the column hierarchy
    eviction_stats.columns = ['_'.join(col).strip() for col in eviction_stats.columns.values]
    
    # Calculate eviction rate (evictions per time unit)
    eviction_stats['time_span'] = eviction_stats['Time_max'] - eviction_stats['Time_min']
    eviction_stats['eviction_rate'] = eviction_stats[f'{eviction_col}_sum'] / eviction_stats['time_span']
    
    return eviction_stats

def analyze_dead_blocks(combined_df):
    """
    Analyze dead blocks from the dataframe.
    Assumes there are columns indicating when blocks are dead.
    
    Args:
        combined_df (DataFrame): The combined dataframe
    
    Returns:
        DataFrame: Summary of dead block statistics by benchmark
    """
    # Look for dead block related columns
    dead_block_cols = [col for col in combined_df.columns 
                       if any(term in col.lower() for term in ['dead', 'unused', 'stale', 'lifetime'])]
    
    if not dead_block_cols:
        print("No dead block related columns found!")
        return None
        
    print(f"Found potential dead block columns: {dead_block_cols}")
    
    # For this example, let's assume we have a column that indicates block lifetime
    # If you have a different structure, you'll need to adjust this logic
    lifetime_col = next((col for col in dead_block_cols if 'lifetime' in col.lower()), None)
    
    if lifetime_col:
        # Extract benchmark name if not already done
        if 'Benchmark' not in combined_df.columns:
            combined_df['Benchmark'] = combined_df['OriginalFile'].apply(
                lambda x: x.split('_')[0] if '_' in x else os.path.splitext(x)[0]
            )
        
        # Calculate lifetime statistics per benchmark
        lifetime_stats = combined_df.groupby('Benchmark').agg({
            lifetime_col: ['count', 'mean', 'median', 'std', 'min', 'max']
        })
        
        # Flatten the column hierarchy
        lifetime_stats.columns = ['_'.join(col).strip() for col in lifetime_stats.columns.values]
        
        return lifetime_stats
    
    return None

def visualize_eviction_heatmap(benchmark_root):
    """
    Create a heatmap visualization of eviction patterns across all benchmarks.
    
    Args:
        benchmark_root (str): Root directory containing benchmark folders (normal/{benchmark})
    """
    # Get all benchmark directories under normal/
    benchmark_dirs = []
    try:
        for d in os.listdir(benchmark_root):
            full_path = os.path.join(benchmark_root, d)
            if os.path.isdir(full_path):
                benchmark_dirs.append(full_path)
    except Exception as e:
        print(f"Error accessing benchmark root directory: {e}")
        return None
    
    print(f"Found {len(benchmark_dirs)} benchmark directories: {[os.path.basename(d) for d in benchmark_dirs]}")
    
    all_data = []
    benchmark_names = []
    
    for bench_dir in benchmark_dirs:
        # Extract benchmark name from folder name (normal/{benchmark})
        benchmark_name = os.path.basename(bench_dir)
        benchmark_names.append(benchmark_name)
        print(f"Processing benchmark: {benchmark_name}")
        
        # Merge all CSV files in this benchmark directory
        merged_file = os.path.join(bench_dir, "merged.csv")
        combined_df = merge_csv_files(os.path.join(bench_dir, "GPU_*.csv"), merged_file)
        
        if combined_df is not None:
            # Add benchmark name and add to collection
            combined_df['Benchmark'] = benchmark_name
            all_data.append(combined_df)
    
    if not all_data:
        print("No data found across benchmarks!")
        return
    
    # Combine all benchmark data
    master_df = pd.concat(all_data, ignore_index=True)
    
    # Identify the eviction column
    eviction_columns = [col for col in master_df.columns if 'evict' in col.lower()]
    
    if not eviction_columns:
        print("No eviction-related columns found!")
        return
        
    eviction_col = eviction_columns[0]
    
    # Create time-series bins for consistent comparison across benchmarks
    # Normalize time to percentage of total execution time per benchmark
    master_df['NormalizedTime'] = master_df.groupby('Benchmark')['Time'].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) * 100
    )
    
    # Create time bins (e.g., 100 bins from 0-100%)
    bins = 100
    master_df['TimeBin'] = pd.cut(master_df['NormalizedTime'], bins=bins, labels=False)
    
    # Calculate eviction density per time bin per benchmark
    eviction_density = master_df.groupby(['Benchmark', 'TimeBin'])[eviction_col].mean().unstack()
    
    # Replace NaN with 0 for visualization
    eviction_density = eviction_density.fillna(0)
    
    # Create a custom colormap for the heatmap
    colors = ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"]
    cmap = LinearSegmentedColormap.from_list("custom_blue", colors)
    
    # Plot heatmap
    plt.figure(figsize=(16, 10))
    ax = sns.heatmap(eviction_density, cmap=cmap, robust=True, 
                     cbar_kws={'label': 'Eviction Density'})
    
    plt.title('Eviction Patterns Across Benchmarks', fontsize=16)
    plt.xlabel('Normalized Execution Time (%)', fontsize=12)
    plt.ylabel('Benchmark', fontsize=12)
    
    # Improve x-axis labeling - show only a few labels for readability
    num_ticks = 10
    tick_positions = np.linspace(0, bins-1, num_ticks, dtype=int)
    tick_labels = [f"{int(i)}%" for i in np.linspace(0, 100, num_ticks)]
    plt.xticks(tick_positions, tick_labels)
    
    plt.tight_layout()
    plt.savefig(os.path.join(benchmark_root, "eviction_heatmap.png"), dpi=300)
    print(f"Saved eviction heatmap to {os.path.join(benchmark_root, 'eviction_heatmap.png')}")
    
    # Return the master dataframe for further analysis
    return master_df

def visualize_dead_block_prediction_potential(master_df):
    """
    Create visualizations to highlight potential for dead block prediction.
    
    Args:
        master_df (DataFrame): Combined dataframe with all benchmark data
    """
    # Look for dead block related columns
    dead_block_cols = [col for col in master_df.columns 
                       if any(term in col.lower() for term in ['dead', 'unused', 'stale', 'lifetime'])]
    
    if not dead_block_cols:
        print("No dead block related columns found!")
        return
    
    # For this example, let's assume we have columns that indicate:
    # 1. Block lifetime (time between insertion and last use)
    # 2. Eviction time (when block was evicted)
    # 3. Last access time (when block was last accessed)
    
    lifetime_col = next((col for col in dead_block_cols if 'lifetime' in col.lower()), None)
    last_access_col = next((col for col in master_df.columns if any(term in col.lower() for term in ['last_access', 'last_use'])), None)
    
    if lifetime_col and last_access_col:
        # Calculate wasted cache residency time (time between last access and eviction)
        master_df['WastedTime'] = master_df['Time'] - master_df[last_access_col]
        
        # Calculate potential benefit of perfect dead block prediction per benchmark
        wasted_stats = master_df.groupby('Benchmark').agg({
            'WastedTime': ['sum', 'mean', 'median'],
            'Time': ['min', 'max']
        })
        
        # Flatten the column hierarchy
        wasted_stats.columns = ['_'.join(col).strip() for col in wasted_stats.columns.values]
        
        # Calculate total execution time and percentage of time wasted
        wasted_stats['TotalTime'] = wasted_stats['Time_max'] - wasted_stats['Time_min']
        wasted_stats['WastedTimePercentage'] = (wasted_stats['WastedTime_sum'] / wasted_stats['TotalTime']) * 100
        
        # Plot the percentage of time wasted by benchmark
        plt.figure(figsize=(14, 8))
        ax = wasted_stats['WastedTimePercentage'].sort_values(ascending=False).plot(kind='bar', color='#2171b5')
        
        plt.title('Potential Cache Efficiency Improvement with Perfect Dead Block Prediction', fontsize=16)
        plt.xlabel('Benchmark', fontsize=12)
        plt.ylabel('Wasted Cache Residency Time (%)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on top of bars
        for i, v in enumerate(wasted_stats['WastedTimePercentage'].sort_values(ascending=False)):
            ax.text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(os.path.join(os.path.dirname(master_df['OriginalFile'].iloc[0]), "dead_block_potential.png"), dpi=300)
        print(f"Saved dead block prediction potential chart")
        
        # Create a scatter plot of block lifetime vs. wasted time
        plt.figure(figsize=(14, 8))
        
        # Use different colors for each benchmark
        benchmarks = master_df['Benchmark'].unique()
        colors = plt.cm.viridis(np.linspace(0, 1, len(benchmarks)))
        
        for i, benchmark in enumerate(benchmarks):
            benchmark_data = master_df[master_df['Benchmark'] == benchmark]
            plt.scatter(benchmark_data[lifetime_col], benchmark_data['WastedTime'], 
                       alpha=0.5, color=colors[i], label=benchmark)
        
        plt.title('Block Lifetime vs. Wasted Cache Residency Time', fontsize=16)
        plt.xlabel('Block Lifetime', fontsize=12)
        plt.ylabel('Wasted Residency Time', fontsize=12)
        plt.legend(title='Benchmark')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(os.path.dirname(master_df['OriginalFile'].iloc[0]), "lifetime_vs_waste.png"), dpi=300)
        print(f"Saved lifetime vs. wasted time scatter plot")
        
        return wasted_stats

def create_temporal_eviction_patterns(master_df):
    """
    Create a visualization of temporal eviction patterns across benchmarks.
    This helps identify when evictions are happening during program execution.
    
    Args:
        master_df (DataFrame): Combined dataframe with all benchmark data
    """
    # Identify the eviction column
    eviction_columns = [col for col in master_df.columns if 'evict' in col.lower()]
    
    if not eviction_columns:
        print("No eviction-related columns found!")
        return
        
    eviction_col = eviction_columns[0]
    
    # Create a rolling window analysis of eviction frequency
    plt.figure(figsize=(16, 10))
    
    # Create 10 normalized time segments
    segments = 10
    master_df['TimeSegment'] = pd.cut(master_df['NormalizedTime'], bins=segments, labels=False)
    
    # Calculate eviction frequency per segment per benchmark
    eviction_freq = master_df.groupby(['Benchmark', 'TimeSegment'])[eviction_col].mean()
    eviction_freq = eviction_freq.unstack(level=0)
    
    # Plot line graph
    ax = eviction_freq.plot(kind='line', marker='o', linewidth=2, markersize=8, figsize=(16, 10))
    
    plt.title('Temporal Evolution of Eviction Patterns Across Benchmarks', fontsize=16)
    plt.xlabel('Execution Timeline (Normalized)', fontsize=14)
    plt.ylabel('Eviction Frequency', fontsize=14)
    
    # Improve x-axis labeling
    tick_positions = range(segments)
    tick_labels = [f"{int(i*100/segments)}-{int((i+1)*100/segments)}%" for i in range(segments)]
    plt.xticks(tick_positions, tick_labels, rotation=45)
    
    plt.grid(True, alpha=0.3)
    plt.legend(title='Benchmark', fontsize=12, title_fontsize=14)
    
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(master_df['OriginalFile'].iloc[0]), "temporal_eviction_patterns.png"), dpi=300)
    print(f"Saved temporal eviction patterns chart")

def analyze_benchmarks(benchmark_root):
    """
    Analyze all benchmarks and create comprehensive visualizations.
    
    Args:
        benchmark_root (str): Root directory containing benchmark folders
    """
    print(f"Analyzing benchmarks in {benchmark_root}...")
    
    # Create the main heatmap and get combined data
    master_df = visualize_eviction_heatmap(benchmark_root)
    
    if master_df is not None:
        # Create dead block prediction potential visualization
        wasted_stats = visualize_dead_block_prediction_potential(master_df)
        
        # Create temporal eviction patterns visualization
        create_temporal_eviction_patterns(master_df)

if __name__ == "__main__":
    # Use 'normal' as the root directory containing benchmark folders
    benchmark_root = 'normal'
    print(f"Using root directory: {benchmark_root}")
    
    # Run the complete analysis
    analyze_benchmarks(benchmark_root)