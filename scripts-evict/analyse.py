# Prefetcher Performance Analysis
# This notebook analyzes GPU performance with different prefetcher configurations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
from pathlib import Path

# Set plot style
plt.style.use('ggplot')
sns.set_palette("Set2")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

# Function to read and process a CSV file
def read_and_process_csv(file_path):
    df = pd.read_csv(file_path)
    
    # Clean column names (remove leading/trailing spaces)
    df.columns = df.columns.str.strip()
    
    # Rename any unnamed columns if they exist
    if 'Unnamed: 0' in df.columns:
        df.rename(columns={'Unnamed: 0': 'index'}, inplace=True)
    
    return df

# Function to extract key metrics
def extract_metrics(df, file_name):
    # Extract kernel time
    kernel_time_data = df[df['what'] == 'kernel_time']
    total_kernel_time = kernel_time_data['value'].sum()
    avg_kernel_time = kernel_time_data['value'].mean()
    
    # Extract CU instruction count
    cu_inst_data = df[df['what'] == 'cu_inst_count']
    total_instructions = cu_inst_data['value'].sum()
    
    # Calculate throughput
    throughput = total_instructions / total_kernel_time if total_kernel_time > 0 else 0
    
    # Extract CPI
    cpi_data = df[df['what'] == 'cu_CPI']
    avg_cpi = cpi_data['value'].mean()
    
    # Extract L1V cache data
    l1v_data = df[df['where'].str.contains('L1VCache', na=False)]
    l1v_read_hit = l1v_data[l1v_data['what'] == 'read-hit']['value'].sum()
    l1v_read_miss = l1v_data[l1v_data['what'] == 'read-miss']['value'].sum()
    l1v_read_mshr_hit = l1v_data[l1v_data['what'] == 'read-mshr-hit']['value'].sum()
    l1v_total_reads = l1v_read_hit + l1v_read_miss + l1v_read_mshr_hit
    l1v_hit_rate = (l1v_read_hit / l1v_total_reads * 100) if l1v_total_reads > 0 else 0
    
    # Extract prefetcher metrics if available
    has_prefetcher = 'no_prefetcher' not in file_name
    prefetch_hits = 0
    prefetch_misses = 0
    prefetch_total = 0
    prefetch_accuracy = 0
    
    if has_prefetcher:
        prefetch_hits_data = df[df['what'] == 'prefetch-hits']
        prefetch_misses_data = df[df['what'] == 'prefetch-misses']
        prefetch_hits = prefetch_hits_data['value'].sum()
        prefetch_misses = prefetch_misses_data['value'].sum()
        prefetch_total = prefetch_hits + prefetch_misses
        prefetch_accuracy = (prefetch_hits / prefetch_total * 100) if prefetch_total > 0 else 0
    
    return {
        'kernel_time': avg_kernel_time,
        'total_kernel_time': total_kernel_time,
        'total_instructions': total_instructions,
        'throughput': throughput,
        'cpi': avg_cpi,
        'l1v_hit_rate': l1v_hit_rate,
        'l1v_read_hit': l1v_read_hit,
        'l1v_read_miss': l1v_read_miss,
        'has_prefetcher': has_prefetcher,
        'prefetch_hits': prefetch_hits,
        'prefetch_misses': prefetch_misses,
        'prefetch_total': prefetch_total,
        'prefetch_accuracy': prefetch_accuracy
    }

