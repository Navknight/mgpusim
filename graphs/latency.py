#!/usr/bin/env python3
"""
This script creates a publication-quality black and white stacked bar chart
showing MSHR hits comparison (Normal vs Prefetch) for all benchmarks.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

# Set up the plotting style for publication quality B&W
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
rcParams['font.size'] = 14
rcParams['axes.labelsize'] = 14
rcParams['axes.titlesize'] = 16
rcParams['xtick.labelsize'] = 12
rcParams['ytick.labelsize'] = 12
rcParams['legend.fontsize'] = 12
rcParams['figure.titlesize'] = 16
rcParams['figure.dpi'] = 200
rcParams['savefig.dpi'] = 400
rcParams['axes.linewidth'] = 2.0
rcParams['lines.linewidth'] = 3.0
rcParams['patch.linewidth'] = 2.5
rcParams['image.cmap'] = 'gray'

def create_mshr_hits_chart(output_file='mshr_hits_comparison_bw.png'):
    """
    Create a publication-quality black and white stacked bar chart 
    showing MSHR hits comparison between Normal and Prefetch for all benchmarks.
    """
    # Data extracted from the image
    benchmarks = ['pagerank', 'floydwarshall', 'fir', 'simpleconvolution']
    
    # Data values as percentages
    normal_hits = [8.8, 49.0, 16.0, 15.1]
    prefetch_hits = [91.2, 51.0, 84.0, 84.9]
    
    # Convert to proportions for stacking
    normal_props = [n/100 for n in normal_hits]
    prefetch_props = [p/100 for p in prefetch_hits]
    
    # Calculate the width needed based on the number of benchmarks
    fig_width = max(10, len(benchmarks) * 2.2)
    plt.figure(figsize=(fig_width, 7))
    
    # Create the stacked percentage bar chart
    x = np.arange(len(benchmarks))
    bar_width = 0.7
    
    # First segment: Normal hits (bottom)
    normal_bars = plt.bar(x, normal_props, bar_width,
                        label='Normal', 
                        color='white', edgecolor='black', hatch='////', linewidth=1.5)
    
    # Second segment: Prefetch hits (top)
    prefetch_bars = plt.bar(x, prefetch_props, bar_width,
                          bottom=normal_props, label='Prefetch',
                          color='white', edgecolor='black', hatch='xxxx', linewidth=1.5)
    
    # Add percentage labels inside each segment
    for i, bar in enumerate(normal_bars):
        height = bar.get_height()
        if height > 0.05:  # Only label segments that are large enough
            plt.text(bar.get_x() + bar.get_width()/2, height/2,
                   f'{normal_hits[i]:.1f}%', ha='center', va='center',
                   fontsize=11, fontweight='bold', color='black')
    
    for i, bar in enumerate(prefetch_bars):
        height = bar.get_height()
        if height > 0.05:  # Only label segments that are large enough
            plt.text(bar.get_x() + bar.get_width()/2, normal_props[i] + height/2,
                   f'{prefetch_hits[i]:.1f}%', ha='center', va='center',
                   fontsize=11, fontweight='bold', color='black')
    
    # Configure the plot styling
    plt.title('MSHR Hits Comparison for All Benchmarks', fontsize=16, fontweight='bold')
    plt.xlabel('Benchmarks', fontsize=14, fontweight='bold')
    plt.ylabel('Percentage (%)', fontsize=14, fontweight='bold')
    plt.xticks(x, benchmarks, rotation=0)
    
    # Set y-axis limit for percentage (0 to 100)
    plt.ylim(0, 1.0)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}'))
    
    # Add horizontal grid lines
    plt.grid(axis='y', alpha=0.5, linestyle='-', linewidth=0.8)
    
    # Position the legend for better readability
    plt.legend(loc='upper right', fontsize=12, frameon=True, framealpha=0.95,
              edgecolor='black')
    
    # Add horizontal lines for average values
    avg_normal = np.mean(normal_props)
    avg_prefetch = np.mean(prefetch_props)
    
    plt.axhline(y=avg_normal, color='black', linestyle='-', linewidth=1, alpha=0.5)
    plt.text(len(benchmarks)-0.5, avg_normal-0.03, f'Normal Avg: {avg_normal*100:.1f}%', 
            ha='right', va='top', fontsize=10, fontweight='bold')
    
    plt.axhline(y=avg_normal+avg_prefetch, color='black', linestyle='-', linewidth=1, alpha=0.5)
    
    # Ensure the border of the plot is visible
    plt.gca().spines['top'].set_visible(True)
    plt.gca().spines['right'].set_visible(True)
    plt.gca().spines['left'].set_visible(True)
    plt.gca().spines['bottom'].set_visible(True)
    
    # Minimize white space
    plt.tight_layout(pad=1.0)
    
    # Save the visualization
    plt.savefig(output_file, bbox_inches='tight', pad_inches=0.2)
    print(f"Saved MSHR hits comparison chart to {output_file}")
    
    # Close the figure to free memory
    plt.close()

if __name__ == "__main__":
    create_mshr_hits_chart()