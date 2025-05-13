import os
import argparse
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
import json

def parse_log_file(log_file_path):
    """
    Parse the log.txt file containing cache access histograms.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Dictionary with L1 and L2 cache data
    """
    print(f"Parsing log file: {log_file_path}")
    
    try:
        with open(log_file_path, 'r') as f:
            content = f.read()
        
        # Split into L1 and L2 sections
        sections = content.split('\n\n')
        
        # There should be at least two sections - L1 and L2
        if len(sections) < 2:
            print(f"Warning: Log file may be malformed. Found {len(sections)} sections instead of 2+.")
            # Try to find L1 and L2 sections by their headers
            l1_index = content.find("L1 Cache")
            l2_index = content.find("L2 Cache")
            
            if l1_index >= 0 and l2_index >= 0:
                # Determine which comes first
                if l1_index < l2_index:
                    l1_section = content[l1_index:l2_index].strip()
                    l2_section = content[l2_index:].strip()
                else:
                    l2_section = content[l2_index:l1_index].strip()
                    l1_section = content[l1_index:].strip()
            elif l2_index >= 0:
                l2_section = content[l2_index:].strip()
                l1_section = ""
            elif l1_index >= 0:
                l1_section = content[l1_index:].strip()
                l2_section = ""
            else:
                print("Error: Could not identify L1 or L2 cache sections in log file")
                return None
        else:
            # Find the L1 and L2 sections by their headers
            l1_section = next((s for s in sections if s.startswith("L1 Cache")), "")
            l2_section = next((s for s in sections if s.startswith("L2 Cache")), "")
            
            if not l1_section and not l2_section:
                print("Error: Could not find L1 or L2 cache sections in log file")
                return None
        
        # Parse the sections
        l1_data = parse_cache_section(l1_section, 'L1') if l1_section else []
        l2_data = parse_cache_section(l2_section, 'L2') if l2_section else []
        
        print(f"Successfully parsed {len(l1_data)} L1 cache entries and {len(l2_data)} L2 cache entries")
        
        return {
            'L1': l1_data,
            'L2': l2_data
        }
    
    except Exception as e:
        print(f"Error parsing log file: {str(e)}")
        return None

def parse_cache_section(section, cache_type):
    """
    Parse a section of cache data (L1 or L2).
    
    Args:
        section: The text section to parse
        cache_type: 'L1' or 'L2'
        
    Returns:
        List of dictionaries with histogram and totalEvictions fields
    """
    # Skip the header line
    lines = section.split('\n')[1:] if section.startswith(f"{cache_type} Cache") else section.split('\n')
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
                # If no histogram found, skip this line
                continue
            
            # Extract total evictions
            evictions_match = re.search(r'TotalEvictions:(\d+)', line)
            if evictions_match:
                entry['totalEvictions'] = int(evictions_match.group(1))
            else:
                # If no evictions count found, skip this line
                continue
            
            entry['sample_num'] = i + 1  # Add sample number for tracking
            entry['cache_type'] = cache_type
            
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

def analyze_cache_data(cache_data):
    """
    Analyze the parsed cache data.
    
    Args:
        cache_data: Dictionary with L1 and L2 cache data
        
    Returns:
        Dictionary with analysis results
    """
    results = {}
    
    for cache_type in ['L1', 'L2']:
        if cache_type not in cache_data or not cache_data[cache_type]:
            print(f"No {cache_type} cache data to analyze")
            continue
        
        data = cache_data[cache_type]
        analysis = analyze_access_patterns(data)
        distribution = create_access_distribution(data)
        
        results[cache_type] = {
            'analysis': analysis,
            'distribution': distribution
        }
    
    return results

