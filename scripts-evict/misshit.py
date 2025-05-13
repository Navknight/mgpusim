#!/usr/bin/env python3
"""
This script analyzes metrics.csv files from multiple benchmarks 
and generates graphs comparing L1V and L2 cache read hits and misses.
"""

import os
import argparse
import csv
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

def parse_metrics_csv(csv_path):
    """
    Parse metrics.csv file and extract cache read hit/miss statistics.
    
    Args:
        csv_path: Path to the metrics.csv file
        
    Returns:
        Dictionary with cache metrics
    """
    try:
        cache_data = {
            'l1v': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l1i': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l1s': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l2': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0}
        }
        
        with open(csv_path, 'r') as f:
            csv_reader = csv.reader(f)
            # Skip header
            next(csv_reader)
            
            for row in csv_reader:
                if len(row) < 4:
                    continue
                
                where = row[1].strip()
                what = row[2].strip()
                try:
                    value = float(row[3])
                except ValueError:
                    continue  # Skip rows with non-numeric values
                
                # Extract L1V cache metrics
                if 'L1VCache' in where:
                    if what == 'read-hit':
                        cache_data['l1v']['hits'] += value
                    elif what == 'read-miss':
                        cache_data['l1v']['misses'] += value
                    elif what == 'read-mshr-hit':
                        # Count MSHR hits as cache hits since they avoid going to next level
                        cache_data['l1v']['hits'] += value
                
                # Extract L1I cache metrics
                elif 'L1ICache' in where:
                    if what == 'read-hit':
                        cache_data['l1i']['hits'] += value
                    elif what == 'read-miss':
                        cache_data['l1i']['misses'] += value
                    elif what == 'read-mshr-hit':
                        cache_data['l1i']['hits'] += value
                
                # Extract L1S cache metrics
                elif 'L1SCache' in where:
                    if what == 'read-hit':
                        cache_data['l1s']['hits'] += value
                    elif what == 'read-miss':
                        cache_data['l1s']['misses'] += value
                    elif what == 'read-mshr-hit':
                        cache_data['l1s']['hits'] += value
                
                # Extract L2 cache metrics - be more flexible with matching
                elif '.L2[' in where:
                    if what == 'read-hit':
                        cache_data['l2']['hits'] += value
                    elif what == 'read-miss':
                        cache_data['l2']['misses'] += value
                    elif what == 'read-mshr-hit':
                        # Count MSHR hits with regular hits
                        cache_data['l2']['hits'] += value
        
        # Calculate hit and miss rates
        for cache_type in cache_data:
            total_accesses = cache_data[cache_type]['hits'] + cache_data[cache_type]['misses']
            if total_accesses > 0:
                cache_data[cache_type]['hit_rate'] = (cache_data[cache_type]['hits'] / total_accesses) * 100
                cache_data[cache_type]['miss_rate'] = (cache_data[cache_type]['misses'] / total_accesses) * 100
        
        return cache_data
    
    except Exception as e:
        print(f"Error parsing metrics file {csv_path}: {str(e)}")
        return {
            'l1v': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l1i': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l1s': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0},
            'l2': {'hits': 0, 'misses': 0, 'hit_rate': 0, 'miss_rate': 0}
        }

