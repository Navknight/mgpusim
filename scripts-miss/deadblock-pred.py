#!/usr/bin/env python3
"""
This script analyzes L1 and L2 cache dead block prediction potential across multiple benchmarks.
It generates separate graphs for single and double access blocks, optimized for side-by-side display
in LaTeX documents.
"""

import os
import argparse
import re
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

# Set up the plotting style for publication quality
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'serif']
rcParams['font.size'] = 10
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 11
rcParams['xtick.labelsize'] = 9
rcParams['ytick.labelsize'] = 9
rcParams['legend.fontsize'] = 9
rcParams['figure.titlesize'] = 12

def parse_log_file(log_file_path):
    """
    Parse the log.txt file and extract L1 and L2 cache access histogram data.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Dictionary with L1 and L2 cache data
    """
    try:
        with open(log_file_path, 'r') as f:
            content = f.read()
        
        # Split into sections
        sections = content.split('\n\n')
        
        # Find L1 and L2 cache sections
        l1_section = next((s for s in sections if s.startswith("L1 Cache")), None)
        l2_section = next((s for s in sections if s.startswith("L2 Cache")), None)
        
        result = {}
        
        # Parse L2 cache data if available
        if l2_section:
            result['L2'] = parse_cache_section(l2_section)
        else:
            print(f"No L2 cache data found in {log_file_path}")
            result['L2'] = []
        
        # Parse L1 cache data if available
        if l1_section:
            result['L1'] = parse_cache_section(l1_section)
        else:
            print(f"No L1 cache data found in {log_file_path}")
            result['L1'] = []
        
        return result
    
    except Exception as e:
        print(f"Error reading log file {log_file_path}: {str(e)}")
        return {'L1': [], 'L2': []}

def parse_cache_section(section):
    """
    Parse a cache section from the log file.
    
    Args:
        section: Text section from the log file
        
    Returns:
        List of dictionaries with histogram and totalEvictions fields
    """
    lines = section.split('\n')[1:]  # Skip the header line
    data = []
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        
        try:
            entry = {}
            
            # Extract the histogram part
            histogram_match = re.search(r'AccessHistogram:map\[(.*?)\]', line)
            if histogram_match:
                histogram_str = histogram_match.group(1)
                entry['histogram'] = parse_histogram(histogram_str)
            else:
                continue
            
            # Extract total evictions
            evictions_match = re.search(r'TotalEvictions:(\d+)', line)
            if evictions_match:
                entry['totalEvictions'] = int(evictions_match.group(1))
            else:
                continue
            
            data.append(entry)
        except Exception as e:
            print(f"Error parsing line {i+1}: {str(e)}")
    
    return data

def parse_histogram(histogram_str):
    """
    Parse the histogram string into a dictionary.
    
    Args:
        histogram_str: String containing key-value pairs
        
    Returns:
        Dictionary of access counts
    """
    result = {}
    
    # Extract all key-value pairs using regex
    pattern = r'(\w+(?:-\w+)?|\>\w+|\d+\+):(\d+)'
    matches = re.findall(pattern, histogram_str)
    
    for key, value in matches:
        result[key] = int(value)
    
    return result

def calculate_prediction_potential(data):
    """
    Calculate the cache dead block prediction potential.
    
    Args:
        data: List of dictionaries with histogram and totalEvictions fields
        
    Returns:
        Dictionary with metrics about dead block prediction potential
    """
    if not data:
        return {
            'single_access_blocks_percent': 0,
            'two_access_blocks_percent': 0,
            'prediction_potential': 0,
            'total_evictions': 0
        }
    
    # Calculate totals across all samples
    # Note: '0' in the histogram actually means 1 demand access (initial load)
    # '1' means initial load + 1 extra access = 2 total accesses
    single_access_blocks = sum(entry['histogram'].get('0', 0) for entry in data)
    two_access_blocks = sum(entry['histogram'].get('1', 0) for entry in data)
    total_evictions = sum(entry['totalEvictions'] for entry in data)
    
    # Calculate percentages
    if total_evictions > 0:
        single_access_blocks_percent = (single_access_blocks / total_evictions) * 100
        two_access_blocks_percent = (two_access_blocks / total_evictions) * 100
        prediction_potential = single_access_blocks_percent + two_access_blocks_percent
    else:
        single_access_blocks_percent = 0
        two_access_blocks_percent = 0
        prediction_potential = 0
    
    return {
        'single_access_blocks_percent': single_access_blocks_percent,
        'two_access_blocks_percent': two_access_blocks_percent,
        'prediction_potential': prediction_potential,
        'total_evictions': total_evictions
    }

