import re
import os
import matplotlib.pyplot as plt
import numpy as np
import argparse

def parse_histogram_data(file_path):
    """Parse histogram data from text file with Go map structures."""
    combined_data = {}
    total_entries = 0
    
    with open(file_path, 'r') as file:
        for line in file:
            # Extract AccessHistogram data
            match = re.search(r'AccessHistogram:map\[(.*?)\]', line)
            if match:
                histogram_part = match.group(1)
                # Split by space to get key-value pairs
                pairs = histogram_part.split(' ')
                
                for pair in pairs:
                    if ':' in pair:
                        key, value = pair.split(':')
                        # Convert value to int
                        value = int(value)
                        
                        # Add to combined data
                        if key not in combined_data:
                            combined_data[key] = 0
                        combined_data[key] += value
                        total_entries += value
    
    return combined_data, total_entries

def create_histogram(data, output_path, graph_name=None, show_plot=True, exclude_zero=False):
    """Create histogram visualization from data."""
    # Order keys
    ordered_keys = sorted(data.keys(), key=lambda k: 
                          float('inf') if k == '>100' else 
                          int(k.split('-')[0]) if '-' in k else int(k))
    
    # Filter data if needed
    if exclude_zero and '0' in ordered_keys:
        zero_count = data['0']
        ordered_keys.remove('0')
        filtered_data = {k: data[k] for k in ordered_keys}
    else:
        zero_count = data.get('0', 0)
        filtered_data = data
    
    # Prepare plot data
    categories = ordered_keys
    counts = [filtered_data[k] for k in ordered_keys]
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bar chart
    bars = ax.bar(categories, counts, color='#8884d8')
    
    # Add labels and title
    ax.set_xlabel('Access Category')
    ax.set_ylabel('Count')
    title = 'Combined Access Histogram'
    if graph_name:
        title = f"{graph_name} - {title}"
    if exclude_zero:
        title += ' (Excluding "0" category)'
    ax.set_title(title)
    
    # Add values on top of bars for significant values
    for bar in bars:
        height = bar.get_height()
        if height > max(counts) * 0.01:  # Only show labels for significant values
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height):,}',
                    ha='center', va='bottom', rotation=0)
    
    # Use log scale if including "0" category (which typically dominates)
    if not exclude_zero and zero_count > sum(counts) * 0.5:
        ax.set_yscale('log')
        plt.figtext(0.5, 0.01, "Using logarithmic scale due to large value differences", 
                    ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2})
    
    # Add summary statistics as text
    total = sum(counts) + (zero_count if exclude_zero else 0)
    summary = f"Total entries: {total:,}\n"
    
    if exclude_zero:
        summary += f"Category '0' (excluded): {zero_count:,} entries\n"
    else:
        summary += f"Category '0': {zero_count:,} entries\n"
    
    # Find second largest category
    if len(counts) > 1:
        second_largest_idx = np.argmax(counts)
        second_largest_key = categories[second_largest_idx]
        second_largest_val = counts[second_largest_idx]
        summary += f"Category '{second_largest_key}': {second_largest_val:,} entries"
    
    plt.figtext(0.15, 0.01, summary, ha="left", fontsize=10, 
                bbox={"facecolor":"lightgray", "alpha":0.5})
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    # Save the figure
    plt.savefig(output_path)
    print(f"Histogram saved to {output_path}")
    
    # Show the plot if requested
    if show_plot:
        plt.show()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate histogram from access data files')
    parser.add_argument('input_file', help='Input text file with access data')
    parser.add_argument('--output', '-o', default='access_histogram.png', 
                        help='Output image file path (default: access_histogram.png)')
    parser.add_argument('--exclude-zero', '-e', action='store_true',
                        help='Exclude category "0" from visualization')
    parser.add_argument('--no-display', '-n', action='store_true',
                        help='Do not display the plot (just save file)')
    
    args = parser.parse_args()
    
    # Extract folder name as graph name
    graph_name = None
    input_path = os.path.abspath(args.input_file)
    folder_name = os.path.basename(os.path.dirname(input_path))
    if folder_name:
        graph_name = folder_name
    
    # Parse data
    data, total = parse_histogram_data(args.input_file)
    
    # Print summary
    print(f"Parsed {total:,} total entries across {len(data)} categories")
    if graph_name:
        print(f"Using graph name from folder: {graph_name}")
    
    # Create visualization
    create_histogram(
        data, 
        args.output,
        graph_name=graph_name,
        show_plot=not args.no_display,
        exclude_zero=args.exclude_zero
    )

if __name__ == "__main__":
    main()