def create_hit_rate_comparison(benchmark_data, output_file, benchmark_order=None):
    """
    Create a chart comparing hit rates across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to cache metrics
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if (data['l1v']['hits'] + data['l1v']['misses'] > 0 or 
                           data['l2']['hits'] + data['l2']['misses'] > 0)}
    
    if not valid_benchmarks:
        print("No valid benchmark data for hit rate comparison")
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
    l1v_hit_rates = [data['l1v']['hit_rate'] for _, data in ordered_benchmarks]
    l2_hit_rates = [data['l2']['hit_rate'] for _, data in ordered_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(10, 5))
    
    # Plot grouped bars with patterns
    bar_width = 0.35
    x = np.arange(len(benchmark_names))
    
    # Use different hatches for L1V and L2
    bars1 = plt.bar(x - bar_width/2, l1v_hit_rates, bar_width, label='L1V Cache', 
                   color='white', edgecolor='black', hatch='////')
    bars2 = plt.bar(x + bar_width/2, l2_hit_rates, bar_width, label='L2 Cache', 
                   color='white', edgecolor='black', hatch='....')
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if l1v_hit_rates[i] > 0:
            plt.text(i - bar_width/2, l1v_hit_rates[i] + 1, f'{l1v_hit_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        if l2_hit_rates[i] > 0:
            plt.text(i + bar_width/2, l2_hit_rates[i] + 1, f'{l2_hit_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure the plot for readability
    plt.title('L1V vs L2 Cache Read Hit Rates', fontsize=14, fontweight='bold')
    plt.xlabel('Benchmark', fontsize=12)
    plt.ylabel('Hit Rate (%)', fontsize=12)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=10)
    plt.ylim(0, 105)  # Add a little space for the percentage labels
    
    plt.legend(loc='lower right', fontsize=10, frameon=True, framealpha=0.9)
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add horizontal lines showing the average hit rates
    if l1v_hit_rates:
        l1v_avg = np.mean([rate for rate in l1v_hit_rates if rate > 0])
        plt.axhline(y=l1v_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
        plt.text(len(benchmark_names) - 1, l1v_avg + 1, f'L1V Avg: {l1v_avg:.1f}%', 
                ha='right', va='bottom', fontsize=9, color='black')
    
    if l2_hit_rates:
        # Use values > 0 to avoid including benchmarks with no L2 accesses
        positive_l2_rates = [rate for rate in l2_hit_rates if rate > 0]
        if positive_l2_rates:
            l2_avg = np.mean(positive_l2_rates)
            plt.axhline(y=l2_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
            plt.text(0, l2_avg + 1, f'L2 Avg: {l2_avg:.1f}%', 
                    ha='left', va='bottom', fontsize=9, color='black')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved hit rate comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved hit rate comparison as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    
    # Don't calculate average if there are no positive values
    l1v_json_avg = float(l1v_avg) if l1v_hit_rates and any(rate > 0 for rate in l1v_hit_rates) else 0
    l2_json_avg = float(l2_avg) if 'l2_avg' in locals() and positive_l2_rates else 0
    
    json_data = {
        'benchmarks': {name: {'L1V_hit_rate': float(l1v), 'L2_hit_rate': float(l2)} 
                      for name, l1v, l2 in zip(benchmark_names, l1v_hit_rates, l2_hit_rates)},
        'L1V_average_hit_rate': l1v_json_avg,
        'L2_average_hit_rate': l2_json_avg
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved hit rate comparison data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_miss_rate_comparison(benchmark_data, output_file, benchmark_order=None):
    """
    Create a chart comparing miss rates across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to cache metrics
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if (data['l1v']['hits'] + data['l1v']['misses'] > 0 or 
                           data['l2']['hits'] + data['l2']['misses'] > 0)}
    
    if not valid_benchmarks:
        print("No valid benchmark data for miss rate comparison")
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
    l1v_miss_rates = [data['l1v']['miss_rate'] for _, data in ordered_benchmarks]
    l2_miss_rates = [data['l2']['miss_rate'] for _, data in ordered_benchmarks]
    
    # Set up the figure for publication quality
    plt.figure(figsize=(10, 5))
    
    # Plot grouped bars with patterns
    bar_width = 0.35
    x = np.arange(len(benchmark_names))
    
    # Use different hatches for L1V and L2
    bars1 = plt.bar(x - bar_width/2, l1v_miss_rates, bar_width, label='L1V Cache', 
                   color='white', edgecolor='black', hatch='////')
    bars2 = plt.bar(x + bar_width/2, l2_miss_rates, bar_width, label='L2 Cache', 
                   color='white', edgecolor='black', hatch='....')
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if l1v_miss_rates[i] > 0:
            plt.text(i - bar_width/2, l1v_miss_rates[i] + 0.5, f'{l1v_miss_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        if l2_miss_rates[i] > 0:
            plt.text(i + bar_width/2, l2_miss_rates[i] + 0.5, f'{l2_miss_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure the plot for readability
    plt.title('L1V vs L2 Cache Read Miss Rates', fontsize=14, fontweight='bold')
    plt.xlabel('Benchmark', fontsize=12)
    plt.ylabel('Miss Rate (%)', fontsize=12)
    plt.xticks(x, benchmark_names, rotation=45, ha='right', fontsize=10)
    
    # Set y-axis limit based on data
    max_miss_rate = max([max(l1v_miss_rates or [0]), max(l2_miss_rates or [0])])
    plt.ylim(0, min(100, max_miss_rate * 1.2 + 0.5))  # Add space for labels
    
    plt.legend(loc='upper right', fontsize=10, frameon=True, framealpha=0.9)
    plt.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add horizontal lines showing the average miss rates
    if l1v_miss_rates:
        positive_l1v_rates = [rate for rate in l1v_miss_rates if rate > 0]
        if positive_l1v_rates:
            l1v_avg = np.mean(positive_l1v_rates)
            plt.axhline(y=l1v_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
            plt.text(len(benchmark_names) - 1, l1v_avg + 0.5, f'L1V Avg: {l1v_avg:.1f}%', 
                    ha='right', va='bottom', fontsize=9, color='black')
    
    if l2_miss_rates:
        positive_l2_rates = [rate for rate in l2_miss_rates if rate > 0]
        if positive_l2_rates:
            l2_avg = np.mean(positive_l2_rates)
            plt.axhline(y=l2_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
            plt.text(0, l2_avg + 0.5, f'L2 Avg: {l2_avg:.1f}%', 
                    ha='left', va='bottom', fontsize=9, color='black')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved miss rate comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved miss rate comparison as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    
    # Don't calculate average if there are no positive values
    l1v_json_avg = float(l1v_avg) if 'l1v_avg' in locals() and positive_l1v_rates else 0
    l2_json_avg = float(l2_avg) if 'l2_avg' in locals() and positive_l2_rates else 0
    
    json_data = {
        'benchmarks': {name: {'L1V_miss_rate': float(l1v), 'L2_miss_rate': float(l2)} 
                      for name, l1v, l2 in zip(benchmark_names, l1v_miss_rates, l2_miss_rates)},
        'L1V_average_miss_rate': l1v_json_avg,
        'L2_average_miss_rate': l2_json_avg
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved miss rate comparison data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_absolute_comparison(benchmark_data, output_file, benchmark_order=None):
    """
    Create a chart comparing absolute hit and miss counts across benchmarks.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to cache metrics
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if (data['l1v']['hits'] + data['l1v']['misses'] > 0 or 
                           data['l2']['hits'] + data['l2']['misses'] > 0)}
    
    if not valid_benchmarks:
        print("No valid benchmark data for absolute hit/miss comparison")
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
    
    # Create a figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Left subplot - L1V absolute hits and misses
    l1v_hits = [data['l1v']['hits'] for _, data in ordered_benchmarks]
    l1v_misses = [data['l1v']['misses'] for _, data in ordered_benchmarks]
    
    # Use a bar plot with log scale for absolute values
    x = np.arange(len(benchmark_names))
    bar_width = 0.4
    
    bars1 = ax1.bar(x - bar_width/2, l1v_hits, bar_width, label='Hits', 
                  color='white', edgecolor='black', hatch='////')
    bars2 = ax1.bar(x + bar_width/2, l1v_misses, bar_width, label='Misses', 
                  color='white', edgecolor='black', hatch='....')
    
    # Configure left subplot for L1V
    ax1.set_title('L1V Cache Absolute Hits and Misses', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Benchmark', fontsize=10)
    ax1.set_ylabel('Access Count (log scale)', fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(benchmark_names, rotation=45, ha='right', fontsize=8)
    
    # Use log scale for better visualization of wide-ranging values
    if max(l1v_hits + l1v_misses) > 0:
        # Add a small offset to handle zeros in log scale
        ax1.set_yscale('log')
        # Add text annotations with actual values at the top of each bar
        for i, (hits, misses) in enumerate(zip(l1v_hits, l1v_misses)):
            if hits > 0:
                ax1.text(i - bar_width/2, hits, f'{hits:.0f}', 
                        ha='center', va='bottom', fontsize=7, rotation=90)
            if misses > 0:
                ax1.text(i + bar_width/2, misses, f'{misses:.0f}', 
                        ha='center', va='bottom', fontsize=7, rotation=90)
        
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Right subplot - L2 absolute hits and misses
    l2_hits = [data['l2']['hits'] for _, data in ordered_benchmarks]
    l2_misses = [data['l2']['misses'] for _, data in ordered_benchmarks]
    
    bars3 = ax2.bar(x - bar_width/2, l2_hits, bar_width, label='Hits', 
                  color='white', edgecolor='black', hatch='////')
    bars4 = ax2.bar(x + bar_width/2, l2_misses, bar_width, label='Misses', 
                  color='white', edgecolor='black', hatch='....')
    
    # Configure right subplot for L2
    ax2.set_title('L2 Cache Absolute Hits and Misses', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Benchmark', fontsize=10)
    ax2.set_ylabel('Access Count (log scale)', fontsize=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(benchmark_names, rotation=45, ha='right', fontsize=8)
    
    # Use log scale for better visualization of wide-ranging values
    if max(l2_hits + l2_misses) > 0:
        # Add a small constant to all values to handle zeros in log scale
        ax2.set_yscale('log')
        # Add text annotations with actual values at the top of each bar
        for i, (hits, misses) in enumerate(zip(l2_hits, l2_misses)):
            if hits > 0:
                ax2.text(i - bar_width/2, hits, f'{hits:.0f}', 
                        ha='center', va='bottom', fontsize=7, rotation=90)
            if misses > 0:
                ax2.text(i + bar_width/2, misses, f'{misses:.0f}', 
                        ha='center', va='bottom', fontsize=7, rotation=90)
        
    ax2.legend(loc='upper right', fontsize=8)
    ax2.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add overall title
    fig.suptitle('Cache Access Patterns Across Benchmarks', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    fig.subplots_adjust(top=0.88)  # Make room for suptitle
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved absolute hit/miss comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved absolute hit/miss comparison as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    json_data = {
        'benchmarks': {name: {
            'L1V_hits': int(l1v_h),
            'L1V_misses': int(l1v_m),
            'L2_hits': int(l2_h),
            'L2_misses': int(l2_m)
        } for name, l1v_h, l1v_m, l2_h, l2_m in zip(benchmark_names, l1v_hits, l1v_misses, l2_hits, l2_misses)}
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved absolute hit/miss data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def create_side_by_side_comparison(benchmark_data, output_file, benchmark_order=None):
    """
    Create a side-by-side visualization of hit rates and miss rates.
    Optimized for LaTeX display.
    
    Args:
        benchmark_data: Dictionary mapping benchmark names to cache metrics
        output_file: Path to save the visualization
        benchmark_order: Optional list of benchmark names to determine the order
    """
    # Filter out benchmarks with no data
    valid_benchmarks = {name: data for name, data in benchmark_data.items() 
                       if (data['l1v']['hits'] + data['l1v']['misses'] > 0 or 
                           data['l2']['hits'] + data['l2']['misses'] > 0)}
    
    if not valid_benchmarks:
        print("No valid benchmark data for side-by-side comparison")
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
    l1v_hit_rates = [data['l1v']['hit_rate'] for _, data in ordered_benchmarks]
    l2_hit_rates = [data['l2']['hit_rate'] for _, data in ordered_benchmarks]
    l1v_miss_rates = [data['l1v']['miss_rate'] for _, data in ordered_benchmarks]
    l2_miss_rates = [data['l2']['miss_rate'] for _, data in ordered_benchmarks]
    
    # Create a figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Left subplot - Hit Rates
    bar_width = 0.35
    x = np.arange(len(benchmark_names))
    
    bars1 = ax1.bar(x - bar_width/2, l1v_hit_rates, bar_width, label='L1V Cache', 
                  color='white', edgecolor='black', hatch='////', linewidth=1.2)
    bars2 = ax1.bar(x + bar_width/2, l2_hit_rates, bar_width, label='L2 Cache', 
                  color='white', edgecolor='black', hatch='....', linewidth=1.2)
    
    # Add percentage labels on top of significant bars
    for i in range(len(benchmark_names)):
        if l1v_hit_rates[i] > 0:
            ax1.text(i - bar_width/2, l1v_hit_rates[i] + 1, f'{l1v_hit_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        if l2_hit_rates[i] > 0:
            ax1.text(i + bar_width/2, l2_hit_rates[i] + 1, f'{l2_hit_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure left subplot
    ax1.set_title('Cache Read Hit Rates', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Benchmark', fontsize=10)
    ax1.set_ylabel('Hit Rate (%)', fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(benchmark_names, rotation=40, ha='right', fontsize=8)
    ax1.set_ylim(0, 105)  # Set y limit to accommodate labels
    
    ax1.legend(loc='lower right', fontsize=8, frameon=True, framealpha=0.9)
    ax1.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add average lines for hit rates
    if l1v_hit_rates:
        positive_l1v_rates = [rate for rate in l1v_hit_rates if rate > 0]
        if positive_l1v_rates:
            l1v_avg = np.mean(positive_l1v_rates)
            ax1.axhline(y=l1v_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
            ax1.text(len(benchmark_names) - 1, l1v_avg + 1, f'L1V Avg: {l1v_avg:.1f}%', 
                    ha='right', va='bottom', fontsize=8, color='black')
    
    if l2_hit_rates:
        positive_l2_rates = [rate for rate in l2_hit_rates if rate > 0]
        if positive_l2_rates:
            l2_avg = np.mean(positive_l2_rates)
            ax1.axhline(y=l2_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
            ax1.text(0, l2_avg + 1, f'L2 Avg: {l2_avg:.1f}%', 
                    ha='left', va='bottom', fontsize=8, color='black')
    
    # Right subplot - Miss Rates
    bars3 = ax2.bar(x - bar_width/2, l1v_miss_rates, bar_width, label='L1V Cache', 
                  color='white', edgecolor='black', hatch='////', linewidth=1.2)
    bars4 = ax2.bar(x + bar_width/2, l2_miss_rates, bar_width, label='L2 Cache', 
                  color='white', edgecolor='black', hatch='....', linewidth=1.2)
    
    # Add percentage labels on top of bars
    for i in range(len(benchmark_names)):
        if l1v_miss_rates[i] > 0:
            ax2.text(i - bar_width/2, l1v_miss_rates[i] + 0.5, f'{l1v_miss_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        if l2_miss_rates[i] > 0:
            ax2.text(i + bar_width/2, l2_miss_rates[i] + 0.5, f'{l2_miss_rates[i]:.1f}%', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Configure right subplot
    ax2.set_title('Cache Read Miss Rates', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Benchmark', fontsize=10)
    ax2.set_ylabel('Miss Rate (%)', fontsize=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(benchmark_names, rotation=40, ha='right', fontsize=8)
    
    # Set y-axis limit based on data
    max_miss_rate = max([max(l1v_miss_rates or [0]), max(l2_miss_rates or [0])])
    ax2.set_ylim(0, min(100, max_miss_rate * 1.2 + 1))  # Add space for labels
    
    ax2.legend(loc='upper right', fontsize=8, frameon=True, framealpha=0.9)
    ax2.grid(axis='y', alpha=0.3, linestyle=':')
    
    # Add average lines for miss rates
    if l1v_miss_rates:
        positive_l1v_miss_rates = [rate for rate in l1v_miss_rates if rate > 0]
        if positive_l1v_miss_rates:
            l1v_miss_avg = np.mean(positive_l1v_miss_rates)
            ax2.axhline(y=l1v_miss_avg, color='black', linestyle=':', linewidth=1, alpha=0.7)
            ax2.text(len(benchmark_names) - 1, l1v_miss_avg + 0.5, f'L1V Avg: {l1v_miss_avg:.1f}%', 
                    ha='right', va='bottom', fontsize=8, color='black')
    
    if l2_miss_rates:
        positive_l2_miss_rates = [rate for rate in l2_miss_rates if rate > 0]
        if positive_l2_miss_rates:
            l2_miss_avg = np.mean(positive_l2_miss_rates)
            ax2.axhline(y=l2_miss_avg, color='black', linestyle='--', linewidth=1, alpha=0.7)
            ax2.text(0, l2_miss_avg + 0.5, f'L2 Avg: {l2_miss_avg:.1f}%', 
                    ha='left', va='bottom', fontsize=8, color='black')
    
    # Add overall title
    fig.suptitle('L1V vs L2 Cache Performance Across Benchmarks', fontsize=14, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout()
    fig.subplots_adjust(top=0.88, wspace=0.2)  # Reduce space between subplots
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved side-by-side comparison to {output_file}")
    
    # Also save as PDF for publication quality
    pdf_path = os.path.splitext(output_file)[0] + '.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"Saved side-by-side comparison as PDF: {pdf_path}")
    
    # Save the raw data as JSON
    json_path = os.path.splitext(output_file)[0] + '.json'
    
    # Initialize with defaults
    l1v_avg_val = 0
    l2_avg_val = 0
    l1v_miss_avg_val = 0
    l2_miss_avg_val = 0
    
    # Update if averages were calculated
    if 'l1v_avg' in locals() and positive_l1v_rates:
        l1v_avg_val = float(l1v_avg)
    if 'l2_avg' in locals() and positive_l2_rates:
        l2_avg_val = float(l2_avg)
    if 'l1v_miss_avg' in locals() and positive_l1v_miss_rates:
        l1v_miss_avg_val = float(l1v_miss_avg)
    if 'l2_miss_avg' in locals() and positive_l2_miss_rates:
        l2_miss_avg_val = float(l2_miss_avg)
    
    json_data = {
        'benchmarks': {name: {
            'L1V_hit_rate': float(l1v_h),
            'L2_hit_rate': float(l2_h),
            'L1V_miss_rate': float(l1v_m),
            'L2_miss_rate': float(l2_m)
        } for name, l1v_h, l2_h, l1v_m, l2_m in zip(
            benchmark_names, l1v_hit_rates, l2_hit_rates, l1v_miss_rates, l2_miss_rates
        )},
        'L1V_average_hit_rate': l1v_avg_val,
        'L2_average_hit_rate': l2_avg_val,
        'L1V_average_miss_rate': l1v_miss_avg_val,
        'L2_average_miss_rate': l2_miss_avg_val
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved side-by-side comparison data to {json_path}")
    
    # Close the figure to free memory
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Compare L1V and L2 cache read hits/misses across benchmarks')
    parser.add_argument('--benchmark_dir', type=str, required=True, help='Root directory containing benchmark folders')
    parser.add_argument('--output_dir', type=str, default='cache_comparison_results', help='Output directory for visualizations')
    parser.add_argument('--sort', choices=['alpha', 'none'], default='none', 
                       help='Sorting order for benchmarks (alpha=alphabetical, none=preserve directory order)')
    parser.add_argument('--side_by_side', action='store_true', default=True,
                       help='Generate side-by-side visualizations optimized for LaTeX')
    
    args = parser.parse_args()
    
    benchmark_dir = args.benchmark_dir
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Dictionary to store cache metrics for each benchmark
    benchmark_data = {}
    
    # Get all benchmark directories while preserving order
    benchmarks = []
    for benchmark in os.listdir(benchmark_dir):
        benchmark_path = os.path.join(benchmark_dir, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
            
        metrics_path = os.path.join(benchmark_path, 'metrics.csv')
        if not os.path.exists(metrics_path):
            print(f"No metrics.csv found for benchmark {benchmark}")
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
        metrics_path = os.path.join(benchmark_path, 'metrics.csv')
        
        print(f"Processing benchmark: {benchmark}")
        
        # Parse the metrics file to get cache data
        cache_data = parse_metrics_csv(metrics_path)
        
        # Store the results
        benchmark_data[benchmark] = cache_data
        
        # Report the results
        print(f"  L1V Cache:")
        print(f"    - Hits: {cache_data['l1v']['hits']}")
        print(f"    - Misses: {cache_data['l1v']['misses']}")
        print(f"    - Hit Rate: {cache_data['l1v']['hit_rate']:.2f}%")
        
        print(f"  L2 Cache:")
        print(f"    - Hits: {cache_data['l2']['hits']}")
        print(f"    - Misses: {cache_data['l2']['misses']}")
        print(f"    - Hit Rate: {cache_data['l2']['hit_rate']:.2f}%")
    
    # Generate side-by-side visualization (default to True for LaTeX optimization)
    if args.side_by_side:
        create_side_by_side_comparison(benchmark_data, 
                                     os.path.join(output_dir, 'cache_side_by_side.png'),
                                     benchmark_order)
    
    # Create individual comparison visualizations
    create_hit_rate_comparison(benchmark_data, 
                             os.path.join(output_dir, 'hit_rate_comparison.png'), 
                             benchmark_order)
    
    create_miss_rate_comparison(benchmark_data, 
                              os.path.join(output_dir, 'miss_rate_comparison.png'), 
                              benchmark_order)
    
    create_absolute_comparison(benchmark_data, 
                             os.path.join(output_dir, 'absolute_comparison.png'), 
                             benchmark_order)

if __name__ == "__main__":
    main()