def analyze_access_patterns(data):
    """
    Analyze access patterns in cache data.
    
    Args:
        data: List of dictionaries with histogram and totalEvictions fields
        
    Returns:
        Dictionary with analysis metrics
    """
    if not data:
        return None
    
    cache_type = data[0]['cache_type']
    total_entries = len(data)
    
    # Initialize counters
    dead_blocks = 0
    one_access_blocks = 0
    high_access_blocks = 0
    total_evictions = 0
    
    # Determine the high access key format for this cache data
    # Look at the first entry to determine the format
    high_access_keys = ['100+', '>100']  # Possible formats
    found_high_access_key = None
    
    for key in high_access_keys:
        if key in data[0]['histogram']:
            found_high_access_key = key
            break
    
    if not found_high_access_key:
        # If none of the known formats are found, try to find any key that might represent high access
        for key in data[0]['histogram'].keys():
            if '100' in key:
                found_high_access_key = key
                break
    
    # If we still didn't find a high access key, use a default based on cache type
    if not found_high_access_key:
        found_high_access_key = '100+' if cache_type == 'L1' else '>100'
        print(f"Warning: Could not detect high access key format. Using default: {found_high_access_key}")
    
    for entry in data:
        total_evictions += entry['totalEvictions']
        
        if '0' in entry['histogram']:
            dead_blocks += entry['histogram']['0']
        
        if '1' in entry['histogram']:
            one_access_blocks += entry['histogram']['1']
        
        if found_high_access_key in entry['histogram']:
            high_access_blocks += entry['histogram'][found_high_access_key]
    
    # Calculate statistics
    avg_dead_blocks = dead_blocks / total_entries if total_entries > 0 else 0
    avg_one_access_blocks = one_access_blocks / total_entries if total_entries > 0 else 0
    avg_high_access_blocks = high_access_blocks / total_entries if total_entries > 0 else 0
    avg_total_evictions = total_evictions / total_entries if total_entries > 0 else 0
    
    # Calculate percentages, handling zero division
    avg_dead_blocks_percent = (avg_dead_blocks / avg_total_evictions) * 100 if avg_total_evictions > 0 else 0
    avg_one_access_blocks_percent = (avg_one_access_blocks / avg_total_evictions) * 100 if avg_total_evictions > 0 else 0
    avg_high_access_blocks_percent = (avg_high_access_blocks / avg_total_evictions) * 100 if avg_total_evictions > 0 else 0
    
    return {
        'cache_type': cache_type,
        'total_entries': total_entries,
        'avg_dead_blocks': avg_dead_blocks,
        'avg_one_access_blocks': avg_one_access_blocks,
        'avg_high_access_blocks': avg_high_access_blocks,
        'avg_total_evictions': avg_total_evictions,
        'avg_dead_blocks_percent': avg_dead_blocks_percent,
        'avg_one_access_blocks_percent': avg_one_access_blocks_percent,
        'avg_high_access_blocks_percent': avg_high_access_blocks_percent,
        'total_dead_blocks': dead_blocks,
        'total_one_access_blocks': one_access_blocks,
        'total_high_access_blocks': high_access_blocks,
        'total_evictions': total_evictions,
        'high_access_key': found_high_access_key
    }

def create_access_distribution(data):
    """
    Create a distribution of access counts.
    
    Args:
        data: List of dictionaries with histogram and totalEvictions fields
        
    Returns:
        Dictionary with counts and percentages
    """
    if not data:
        return None
    
    cache_type = data[0]['cache_type']
    
    # Determine the high access key format for this cache data
    # Look at the first entry to determine the format
    high_access_keys = ['100+', '>100']  # Possible formats
    found_high_access_key = None
    
    for key in high_access_keys:
        if key in data[0]['histogram']:
            found_high_access_key = key
            break
    
    if not found_high_access_key:
        # If none of the known formats are found, try to find any key that might represent high access
        for key in data[0]['histogram'].keys():
            if '100' in key:
                found_high_access_key = key
                break
    
    # If we still didn't find a high access key, use a default based on cache type
    if not found_high_access_key:
        found_high_access_key = '100+' if cache_type == 'L1' else '>100'
        print(f"Warning: Could not detect high access key format. Using default: {found_high_access_key}")
    
    # Define the access categories
    categories = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
        '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100'
    ]
    all_categories = categories + [found_high_access_key]
    
    # Initialize counter dictionary
    counts = {cat: 0 for cat in all_categories}
    
    # Aggregate counts across all samples
    for entry in data:
        histogram = entry['histogram']
        for cat in all_categories:
            if cat in histogram:
                counts[cat] += histogram[cat]
    
    # Calculate total and percentages
    total = sum(counts.values())
    if total > 0:
        percentages = {cat: (counts[cat] / total) * 100 for cat in all_categories}
    else:
        percentages = {cat: 0.0 for cat in all_categories}
        print(f"Warning: No data found for {cache_type} cache distribution (total count is zero)")
    
    return {
        'cache_type': cache_type,
        'categories': all_categories,
        'counts': counts,
        'percentages': percentages,
        'total': total,
        'high_access_key': found_high_access_key
    }