def create_single_access_visualization(benchmark_data, cache_type, output_file, benchmark_order=None):
    """
    Create a bar chart showing single access blocks across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        cache_type: 'L1' or 'L2'
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data[cache_type] for name, data in benchmark_data.items() 
                       if data[cache_type]['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print(f"No valid benchmark data for {cache_type} single access visualization")
        return
    
    # If benchmark_order is provided, maintain that order
    # Otherwise use alphabetical order
    if benchmark_order:
        # Filter benchmark_order to only include valid benchmarks
        ordered_benchmarks = [(name, valid_benchmarks[name]) for name in benchmark_order if name in valid_benchmarks]
    else:
        # Use alphabetical order
        ordered_benchmarks = sorted(valid_benchmarks.items())
    
    benchmark_names = [name for name, _ in ordered_benchmarks]
    single_access = [data['single_access_blocks_percent'] for _, data in ordered_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(7, 4))
    
    # Plot bars with patterns
    bar_width = 0.7
    x = np.arange(len(benchmark_names))
    
    # Use hatches for black and white distinction
    bars = plt.bar(x, single_access, bar_width, label='Single Access Blocks', 
                   color='white', edgecolor='black', hatch='////')
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if single_access[i] > 2:  # Only label bars with significant values
            plt.text(i, single_access[i] + 0.5, f'{single_access[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure the plot for readability
    plt.title(f'{cache_type} Cache Single Access Blocks', fontsize=11)
    plt.xlabel('Benchmark', fontsize=10)
    plt.ylabel('Percentage of Evictions (%)', fontsize=10)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=8)
    plt.ylim(0, min(100, max(single_access) * 1.15))  # Set y limit to data range + 15%
    
    # Add a horizontal line showing the average
    avg = np.mean(single_access)
    plt.axhline(y=avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
    plt.text(len(benchmark_names) - 1, avg + 0.5, f'Avg: {avg:.0f}%', 
            ha='right', va='bottom', fontsize=8, color='black')
    
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved {cache_type} single access visualization to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved {cache_type} single access visualization as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    json_data = {
        'benchmarks': {name: float(data) for name, data in zip(benchmark_names, single_access)},
        'average': float(avg)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved {cache_type} single access data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_two_access_visualization(benchmark_data, cache_type, output_file, benchmark_order=None):
    """
    Create a bar chart showing two access blocks across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        cache_type: 'L1' or 'L2'
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data[cache_type] for name, data in benchmark_data.items() 
                       if data[cache_type]['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print(f"No valid benchmark data for {cache_type} two access visualization")
        return
    
    # If benchmark_order is provided, maintain that order
    # Otherwise use alphabetical order
    if benchmark_order:
        # Filter benchmark_order to only include valid benchmarks
        ordered_benchmarks = [(name, valid_benchmarks[name]) for name in benchmark_order if name in valid_benchmarks]
    else:
        # Use alphabetical order  
        ordered_benchmarks = sorted(valid_benchmarks.items())
    
    benchmark_names = [name for name, _ in ordered_benchmarks]
    two_access = [data['two_access_blocks_percent'] for _, data in ordered_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(7, 4))
    
    # Plot bars with patterns
    bar_width = 0.7
    x = np.arange(len(benchmark_names))
    
    # Use hatches for black and white distinction
    bars = plt.bar(x, two_access, bar_width, label='Two Access Blocks', 
                   color='white', edgecolor='black', hatch='....')
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if two_access[i] > 2:  # Only label bars with significant values
            plt.text(i, two_access[i] + 0.5, f'{two_access[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure the plot for readability
    plt.title(f'{cache_type} Cache Two Access Blocks', fontsize=11)
    plt.xlabel('Benchmark', fontsize=10)
    plt.ylabel('Percentage of Evictions (%)', fontsize=10)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=8)
    plt.ylim(0, min(100, max(two_access) * 1.15))  # Set y limit to data range + 15%
    
    # Add a horizontal line showing the average
    avg = np.mean(two_access)
    plt.axhline(y=avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
    plt.text(len(benchmark_names) - 1, avg + 0.5, f'Avg: {avg:.0f}%', 
            ha='right', va='bottom', fontsize=8, color='black')
    
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved {cache_type} two access visualization to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved {cache_type} two access visualization as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    json_data = {
        'benchmarks': {name: float(data) for name, data in zip(benchmark_names, two_access)},
        'average': float(avg)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved {cache_type} two access data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_l1_vs_l2_visualization(benchmark_data, access_type, output_file, benchmark_order=None):
    """
    Create a comparison of L1 vs L2 for a specific access type.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        access_type: 'single_access_blocks_percent' or 'two_access_blocks_percent'
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Determine display name for the access type
    display_name = "Single Access Blocks" if access_type == 'single_access_blocks_percent' else "Two Access Blocks"
    
    # Filter benchmarks that have both L1 and L2 data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if data['L1']['total_evictions'] > 0 and data['L2']['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print(f"No benchmarks with both L1 and L2 data for {display_name} comparison")
        return
    
    # If benchmark_order is provided, maintain that order
    # Otherwise use alphabetical order
    if benchmark_order:
        # Filter benchmark_order to only include valid benchmarks
        ordered_benchmarks = [(name, valid_benchmarks[name]) for name in benchmark_order if name in valid_benchmarks]
    else:
        # Use alphabetical order
        ordered_benchmarks = sorted(valid_benchmarks.items())
    
    benchmark_names = [name for name, _ in ordered_benchmarks]
    l1_values = [data['L1'][access_type] for _, data in ordered_benchmarks]
    l2_values = [data['L2'][access_type] for _, data in ordered_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(7, 4))
    
    # Plot grouped bars with patterns
    bar_width = 0.35
    x = np.arange(len(benchmark_names))
    
    # Use different hatches for L1 and L2
    bars1 = plt.bar(x - bar_width/2, l2_values, bar_width, label='L2 Cache', 
                   color='white', edgecolor='black', hatch='////')
    bars2 = plt.bar(x + bar_width/2, l1_values, bar_width, label='L1 Cache', 
                   color='white', edgecolor='black', hatch='....')
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if l2_values[i] > 2:  # Only label bars with significant values
            plt.text(i - bar_width/2, l2_values[i] + 0.5, f'{l2_values[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=7, fontweight='bold')
        if l1_values[i] > 2:
            plt.text(i + bar_width/2, l1_values[i] + 0.5, f'{l1_values[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=7, fontweight='bold')
    
    # Configure the plot for readability
    plt.title(f'L1 vs L2 Cache {display_name}', fontsize=11)
    plt.xlabel('Benchmark', fontsize=10)
    plt.ylabel('Percentage of Evictions (%)', fontsize=10)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=8)
    
    # Set y-axis limit based on data range
    max_value = max(max(l1_values), max(l2_values))
    plt.ylim(0, min(100, max_value * 1.15))  # Set y limit to data range + 15%
    
    plt.legend(loc='upper right', fontsize=8, frameon=True, framealpha=0.9)
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add horizontal lines showing the averages
    l1_avg = np.mean(l1_values)
    l2_avg = np.mean(l2_values)
    
    plt.axhline(y=l1_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
    plt.axhline(y=l2_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
    
    plt.text(len(benchmark_names) - 1, l1_avg + 0.5, f'L1 Avg: {l1_avg:.0f}%', 
            ha='right', va='bottom', fontsize=7, color='black')
    plt.text(len(benchmark_names) - 1, l2_avg + 0.5, f'L2 Avg: {l2_avg:.0f}%', 
            ha='right', va='bottom', fontsize=7, color='black')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved L1 vs L2 {display_name} comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved L1 vs L2 {display_name} comparison as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    json_data = {
        'benchmarks': {name: {'L1': float(l1), 'L2': float(l2)} 
                      for name, l1, l2 in zip(benchmark_names, l1_values, l2_values)},
        'L1_average': float(l1_avg),
        'L2_average': float(l2_avg)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved L1 vs L2 {display_name} comparison data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_side_by_side_l2_visualization(benchmark_data, output_file, benchmark_order=None):
    """
    Create a side-by-side visualization of L2 cache single and double access blocks.
    Optimized for readability in LaTeX when placed in a figure environment.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no L2 data
    valid_benchmarks = {name: data['L2'] for name, data in benchmark_data.items() 
                       if data['L2']['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print("No valid benchmark data for L2 side-by-side visualization")
        return
    
    # If benchmark_order is provided, maintain that order
    # Otherwise use alphabetical order
    if benchmark_order:
        # Filter benchmark_order to only include valid benchmarks
        ordered_benchmarks = [(name, valid_benchmarks[name]) for name in benchmark_order if name in valid_benchmarks]
    else:
        # Use alphabetical order
        ordered_benchmarks = sorted(valid_benchmarks.items())
    
    benchmark_names = [name for name, _ in ordered_benchmarks]
    single_access = [data['single_access_blocks_percent'] for _, data in ordered_benchmarks]
    two_access = [data['two_access_blocks_percent'] for _, data in ordered_benchmarks]
    
    # Create figure with subplots - optimized for LaTeX
    # These dimensions should work well in a LaTeX document
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    
    # Plot bar charts with clear patterns
    bar_width = 0.8  # Make bars slightly wider for better readability
    x = np.arange(len(benchmark_names))
    
    # Left subplot - single access
    bars1 = ax1.bar(x, single_access, bar_width, color='white', edgecolor='black', hatch='////', linewidth=1.2)
    
    # Add percentage labels on top of significant bars
    for i in range(len(benchmark_names)):
        if single_access[i] > 3:  # Only label significant values
            ax1.text(i, single_access[i] + 0.8, f'{single_access[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Right subplot - two access
    bars2 = ax2.bar(x, two_access, bar_width, color='white', edgecolor='black', hatch='....', linewidth=1.2)
    
    # Add percentage labels on top of significant bars
    for i in range(len(benchmark_names)):
        if two_access[i] > 3:  # Only label significant values
            ax2.text(i, two_access[i] + 0.8, f'{two_access[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Configure left subplot
    ax1.set_title('L2 Cache Single Access Blocks', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Benchmark', fontsize=11)
    ax1.set_ylabel('Percentage of Evictions (%)', fontsize=11)
    ax1.set_xticks(x)
    
    # Make benchmark names more readable
    # Rotate less and use smaller font to fit better
    ax1.set_xticklabels(benchmark_names, rotation=40, ha='right', fontsize=8.5)
    
    # Add a horizontal line showing the average for single access
    avg1 = np.mean(single_access)
    ax1.axhline(y=avg1, color='black', linestyle='--', linewidth=1.2, alpha=0.7)
    ax1.text(len(benchmark_names) - 1, avg1 + 0.8, f'Avg: {avg1:.0f}%', 
            ha='right', va='bottom', fontsize=9, color='black', fontweight='bold')
    
    # Configure right subplot
    ax2.set_title('L2 Cache Two Access Blocks', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Benchmark', fontsize=11)
    # No y-label for right subplot to avoid redundancy
    ax2.set_xticks(x)
    
    # Make benchmark names more readable, matching left subplot
    ax2.set_xticklabels(benchmark_names, rotation=40, ha='right', fontsize=8.5)
    
    # Add a horizontal line showing the average for two access
    avg2 = np.mean(two_access)
    ax2.axhline(y=avg2, color='black', linestyle='--', linewidth=1.2, alpha=0.7)
    ax2.text(len(benchmark_names) - 1, avg2 + 0.8, f'Avg: {avg2:.0f}%', 
            ha='right', va='bottom', fontsize=9, color='black', fontweight='bold')
    
    # Set consistent y-axis limit based on data
    y_max = max(max(single_access), max(two_access))
    y_limit = min(100, y_max * 1.15)  # Set y limit to data range + 15%
    ax1.set_ylim(0, y_limit)
    
    # Add grid lines for readability but keep them light
    ax1.grid(axis='y', alpha=0.3, linestyle=':')
    ax2.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add overall title
    fig.suptitle('L2 Cache Access Patterns', fontsize=14, y=0.98, fontweight='bold')
    
    # Adjust layout to prevent overlapping and ensure tight spacing
    plt.tight_layout()
    
    # Additional adjustment for the overall title
    fig.subplots_adjust(top=0.88, wspace=0.1)  # Reduce space between subplots
    
    # Save as high-resolution PNG
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    print(f"Saved L2 side-by-side visualization to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved L2 side-by-side visualization as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    json_data = {
        'benchmarks': {name: {
            'single_access_blocks_percent': float(s),
            'two_access_blocks_percent': float(t)
        } for name, s, t in zip(benchmark_names, single_access, two_access)},
        'single_access_average': float(avg1),
        'two_access_average': float(avg2)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved L2 side-by-side data to {json_path}")
    
    # Close the figure to free memory
    plt.close('all')

def main():
    parser = argparse.ArgumentParser(description='Generate separate graphs for single and double access blocks in L1 and L2 caches')
    parser.add_argument('--benchmark_dir', type=str, required=True, help='Root directory containing benchmark folders')
    parser.add_argument('--output_dir', type=str, default='cache_access_results', help='Output directory for visualizations')
    parser.add_argument('--sort', choices=['alpha', 'none'], default='none', 
                      help='Sorting order for benchmarks (alpha=alphabetical, none=preserve directory order)')
    parser.add_argument('--side_by_side', action='store_true', default=True,
                      help='Generate side-by-side L2 cache visualizations optimized for LaTeX')
    
    args = parser.parse_args()
    
    benchmark_dir = args.benchmark_dir
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create dictionary to store results for each benchmark
    benchmark_data = {}
    
    # Get all benchmark directories while preserving order
    benchmarks = []
    for benchmark in os.listdir(benchmark_dir):
        benchmark_path = os.path.join(benchmark_dir, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
            
        log_file_path = os.path.join(benchmark_path, 'log.txt')
        if not os.path.exists(log_file_path):
            print(f"No log.txt found for benchmark {benchmark}")
            continue
            
        benchmarks.append(benchmark)
    
    # Sort benchmarks alphabetically if requested
    if args.sort == 'alpha':
        benchmarks.sort()
    
    # Store benchmark order for consistent graphs
    benchmark_order = benchmarks.copy()
    
    # Process each benchmark in the determined order
    for benchmark in benchmarks:
        benchmark_path = os.path.join(benchmark_dir, benchmark)
        log_file_path = os.path.join(benchmark_path, 'log.txt')
        
        print(f"Processing benchmark: {benchmark}")
        
        # Parse the log file to get L1 and L2 cache data
        cache_data = parse_log_file(log_file_path)
        
        # Calculate metrics for both cache levels
        l1_metrics = calculate_prediction_potential(cache_data['L1'])
        l2_metrics = calculate_prediction_potential(cache_data['L2'])
        
        # Store the results
        benchmark_data[benchmark] = {
            'L1': l1_metrics,
            'L2': l2_metrics
        }
    
    # Generate side-by-side L2 visualization (default to True for LaTeX optimization)
    if args.side_by_side:
        create_side_by_side_l2_visualization(benchmark_data, 
                                          os.path.join(output_dir, 'l2_side_by_side.png'),
                                          benchmark_order)
    
    # Create the separate visualizations with consistent benchmark order
    # L1 Cache single access blocks
    create_single_access_visualization(benchmark_data, 'L1', 
                                     os.path.join(output_dir, 'l1_single_access.png'), 
                                     benchmark_order)
    
    # L1 Cache two access blocks
    create_two_access_visualization(benchmark_data, 'L1', 
                                   os.path.join(output_dir, 'l1_two_access.png'), 
                                   benchmark_order)
    
    # L2 Cache single access blocks
    create_single_access_visualization(benchmark_data, 'L2', 
                                     os.path.join(output_dir, 'l2_single_access.png'), 
                                     benchmark_order)
    
    # L2 Cache two access blocks
    create_two_access_visualization(benchmark_data, 'L2', 
                                   os.path.join(output_dir, 'l2_two_access.png'), 
                                   benchmark_order)
    
    # Comparison of L1 vs L2 for single access blocks
    create_l1_vs_l2_visualization(benchmark_data, 'single_access_blocks_percent', 
                                os.path.join(output_dir, 'l1_vs_l2_single_access.png'),
                                benchmark_order)
    
    # Comparison of L1 vs L2 for two access blocks
    create_l1_vs_l2_visualization(benchmark_data, 'two_access_blocks_percent', 
                                os.path.join(output_dir, 'l1_vs_l2_two_access.png'),
                                benchmark_order)

if __name__ == "__main__":
    main()