# Function to read and process all CSV files in a directory
def process_all_files(directory_path="."):
    """Process all CSV files in the specified directory, auto-detecting prefetcher configurations"""
    results = {}
    
    # Get all CSV files in the directory
    import glob
    file_paths = glob.glob(os.path.join(directory_path, "*.csv"))
    
    if not file_paths:
        print(f"No CSV files found in {directory_path}")
        return results
    
    # Identify the baseline file (without prefetcher)
    baseline_file = None
    for f in file_paths:
        file_name = os.path.basename(f)
        if file_name.lower() == 'metrics.csv' or 'latency' in file_name.lower() or 'no_prefetch' in file_name.lower():
            baseline_file = f
            break
    
    if baseline_file:
        print(f"Identified baseline file: {os.path.basename(baseline_file)}")
        file_paths.remove(baseline_file)
        
        # Process baseline file
        try:
            df = read_and_process_csv(baseline_file)
            metrics = extract_metrics(df, os.path.basename(baseline_file))
            results['no_prefetcher'] = metrics
            print(f"  Processed baseline without prefetcher")
        except Exception as e:
            print(f"  Error processing {baseline_file}: {e}")
    else:
        print("Notice: No baseline file (metrics.csv) identified. Running with limited comparative metrics.")
    
    # Process all other files (with prefetchers)
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        
        # Try to extract prefetcher size from filename
        config_name = None
        # Check if filename is just a number (like "2.csv", "16.csv")
        name_without_ext = os.path.splitext(file_name)[0]
        if name_without_ext.isdigit():
            config_name = f"prefetcher_{name_without_ext}"
        else:
            # Try to find a number in the filename
            import re
            numbers = re.findall(r'\d+', file_name)
            if numbers:
                config_name = f"prefetcher_{numbers[0]}"
            else:
                # If no number found, use the filename
                config_name = f"prefetcher_{name_without_ext}"
        
        print(f"Processing {config_name} ({file_path})...")
        try:
            df = read_and_process_csv(file_path)
            metrics = extract_metrics(df, file_name)
            results[config_name] = metrics
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
    
    return results

# Create a summary DataFrame for easy comparison
def create_summary_df(results):
    configs = []
    
    # Check if we have a baseline
    has_baseline = 'no_prefetcher' in results
    baseline_throughput = results['no_prefetcher']['throughput'] if has_baseline else 1.0
    
    for config_name, metrics in results.items():
        # Create a human-readable name
        if config_name == 'no_prefetcher':
            display_name = 'No Prefetcher'
        else:
            size = config_name.split('_')[1]
            display_name = f'Prefetcher Size {size}'
        
        # Create config entry
        config_entry = {
            'config': display_name,
            'kernel_time': metrics['kernel_time'],
            'total_kernel_time': metrics['total_kernel_time'],
            'throughput': metrics['throughput'],
            'cpi': metrics['cpi'],
            'l1v_hit_rate': metrics['l1v_hit_rate'],
            'has_prefetcher': metrics['has_prefetcher'],
            'prefetch_hits': metrics['prefetch_hits'],
            'prefetch_misses': metrics['prefetch_misses'],
            'prefetch_total': metrics['prefetch_total'],
            'prefetch_accuracy': metrics['prefetch_accuracy']
        }
        
        # Add normalized throughput only if baseline exists
        if has_baseline:
            config_entry['throughput_normalized'] = metrics['throughput'] / baseline_throughput
        
        configs.append(config_entry)
    
    return pd.DataFrame(configs)

