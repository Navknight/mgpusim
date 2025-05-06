#!/usr/bin/env python3
"""
This script analyzes L1 and L2 cache dead block prediction potential across multiple benchmarks.
It generates publication-quality, black and white friendly graphs for reports.
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

def create_comparison_visualization(benchmark_data, cache_type, output_file):
    """
    Create a bar chart comparing dead block prediction potential across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        cache_type: 'L1' or 'L2'
        output_file: Path to save the visualization
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data[cache_type] for name, data in benchmark_data.items() 
                       if data[cache_type]['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print(f"No valid benchmark data for {cache_type} visualization")
        return
    
    # Sort benchmarks by prediction potential
    sorted_benchmarks = sorted(valid_benchmarks.items(), 
                              key=lambda x: x[1]['prediction_potential'], 
                              reverse=True)
    
    benchmark_names = [name for name, _ in sorted_benchmarks]
    single_access = [data['single_access_blocks_percent'] for _, data in sorted_benchmarks]
    two_access = [data['two_access_blocks_percent'] for _, data in sorted_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(7, 4))  # Smaller size for reports
    
    # Plot stacked bars with patterns instead of colors
    bar_width = 0.7
    x = np.arange(len(benchmark_names))
    
    # Use hatches for black and white distinction
    bars1 = plt.bar(x, single_access, bar_width, label='Single Access Blocks', 
                   color='white', edgecolor='black', hatch='////')
    bars2 = plt.bar(x, two_access, bar_width, bottom=single_access, 
                   label='Two Access Blocks', color='white', edgecolor='black', hatch='....')
    
    # Add total percentage labels on top of bars (smaller font for compactness)
    for i in range(len(benchmark_names)):
        total = single_access[i] + two_access[i]
        if total > 5:  # Only add labels to bars that are big enough to be visible
            plt.text(i, total + 0.5, f'{total:.0f}%', ha='center', va='bottom', 
                    fontsize=8, fontweight='bold')
    
    # Configure the plot for readability at small sizes
    plt.title(f'{cache_type} Cache Dead Block Prediction Potential', fontsize=11)
    plt.xlabel('Benchmark', fontsize=10)
    plt.ylabel('Percentage of Evictions (%)', fontsize=10)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=8)
    plt.ylim(0, min(100, max([s+t for s,t in zip(single_access, two_access)]) * 1.15))  # Set y limit to data range + 15%
    
    # Add a tight and clear legend
    plt.legend(loc='upper right', fontsize=8, frameon=True, framealpha=0.9)
    
    # Add a horizontal line showing the average prediction potential
    avg_potential = np.mean([data['prediction_potential'] for data in valid_benchmarks.values()])
    plt.axhline(y=avg_potential, color='black', linestyle='--', linewidth=1, alpha=0.7)
    plt.text(len(benchmark_names) - 1, avg_potential + 0.5, f'Avg: {avg_potential:.0f}%', 
            ha='right', va='bottom', fontsize=8, color='black')
    
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved {cache_type} benchmark comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved {cache_type} benchmark comparison as PDF: {pdf_path}")
    
    # Also save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    
    # Format the data for JSON serialization
    json_data = {
        'benchmarks': {name: {
            'single_access_blocks_percent': float(data['single_access_blocks_percent']),
            'two_access_blocks_percent': float(data['two_access_blocks_percent']),
            'prediction_potential': float(data['prediction_potential']),
            'total_evictions': int(data['total_evictions'])
        } for name, data in sorted_benchmarks},
        'average_prediction_potential': float(avg_potential)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved {cache_type} benchmark data to {json_path}")

def create_dual_comparison_visualization(benchmark_data, output_file):
    """
    Create a dual bar chart comparing L1 and L2 prediction potential for each benchmark.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to prediction potential metrics
        output_file: Path to save the visualization
    """
    # Filter benchmarks that have both L1 and L2 data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if data['L1']['total_evictions'] > 0 and data['L2']['total_evictions'] > 0}
    
    if not valid_benchmarks:
        print("No benchmarks with both L1 and L2 data for comparison")
        return
    
    # Sort benchmarks by L2 prediction potential (primary metric)
    sorted_benchmarks = sorted(valid_benchmarks.items(), 
                              key=lambda x: x[1]['L2']['prediction_potential'], 
                              reverse=True)
    
    benchmark_names = [name for name, _ in sorted_benchmarks]
    l1_potential = [data['L1']['prediction_potential'] for _, data in sorted_benchmarks]
    l2_potential = [data['L2']['prediction_potential'] for _, data in sorted_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(7, 4))  # Smaller size for reports
    
    # Plot grouped bars with patterns instead of colors
    bar_width = 0.35
    x = np.arange(len(benchmark_names))
    
    # Use different hatches for L1 and L2
    bars1 = plt.bar(x - bar_width/2, l2_potential, bar_width, label='L2 Cache', 
                   color='white', edgecolor='black', hatch='////')
    bars2 = plt.bar(x + bar_width/2, l1_potential, bar_width, label='L1 Cache', 
                   color='white', edgecolor='black', hatch='....')
    
    # Add percentage labels on top of bars (only for significant values)
    for i in range(len(benchmark_names)):
        if l2_potential[i] > 5:  # Only label bars with significant values
            plt.text(i - bar_width/2, l2_potential[i] + 0.5, f'{l2_potential[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=7, fontweight='bold')
        if l1_potential[i] > 5:
            plt.text(i + bar_width/2, l1_potential[i] + 0.5, f'{l1_potential[i]:.0f}%', 
                    ha='center', va='bottom', fontsize=7, fontweight='bold')
    
    # Configure the plot for readability at small sizes
    plt.title('L1 vs L2 Cache Dead Block Prediction Potential', fontsize=11)
    plt.xlabel('Benchmark', fontsize=10)
    plt.ylabel('Prediction Potential (%)', fontsize=10)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=8)
    
    # Set y-axis limit based on data range
    max_value = max(max(l1_potential), max(l2_potential))
    plt.ylim(0, min(100, max_value * 1.15))  # Set y limit to data range + 15%
    
    plt.legend(loc='upper right', fontsize=8, frameon=True, framealpha=0.9)
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add horizontal lines showing the average prediction potentials
    l1_avg = np.mean(l1_potential)
    l2_avg = np.mean(l2_potential)
    
    plt.axhline(y=l1_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
    plt.axhline(y=l2_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
    
    plt.text(len(benchmark_names) - 1, l1_avg + 0.5, f'L1 Avg: {l1_avg:.0f}%', 
            ha='right', va='bottom', fontsize=7, color='black')
    plt.text(len(benchmark_names) - 1, l2_avg + 0.5, f'L2 Avg: {l2_avg:.0f}%', 
            ha='right', va='bottom', fontsize=7, color='black')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved L1 vs L2 comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved L1 vs L2 comparison as PDF: {pdf_path}")
    
    # Also save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    
    # Format the data for JSON serialization
    json_data = {
        'benchmarks': {name: {
            'L1': {
                'single_access_blocks_percent': float(data['L1']['single_access_blocks_percent']),
                'two_access_blocks_percent': float(data['L1']['two_access_blocks_percent']),
                'prediction_potential': float(data['L1']['prediction_potential']),
                'total_evictions': int(data['L1']['total_evictions'])
            },
            'L2': {
                'single_access_blocks_percent': float(data['L2']['single_access_blocks_percent']),
                'two_access_blocks_percent': float(data['L2']['two_access_blocks_percent']),
                'prediction_potential': float(data['L2']['prediction_potential']),
                'total_evictions': int(data['L2']['total_evictions'])
            }
        } for name, data in sorted_benchmarks},
        'L1_average_prediction_potential': float(l1_avg),
        'L2_average_prediction_potential': float(l2_avg)
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved comparison data to {json_path}")

def main():
    parser = argparse.ArgumentParser(description='Compare L1 and L2 cache dead block prediction potential across benchmarks')
    parser.add_argument('--benchmark_dir', type=str, required=True, help='Root directory containing benchmark folders')
    parser.add_argument('--output_dir', type=str, default='prediction_results', help='Output directory for visualizations')
    
    args = parser.parse_args()
    
    benchmark_dir = args.benchmark_dir
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create dictionary to store results for each benchmark
    benchmark_data = {}
    
    # Process each benchmark directory
    for benchmark in os.listdir(benchmark_dir):
        benchmark_path = os.path.join(benchmark_dir, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
        
        log_file_path = os.path.join(benchmark_path, 'log.txt')
        if not os.path.exists(log_file_path):
            print(f"No log.txt found for benchmark {benchmark}")
            continue
        
        print(f"Processing benchmark: {benchmark}")
        
        # Parse the log file to get L1 and L2 cache data
        cache_data = parse_log_file(log_file_path)
        
        # Calculate prediction potential for both cache levels
        l1_metrics = calculate_prediction_potential(cache_data['L1'])
        l2_metrics = calculate_prediction_potential(cache_data['L2'])
        
        # Store the results
        benchmark_data[benchmark] = {
            'L1': l1_metrics,
            'L2': l2_metrics
        }
        
        # Report the results with correct terminology
        print(f"  L1 Cache:")
        print(f"    - Single-access blocks: {l1_metrics['single_access_blocks_percent']:.2f}%")
        print(f"    - Two-access blocks: {l1_metrics['two_access_blocks_percent']:.2f}%")
        print(f"    - Prediction potential: {l1_metrics['prediction_potential']:.2f}%")
        print(f"    - Total evictions: {l1_metrics['total_evictions']}")
        
        print(f"  L2 Cache:")
        print(f"    - Single-access blocks: {l2_metrics['single_access_blocks_percent']:.2f}%")
        print(f"    - Two-access blocks: {l2_metrics['two_access_blocks_percent']:.2f}%")
        print(f"    - Prediction potential: {l2_metrics['prediction_potential']:.2f}%")
        print(f"    - Total evictions: {l2_metrics['total_evictions']}")
    
    # Create the comparison visualizations
    create_comparison_visualization(benchmark_data, 'L1', os.path.join(output_dir, 'l1_prediction_potential.png'))
    create_comparison_visualization(benchmark_data, 'L2', os.path.join(output_dir, 'l2_prediction_potential.png'))
    create_dual_comparison_visualization(benchmark_data, os.path.join(output_dir, 'l1_vs_l2_prediction_potential.png'))

if __name__ == "__main__":
    main()