def generate_visualizations(analysis_results, output_dir):
    """
    Generate visualizations from the analysis results.
    
    Args:
        analysis_results: Dictionary with analysis results
        output_dir: Directory to save the visualizations
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Check what cache types we have data for
    available_caches = [cache_type for cache_type in ['L1', 'L2'] if cache_type in analysis_results]
    
    if not available_caches:
        print("No cache data available for visualization")
        return
    
    # If we have both L1 and L2 data, create comparative visualizations
    if 'L1' in available_caches and 'L2' in available_caches:
        l1_dist = analysis_results['L1']['distribution']
        l2_dist = analysis_results['L2']['distribution']
        l1_analysis = analysis_results['L1']['analysis']
        l2_analysis = analysis_results['L2']['analysis']
        
        # Check if we have enough data to create visualizations
        if (l1_dist['total'] > 0 and l2_dist['total'] > 0 and 
            l1_analysis['avg_total_evictions'] > 0 and l2_analysis['avg_total_evictions'] > 0):
            
            # Generate comparative visualizations
            plot_access_distribution(l1_dist, l2_dist, output_dir)
            plot_cumulative_distribution(l1_dist, l2_dist, output_dir)
            create_prediction_potential_visualization(l2_analysis, output_dir)
            create_comprehensive_visualization(l1_dist, l2_dist, l1_analysis, l2_analysis, output_dir)
        else:
            print("Insufficient data for comparative visualizations")
    
    # Generate individual cache visualizations
    for cache_type in available_caches:
        dist = analysis_results[cache_type]['distribution']
        analysis = analysis_results[cache_type]['analysis']
        
        # Check if we have enough data
        if dist['total'] > 0 and analysis['avg_total_evictions'] > 0:
            # Generate single-cache visualizations
            plot_single_cache_distribution(dist, output_dir)
            
            # For L2 cache, create dead block prediction visualizations
            if cache_type == 'L2':
                create_prediction_potential_visualization(analysis, output_dir)
        else:
            print(f"Insufficient data for {cache_type} cache visualizations")
    
    print(f"Visualizations saved to {output_dir}")

def plot_access_distribution(l1_dist, l2_dist, output_dir):
    """
    Create a plot showing access distribution for L1 and L2 caches.
    
    Args:
        l1_dist: L1 cache access distribution
        l2_dist: L2 cache access distribution
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(15, 8))
    
    # Create a bar chart for L2 (primary focus for dead block prediction)
    # Exclude the high access category for better visibility
    l2_high_access_key = l2_dist['high_access_key']
    categories = [cat for cat in l2_dist['categories'] if cat != l2_high_access_key]
    values = [l2_dist['percentages'][cat] for cat in categories]
    
    ax = plt.subplot(111)
    bars = ax.bar(categories, values, color='#3182bd', alpha=0.8)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        if height > 2.0:  # Only add labels for significant bars
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{height:.1f}%', ha='center', va='bottom')
    
    # Add a text annotation for dead block potential
    dead_block_potential = l2_dist['percentages']['0'] + l2_dist['percentages']['1']
    plt.annotate(f'Dead Block Prediction Potential: {dead_block_potential:.1f}%',
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow', alpha=0.8))
    
    plt.title('L2 Cache Access Distribution Before Eviction', fontsize=16)
    plt.xlabel('Number of Accesses Before Eviction', fontsize=14)
    plt.ylabel('Percentage of Total Evictions (%)', fontsize=14)
    plt.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'l2_access_distribution.png'), dpi=300)
    plt.close()
    
    # Create a more specialized plot to focus on the key dead block indicators
    plt.figure(figsize=(12, 6))
    
    # Focus on just the first few categories
    focus_categories = ['0', '1', '2', '3', '4', '5']
    l1_values = [l1_dist['percentages'][cat] for cat in focus_categories]
    l2_values = [l2_dist['percentages'][cat] for cat in focus_categories]
    
    x = np.arange(len(focus_categories))
    width = 0.35
    
    ax = plt.subplot(111)
    ax.bar(x - width/2, l2_values, width, label='L2 Cache', color='#3182bd')
    ax.bar(x + width/2, l1_values, width, label='L1 Cache', color='#de2d26')
    
    plt.title('Dead Block Identification Opportunity (Low Access Counts)', fontsize=16)
    plt.xlabel('Number of Accesses Before Eviction', fontsize=14)
    plt.ylabel('Percentage of Cache Evictions (%)', fontsize=14)
    plt.xticks(x, focus_categories)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    # Add detailed annotations
    for i, (l2_val, l1_val) in enumerate(zip(l2_values, l1_values)):
        if l2_val > 2.0:
            plt.annotate(f'{l2_val:.1f}%', xy=(i - width/2, l2_val + 0.5),
                        ha='center', va='bottom', color='#3182bd')
        if l1_val > 2.0:
            plt.annotate(f'{l1_val:.1f}%', xy=(i + width/2, l1_val + 0.5),
                        ha='center', va='bottom', color='#de2d26')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cache_comparison_low_access.png'), dpi=300)
    plt.close()