# Function to visualize the performance metrics
def visualize_performance(summary_df):
    has_baseline = 'throughput_normalized' in summary_df.columns and not summary_df['throughput_normalized'].isna().all()
    
    # Set up plots - either 2x2 or just 2 plots based on baseline availability
    if has_baseline:
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    else:
        fig, axs = plt.subplots(1, 2, figsize=(15, 6))
        axs = np.array(axs).reshape(1, 2)  # Make consistent indexing
    
    # 1. Kernel Time Comparison
    ax1 = axs[0, 0]
    sns.barplot(x='config', y='kernel_time', data=summary_df, ax=ax1)
    ax1.set_title('Kernel Time Comparison')
    ax1.set_ylabel('Kernel Time (seconds)')
    ax1.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    for p in ax1.patches:
        ax1.annotate(f"{p.get_height():.8f}",
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=9, color='black',
                    xytext=(0, 5), textcoords='offset points')
    
    # 2. Throughput Comparison
    ax2 = axs[0, 1]
    sns.barplot(x='config', y='throughput', data=summary_df, ax=ax2)
    ax2.set_title('Throughput Comparison')
    ax2.set_ylabel('Throughput (instructions/time)')
    ax2.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    for p in ax2.patches:
        ax2.annotate(f"{p.get_height():.2e}",
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=9, color='black',
                    xytext=(0, 5), textcoords='offset points')
    
    if has_baseline:
        # 3. L1V Cache Hit Rate
        ax3 = axs[1, 0]
        sns.barplot(x='config', y='l1v_hit_rate', data=summary_df, ax=ax3)
        ax3.set_title('L1V Cache Hit Rate')
        ax3.set_ylabel('Hit Rate (%)')
        min_hit_rate = max(summary_df['l1v_hit_rate'].min() - 0.5, 93)
        max_hit_rate = min(summary_df['l1v_hit_rate'].max() + 0.5, 100)
        ax3.set_ylim(min_hit_rate, max_hit_rate)  # Adjust to focus on the differences
        for p in ax3.patches:
            ax3.annotate(f"{p.get_height():.2f}%",
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', fontsize=9, color='black',
                        xytext=(0, 5), textcoords='offset points')
        
        # 4. Speedup Factor (Normalized Throughput)
        ax4 = axs[1, 1]
        sns.barplot(x='config', y='throughput_normalized', data=summary_df, ax=ax4)
        ax4.set_title('Speedup Factor (vs. No Prefetcher)')
        ax4.set_ylabel('Speedup Factor')
        ax4.axhline(y=1, color='r', linestyle='--', alpha=0.5)
        for p in ax4.patches:
            if not np.isnan(p.get_height()):
                ax4.annotate(f"{p.get_height():.2f}x",
                            (p.get_x() + p.get_width() / 2., p.get_height()),
                            ha='center', va='center', fontsize=9, color='black',
                            xytext=(0, 5), textcoords='offset points')
    
    plt.tight_layout()
    plt.savefig('performance_comparison.png', dpi=300)
    plt.show()

# Function to visualize prefetcher-specific metrics
def visualize_prefetcher_metrics(summary_df):
    # Filter out the no-prefetcher configuration
    prefetcher_df = summary_df[summary_df['has_prefetcher']].copy()
    
    if len(prefetcher_df) == 0:
        print("No prefetcher data to visualize")
        return
    
    # Set up a 2x1 grid of plots
    fig, axs = plt.subplots(2, 1, figsize=(12, 10))
    
    # 1. Prefetch Counts
    ax1 = axs[0]
    prefetch_counts = prefetcher_df.melt(
        id_vars=['config'], 
        value_vars=['prefetch_hits', 'prefetch_misses'], 
        var_name='Type', 
        value_name='Count'
    )
    sns.barplot(x='config', y='Count', hue='Type', data=prefetch_counts, ax=ax1)
    ax1.set_title('Prefetcher Hit vs. Miss Counts')
    ax1.set_ylabel('Count')
    for container in ax1.containers:
        ax1.bar_label(container, fmt='%d')
    
    # 2. Prefetcher Accuracy and Hit Rate Correlation
    ax2 = axs[1]
    
    # Double y-axis plot for accuracy and L1V hit rate
    color1, color2 = sns.color_palette("Set2")[0:2]
    
    # First axis: Prefetcher Accuracy
    sns.barplot(x='config', y='prefetch_accuracy', data=prefetcher_df, ax=ax2, color=color1)
    ax2.set_title('Prefetcher Accuracy vs. L1V Hit Rate')
    ax2.set_ylabel('Prefetcher Accuracy (%)', color=color1)
    ax2.tick_params(axis='y', labelcolor=color1)
    
    # Second axis: L1V Hit Rate
    ax2_twin = ax2.twinx()
    sns.lineplot(x=range(len(prefetcher_df)), y=prefetcher_df['l1v_hit_rate'], 
                marker='o', color=color2, ax=ax2_twin)
    ax2_twin.set_ylabel('L1V Hit Rate (%)', color=color2)
    ax2_twin.tick_params(axis='y', labelcolor=color2)
    ax2_twin.set_ylim(93.5, 95.5)  # Adjust to focus on the differences
    
    # Add annotations for the bars
    for i, p in enumerate(ax2.patches):
        ax2.annotate(f"{p.get_height():.2f}%",
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=9, color='black',
                    xytext=(0, 5), textcoords='offset points')
    
    # Add annotations for the line points
    for i, row in enumerate(prefetcher_df.itertuples()):
        ax2_twin.annotate(f"{row.l1v_hit_rate:.2f}%",
                        (i, row.l1v_hit_rate),
                        ha='center', va='bottom', fontsize=9, color=color2,
                        xytext=(0, 5), textcoords='offset points')
    
    plt.tight_layout()
    plt.savefig('prefetcher_metrics.png', dpi=300)
    plt.show()