def plot_single_cache_distribution(dist, output_dir):
    """
    Create a plot showing access distribution for a single cache.
    
    Args:
        dist: Cache access distribution
        output_dir: Directory to save the plot
    """
    cache_type = dist['cache_type']
    plt.figure(figsize=(15, 8))
    
    # Determine how many categories to show based on cache type
    high_access_key = dist['high_access_key']
    if cache_type == 'L1':
        # For L1, show all categories including high access key
        categories = dist['categories']
    else:
        # For L2, exclude high access key for better visibility of lower access counts
        categories = [cat for cat in dist['categories'] if cat != high_access_key]
    
    values = [dist['percentages'][cat] for cat in categories]
    
    ax = plt.subplot(111)
    bars = ax.bar(categories, values, color='#3182bd' if cache_type == 'L2' else '#de2d26', alpha=0.8)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        if height > 2.0:  # Only add labels for significant bars
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{height:.1f}%', ha='center', va='bottom')
    
    # For L2 cache, add an annotation about dead block potential
    if cache_type == 'L2':
        dead_block_potential = dist['percentages']['0'] + dist['percentages']['1']
        plt.annotate(f'Dead Block Prediction Potential: {dead_block_potential:.1f}%',
                    xy=(0.5, 0.95), xycoords='axes fraction',
                    ha='center', va='top',
                    bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow', alpha=0.8))
    
    plt.title(f'{cache_type} Cache Access Distribution Before Eviction', fontsize=16)
    plt.xlabel('Number of Accesses Before Eviction', fontsize=14)
    plt.ylabel('Percentage of Total Evictions (%)', fontsize=14)
    plt.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{cache_type.lower()}_access_distribution.png'), dpi=300)
    plt.close()

def plot_cumulative_distribution(l1_dist, l2_dist, output_dir):
    """
    Create a plot showing cumulative distribution of accesses for L1 and L2 caches.
    
    Args:
        l1_dist: L1 cache access distribution
        l2_dist: L2 cache access distribution
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(15, 8))
    
    # Use a common set of categories that exist in both distributions
    # This ensures we can create a meaningful comparison
    l1_high_access_key = l1_dist['high_access_key']
    l2_high_access_key = l2_dist['high_access_key']
    
    # Get the common categories in the correct order
    standard_categories = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
        '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100'
    ]
    
    # Filter to only include categories that exist in both distributions
    common_categories = [cat for cat in standard_categories if cat in l1_dist['percentages'] and cat in l2_dist['percentages']]
    
    # Add the high access keys at the end
    categories = common_categories + [l1_high_access_key, l2_high_access_key]
    
    # Calculate cumulative percentages
    l1_cumulative = []
    l2_cumulative = []
    
    l1_cum_sum = 0
    l2_cum_sum = 0
    
    for cat in categories:
        # Add L1 percentage if category exists in L1
        if cat in l1_dist['percentages']:
            l1_cum_sum += l1_dist['percentages'][cat]
        l1_cumulative.append(l1_cum_sum)
        
        # Add L2 percentage if category exists in L2
        if cat in l2_dist['percentages']:
            l2_cum_sum += l2_dist['percentages'][cat]
        l2_cumulative.append(l2_cum_sum)
    
    plt.plot(range(len(categories)), l1_cumulative, 'o-', color='#de2d26', label='L1 Cache')
    plt.plot(range(len(categories)), l2_cumulative, 'o-', color='#3182bd', label='L2 Cache')
    
    plt.title('Cumulative Distribution of Cache Block Accesses Before Eviction', fontsize=16)
    plt.xlabel('Number of Accesses', fontsize=14)
    plt.ylabel('Cumulative Percentage (%)', fontsize=14)
    plt.xticks(range(len(categories)), categories, rotation=45)
    plt.grid(alpha=0.3)
    plt.legend()
    
    # Add annotation about dead block prediction potential
    plt.annotate(f'L2: {l2_cumulative[1]:.1f}% of blocks have ≤1 access',
                xy=(1, l2_cumulative[1]),
                xytext=(5, l2_cumulative[1] + 5),
                arrowprops=dict(arrowstyle='->'),
                color='#3182bd')
    
    plt.axhline(y=90, color='gray', linestyle='--', alpha=0.7)
    plt.annotate('90% threshold',
                xy=(0, 90),
                xytext=(1, 91),
                color='gray')
    
    # Find the index where L2 curve crosses 90%
    l2_90_idx = next((i for i, val in enumerate(l2_cumulative) if val >= 90), len(l2_cumulative) - 1)
    if l2_90_idx < len(categories):
        plt.annotate(f'L2: 90% of blocks have ≤{categories[l2_90_idx]} accesses',
                    xy=(l2_90_idx, 90),
                    xytext=(l2_90_idx - 3, 84),
                    arrowprops=dict(arrowstyle='->'),
                    color='#3182bd')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cumulative_access_distribution.png'), dpi=300)
    plt.close()

def create_prediction_potential_visualization(l2_analysis, output_dir):
    """
    Create a chart showing the dead block prediction potential for L2 cache.
    
    Args:
        l2_analysis: L2 cache analysis results
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Define categories and colors
    categories = ['Dead Blocks\n(0 accesses)', 'One Access\nBlocks', 'Multi-Access\nBlocks']
    values = [
        l2_analysis['avg_dead_blocks_percent'],
        l2_analysis['avg_one_access_blocks_percent'],
        100 - l2_analysis['avg_dead_blocks_percent'] - l2_analysis['avg_one_access_blocks_percent']
    ]
    colors = ['#e41a1c', '#377eb8', '#4daf4a']
    
    # Create the pie chart
    patches, texts, autotexts = plt.pie(
        values, 
        labels=categories,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.85,
        explode=(0.05, 0.05, 0)
    )
    
    # Enhance the text
    for text in texts:
        text.set_fontsize(12)
    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')
    
    plt.title('L2 Cache Block Access Distribution', fontsize=16)
    
    # Add a center circle to make it a donut chart
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    plt.gcf().gca().add_artist(centre_circle)
    
    # Add annotation about prediction potential
    prediction_potential = values[0] + values[1]
    plt.annotate(f'Dead Block Prediction Potential:\n{prediction_potential:.1f}% of all L2 cache evictions',
                xy=(0, 0),
                xytext=(0, 0),
                ha='center',
                va='center',
                fontsize=14,
                fontweight='bold')
    
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'l2_prediction_potential.png'), dpi=300)
    plt.close()