# Function to create a correlation plot
def plot_correlation(summary_df):
    if len(summary_df) < 2:
        print("Correlation plot requires at least two data points")
        return
    
    plt.figure(figsize=(10, 8))
    
    # Create correlation plot between L1V hit rate and throughput
    plt.scatter(summary_df['l1v_hit_rate'], summary_df['throughput'], 
                s=100, c=summary_df.index, cmap='viridis')
    
    # Add annotations for each point
    for i, row in summary_df.iterrows():
        plt.annotate(row['config'], 
                    (row['l1v_hit_rate'], row['throughput']),
                    xytext=(5, 5), textcoords='offset points')
    
    # Add trendline
    z = np.polyfit(summary_df['l1v_hit_rate'], summary_df['throughput'], 1)
    p = np.poly1d(z)
    plt.plot(summary_df['l1v_hit_rate'], p(summary_df['l1v_hit_rate']), 
             "r--", alpha=0.7)
    
    plt.title('Correlation: L1V Cache Hit Rate vs. Throughput')
    plt.xlabel('L1V Cache Hit Rate (%)')
    plt.ylabel('Throughput (instructions/time)')
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('correlation_plot.png', dpi=300)
    plt.show()

# Main execution section
def main():
    # Process all files in the specified directory and create summary
    results = process_all_files("./prefetcher/conv2d")  # Change this path to your data directory
    
    if not results:
        print("No valid data found. Please check your input directory.")
        return
    
    has_baseline = 'no_prefetcher' in results
    if not has_baseline:
        print("Notice: No baseline (no_prefetcher) data found. Running with limited comparative metrics.")
        
    summary_df = create_summary_df(results)
    
    # Display summary
    print("\nPerformance Summary:")
    print(summary_df.to_string())
    
    # Save to CSV for reference
    summary_df.to_csv('prefetcher_performance_summary.csv', index=False)
    
    # Create visualizations
    visualize_performance(summary_df)
    
    if len(summary_df[summary_df['has_prefetcher']]) > 0:
        visualize_prefetcher_metrics(summary_df)
    else:
        print("No prefetcher configurations found, skipping prefetcher metrics visualization.")
    
    if has_baseline and len(summary_df) > 1:
        plot_correlation(summary_df)
    else:
        print("Correlation plot requires baseline and at least one prefetcher configuration, skipping.")
    
    # Print key insights
    print("\nKey Insights:")
    print("1. L1V Cache Hit Rate:")
    for i, row in summary_df.iterrows():
        print(f"   - {row['config']}: {row['l1v_hit_rate']:.2f}%")
    
    if has_baseline:
        print("\n2. Kernel Time Performance:")
        baseline_time = summary_df[summary_df['config'] == 'No Prefetcher']['kernel_time'].values[0]
        for i, row in summary_df.iterrows():
            improvement = (baseline_time - row['kernel_time']) / baseline_time * 100
            print(f"   - {row['config']}: {row['kernel_time']:.8f} seconds ({improvement:.1f}% improvement)")
    
    prefetcher_rows = summary_df[summary_df['has_prefetcher']]
    if len(prefetcher_rows) > 0:
        print("\n3. Prefetcher Efficiency:")
        for i, row in prefetcher_rows.iterrows():
            print(f"   - {row['config']}: {row['prefetch_hits']:.0f} hits / {row['prefetch_total']:.0f} total ({row['prefetch_accuracy']:.2f}% accuracy)")

# Run the analysis if executed directly
if __name__ == "__main__":
    main()