def create_comprehensive_visualization(l1_dist, l2_dist, l1_analysis, l2_analysis, output_dir):
    """
    Create a comprehensive visualization of cache eviction patterns.
    
    Args:
        l1_dist: L1 cache access distribution
        l2_dist: L2 cache access distribution
        l1_analysis: L1 cache analysis
        l2_analysis: L2 cache analysis
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(18, 12))
    
    # Set up 2x2 grid
    gs = plt.GridSpec(2, 2, height_ratios=[1, 1], width_ratios=[1.5, 1])
    
    # 1. Top left: L2 Access Distribution (Bar Chart)
    ax1 = plt.subplot(gs[0, 0])
    l2_high_access_key = l2_dist['high_access_key']
    categories = [cat for cat in l2_dist['categories'] if cat != l2_high_access_key]
    values = [l2_dist['percentages'][cat] for cat in categories]
    
    bars = ax1.bar(categories, values, color='#3182bd', alpha=0.8)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        if height > 2.0:  # Only add labels for significant bars
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom')
    
    ax1.set_title('L2 Cache Access Distribution', fontsize=14)
    ax1.set_xlabel('Number of Accesses Before Eviction')
    ax1.set_ylabel('Percentage of Evictions (%)')
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_xticklabels(categories, rotation=45)
    
    # 2. Top right: Dead Block Prediction Potential (Pie Chart)
    ax2 = plt.subplot(gs[0, 1])
    
    # Define categories and colors for pie chart
    pie_categories = ['Dead Blocks\n(0 accesses)', 'One Access\nBlocks', 'Multi-Access\nBlocks']
    pie_values = [
        l2_analysis['avg_dead_blocks_percent'],
        l2_analysis['avg_one_access_blocks_percent'],
        100 - l2_analysis['avg_dead_blocks_percent'] - l2_analysis['avg_one_access_blocks_percent']
    ]
    pie_colors = ['#e41a1c', '#377eb8', '#4daf4a']
    
    # Create the pie chart
    patches, texts, autotexts = ax2.pie(
        pie_values, 
        labels=pie_categories,
        colors=pie_colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.85
    )
    
    # Enhance the text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(10)
    
    ax2.set_title('L2 Cache Block Access Distribution', fontsize=14)
    
    # Add a center circle to make it a donut chart
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    ax2.add_artist(centre_circle)
    
    # Add annotation about prediction potential
    prediction_potential = pie_values[0] + pie_values[1]
    ax2.annotate(f'Prediction Potential: {prediction_potential:.1f}%',
                xy=(0, 0),
                xytext=(0, 0),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold')
    
    # 3. Bottom left: Cumulative Distribution (Line Chart)
    ax3 = plt.subplot(gs[1, 0])
    
    # Use a common set of categories that exist in both distributions
    l1_high_access_key = l1_dist['high_access_key']
    l2_high_access_key = l2_dist['high_access_key']
    
    # Get the common categories in the correct order
    standard_categories = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
        '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100'
    ]
    
    # Filter to only include categories that exist in both distributions
    common_categories = [cat for cat in standard_categories if cat in l1_dist['percentages'] and cat in l2_dist['percentages']]
    
    # Calculate cumulative percentages
    l1_cumulative = []
    l2_cumulative = []
    
    l1_cum_sum = 0
    l2_cum_sum = 0
    
    for cat in common_categories:
        l1_cum_sum += l1_dist['percentages'][cat]
        l2_cum_sum += l2_dist['percentages'][cat]
        
        l1_cumulative.append(l1_cum_sum)
        l2_cumulative.append(l2_cum_sum)
    
    ax3.plot(range(len(common_categories)), l1_cumulative, 'o-', color='#de2d26', label='L1 Cache')
    ax3.plot(range(len(common_categories)), l2_cumulative, 'o-', color='#3182bd', label='L2 Cache')
    
    ax3.set_title('Cumulative Distribution of Block Accesses', fontsize=14)
    ax3.set_xlabel('Number of Accesses')
    ax3.set_ylabel('Cumulative Percentage (%)')
    ax3.set_xticks(range(len(common_categories)))
    ax3.set_xticklabels(common_categories, rotation=45)
    ax3.grid(alpha=0.3)
    ax3.legend()
    
    # 4. Bottom right: L1 vs L2 Dead Block Comparison (Bar Chart)
    ax4 = plt.subplot(gs[1, 1])
    
    # Focus on just the first few categories
    focus_categories = ['0', '1', '2', '3', '4', '5']
    # Filter to only include categories that exist in both distributions
    focus_categories = [cat for cat in focus_categories if cat in l1_dist['percentages'] and cat in l2_dist['percentages']]
    
    l1_values = [l1_dist['percentages'][cat] for cat in focus_categories]
    l2_values = [l2_dist['percentages'][cat] for cat in focus_categories]
    
    x = np.arange(len(focus_categories))
    width = 0.35
    
    ax4.bar(x - width/2, l2_values, width, label='L2 Cache', color='#3182bd')
    ax4.bar(x + width/2, l1_values, width, label='L1 Cache', color='#de2d26')
    
    ax4.set_title('Low Access Count Comparison', fontsize=14)
    ax4.set_xlabel('Number of Accesses')
    ax4.set_ylabel('Percentage (%)')
    ax4.set_xticks(x)
    ax4.set_xticklabels(focus_categories)
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'comprehensive_cache_analysis.png'), dpi=300)
    plt.close()

def create_markdown_report(analysis_results, output_dir):
    """
    Create a markdown report summarizing the analysis results.
    
    Args:
        analysis_results: Dictionary with analysis results
        output_dir: Directory to save the report
    """
    # Check what cache types we have data for
    available_caches = [cache_type for cache_type in ['L1', 'L2'] if cache_type in analysis_results]
    
    if not available_caches:
        print("No cache data available for report generation")
        return
    
    report = "# Cache Eviction Analysis Report\n\n"
    
    # Overall Summary
    report += "## Overall Summary\n\n"
    
    # Include L2 cache data if available
    if 'L2' in available_caches:
        l2_analysis = analysis_results['L2']['analysis']
        l2_prediction_potential = l2_analysis['avg_dead_blocks_percent'] + l2_analysis['avg_one_access_blocks_percent']
        
        report += f"- **L2 Cache Dead Block Prediction Potential:** {l2_prediction_potential:.2f}%\n"
        report += f"- **L2 Dead Blocks (0 accesses):** {l2_analysis['avg_dead_blocks_percent']:.2f}%\n"
        report += f"- **L2 One-Access Blocks:** {l2_analysis['avg_one_access_blocks_percent']:.2f}%\n"
        report += f"- **Average L2 Cache Evictions:** {l2_analysis['avg_total_evictions']:.0f}\n\n"
    
    # Include L1 cache data if available
    if 'L1' in available_caches:
        l1_analysis = analysis_results['L1']['analysis']
        l1_high_access_key = l1_analysis['high_access_key']
        
        report += f"- **L1 Cache High-Access Blocks ({l1_high_access_key}):** {l1_analysis['avg_high_access_blocks_percent']:.2f}%\n"
        report += f"- **Average L1 Cache Evictions:** {l1_analysis['avg_total_evictions']:.0f}\n\n"
    
    # L2 Cache Analysis
    if 'L2' in available_caches:
        report += "## L2 Cache Analysis\n\n"
        report += "The L2 cache shows significant potential for dead block prediction:\n\n"
        report += f"- {l2_analysis['avg_dead_blocks_percent']:.2f}% of evicted blocks received **zero accesses** before eviction\n"
        report += f"- {l2_analysis['avg_one_access_blocks_percent']:.2f}% of evicted blocks received **only one access** before eviction\n"
        report += f"- This means {l2_prediction_potential:.2f}% of all L2 cache evictions could potentially benefit from dead block prediction\n\n"
    
    # L1 Cache Analysis
    if 'L1' in available_caches:
        report += "## L1 Cache Analysis\n\n"
        report += "The L1 cache shows different access patterns compared to L2:\n\n"
        report += f"- {l1_analysis['avg_high_access_blocks_percent']:.2f}% of evicted blocks received **{l1_high_access_key} accesses** before eviction\n"
        report += f"- Only {l1_analysis['avg_dead_blocks_percent']:.2f}% of evicted blocks received zero accesses\n"
        report += f"- And only {l1_analysis['avg_one_access_blocks_percent']:.2f}% received just one access\n\n"
    
    # L1 vs L2 Comparison
    if 'L1' in available_caches and 'L2' in available_caches:
        report += "## L1 Cache vs. L2 Cache Comparison\n\n"
        report += "The access patterns between L1 and L2 caches show significant differences:\n\n"
        
        l1_high_access_key = l1_analysis['high_access_key']
        l2_high_access_key = l2_analysis['high_access_key']
        
        report += f"- **L1 Cache High-Access Blocks ({l1_high_access_key}):** {l1_analysis['avg_high_access_blocks_percent']:.2f}%\n"
        report += f"- **L2 Cache High-Access Blocks ({l2_high_access_key}):** {l2_analysis['avg_high_access_blocks_percent']:.2f}%\n\n"
        
        report += "This indicates that L1 cache blocks are heavily reused, while L2 cache blocks often see very few accesses before eviction.\n\n"
    
    # Access Distribution Analysis
    report += "## Access Count Distribution\n\n"
    
    if 'L1' in available_caches and 'L2' in available_caches:
        l1_dist = analysis_results['L1']['distribution']
        l2_dist = analysis_results['L2']['distribution']
        
        report += "The distribution of access counts before eviction:\n\n"
        
        report += "| Access Count | L2 Cache (%) | L1 Cache (%) |\n"
        report += "|--------------|--------------|-------------|\n"
        
        # Get a list of all basic categories that exist in either distribution
        standard_categories = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
            '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100'
        ]
        
        # Determine the high access keys
        l1_high_access_key = l1_dist['high_access_key']
        l2_high_access_key = l2_dist['high_access_key']
        
        for cat in standard_categories:
            l2_pct = l2_dist['percentages'].get(cat, 0)
            l1_pct = l1_dist['percentages'].get(cat, 0)
            
            report += f"| {cat} | {l2_pct:.2f}% | {l1_pct:.2f}% |\n"
        
        # Add high access keys separately if they differ
        if l1_high_access_key != l2_high_access_key:
            l2_high_pct = l2_dist['percentages'].get(l2_high_access_key, 0)
            l1_high_pct = l1_dist['percentages'].get(l1_high_access_key, 0)
            
            report += f"| {l2_high_access_key} | {l2_high_pct:.2f}% | - |\n"
            report += f"| {l1_high_access_key} | - | {l1_high_pct:.2f}% |\n"
        else:
            # If they're the same, add just one row
            high_pct_l2 = l2_dist['percentages'].get(l2_high_access_key, 0)
            high_pct_l1 = l1_dist['percentages'].get(l1_high_access_key, 0)
            report += f"| {l1_high_access_key} | {high_pct_l2:.2f}% | {high_pct_l1:.2f}% |\n"
            
    elif 'L2' in available_caches:
        l2_dist = analysis_results['L2']['distribution']
        l2_high_access_key = l2_dist['high_access_key']
        
        report += "The distribution of access counts before eviction for L2 cache:\n\n"
        
        report += "| Access Count | L2 Cache (%) |\n"
        report += "|--------------|-------------|\n"
        
        # All categories for L2
        for cat in l2_dist['categories']:
            l2_pct = l2_dist['percentages'][cat]
            report += f"| {cat} | {l2_pct:.2f}% |\n"
    
    report += "\n"
    
    # Recommendations for Dead Block Predictor
    report += "## Recommendations for Dead Block Predictor\n\n"
    
    report += "Based on the analysis of cache eviction patterns, here are recommendations for developing an effective dead block predictor:\n\n"
    
    if 'L2' in available_caches:
        l2_prediction_potential = l2_analysis['avg_dead_blocks_percent'] + l2_analysis['avg_one_access_blocks_percent']
        report += f"1. **Focus on Zero and One-Access Blocks:** The data shows that ~{l2_prediction_potential:.0f}% of L2 cache blocks are evicted with 0 or 1 accesses. These are prime candidates for prediction and early eviction.\n\n"
    
    if 'L1' in available_caches and 'L2' in available_caches:
        report += "2. **Apply Different Strategies for L1 and L2 Caches:** The significant difference in access patterns between L1 and L2 caches suggests that different prediction strategies are needed for each level.\n\n"
    
    report += "3. **Implement Access-Based Prediction:** Since the vast majority of L2 blocks see very few accesses, a predictor based on first-access patterns could be highly effective.\n\n"
    
    report += "4. **Exploit Temporal Locality:** Consider using the time between accesses as a predictive feature, as blocks with long gaps between first and second access may indicate low utility.\n\n"
    
    report += "5. **Program Counter Signatures:** Correlate block access patterns with the program counters of the instructions that access them to identify code patterns that lead to dead blocks.\n\n"
    
    # Conclusion
    report += "## Conclusion\n\n"
    
    if 'L2' in available_caches:
        report += f"The analysis reveals significant potential for dead block prediction in the L2 cache, with {l2_prediction_potential:.2f}% of blocks "
        report += "receiving at most one access before eviction. This suggests that an effective dead block predictor could substantially "
        report += "improve cache efficiency by identifying and evicting these low-utility blocks early."
    else:
        report += "The analysis provides insights into cache access patterns that can be leveraged to design an effective dead block predictor. "
        report += "By identifying blocks with low utility early in their cache residency, cache efficiency can be substantially improved."
    
    # Write report to file
    report_path = os.path.join(output_dir, 'cache_analysis_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Analysis report saved to {report_path}")
    
    # Save the analysis results as JSON for potential later use
    json_path = os.path.join(output_dir, 'cache_analysis_data.json')
    
    # Create a simplified version of the results for JSON serialization
    json_results = {}
    for cache_type in available_caches:
        json_results[cache_type] = {
            'analysis': {k: float(v) if isinstance(v, np.float64) else v for k, v in analysis_results[cache_type]['analysis'].items() if not isinstance(v, np.ndarray)},
            'distribution': {
                'percentages': {k: float(v) for k, v in analysis_results[cache_type]['distribution']['percentages'].items()},
                'total': int(analysis_results[cache_type]['distribution']['total']),
                'high_access_key': analysis_results[cache_type]['distribution']['high_access_key']
            }
        }
    
    with open(json_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"Analysis data saved to {json_path}")

def main():
    parser = argparse.ArgumentParser(description='Analyze cache eviction patterns from log files')
    parser.add_argument('--log_file', type=str, required=True, help='Path to the log file with cache histogram data')
    parser.add_argument('--output_dir', type=str, default='cache_analysis_output', help='Directory to save analysis results')
    
    args = parser.parse_args()
    
    # Parse the log file
    cache_data = parse_log_file(args.log_file)
    
    if not cache_data:
        print("Failed to parse log file")
        return
    
    # Analyze the cache data
    analysis_results = analyze_cache_data(cache_data)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Generate visualizations
    generate_visualizations(analysis_results, args.output_dir)
    
    # Create markdown report
    create_markdown_report(analysis_results, args.output_dir)
    
    print(f"Analysis complete. Results saved to {args.output_dir}")

if __name__ == "__main__":
    main()