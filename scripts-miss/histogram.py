import re
import numpy as np
import matplotlib.pyplot as plt

def parse_cache_data(filename):
    """Parse the cache data from the given file into L1 and L2 cache data."""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Split content into L2 and L1 cache sections
    sections = re.split(r'L[12] Cache', content)
    
    # Remove empty sections and strip whitespace
    sections = [s.strip() for s in sections if s.strip()]
    
    # The first section after "L2 Cache" is L2 data
    l2_data = sections[0].strip().split('\n')
    l2_data = [line for line in l2_data if line.strip()]
    
    # The section after "L1 Cache" is L1 data
    l1_data = sections[1].strip().split('\n')
    l1_data = [line for line in l1_data if line.strip()]
    
    return l2_data, l1_data

def parse_histogram_data(line):
    """Parse a single line of cache data."""
    # Extract the AccessHistogram part
    hist_match = re.search(r'AccessHistogram:map\[(.*?)\]', line)
    if not hist_match:
        return None
    
    hist_str = hist_match.group(1)
    
    # Parse histogram entries
    hist_data = {}
    
    # Process special access counts like ranges and >100
    entries = re.findall(r'([^:]+):(\d+)', hist_str)
    for key, value in entries:
        hist_data[key.strip()] = int(value)  # Strip whitespace from keys
    
    # Also get total evictions
    total_match = re.search(r'TotalEvictions:(\d+)', line)
    if total_match:
        hist_data['TotalEvictions'] = int(total_match.group(1))
    
    return hist_data

def process_cache_data(cache_lines):
    """Process multiple lines of cache data and compute averages."""
    all_data = []
    
    for line in cache_lines:
        data = parse_histogram_data(line)
        if data:
            all_data.append(data)
    
    # Combine all histograms and calculate average
    combined = {}
    for data in all_data:
        for key, value in data.items():
            if key not in combined:
                combined[key] = []
            combined[key].append(value)
    
    # Calculate averages
    averages = {key: np.mean(values) for key, values in combined.items()}
    
    return averages

def create_histogram(l1_avg, l2_avg):
    """Create separate histograms for L1 and L2 cache access patterns."""
    # Set up category order for x-axis (need to handle special cases like ranges)
    categories = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                 '11-20', '21-30', '31-40', '41-50', '51-60', '61-70',
                 '71-80', '81-90', '91-100', '>100']
    
    # Filter and order the data
    l1_values = []
    l2_values = []
    for cat in categories:
        l1_values.append(l1_avg.get(cat, 0))
        l2_values.append(l2_avg.get(cat, 0))
    
    # Create L1 Cache histogram
    plt.figure(figsize=(10, 6))
    plt.bar(categories, l1_values, color='blue', alpha=0.7)
    plt.title('L1 Cache Access Histogram (Average)')
    plt.xlabel('Number of Accesses Before Eviction')
    plt.ylabel('Count')
    plt.yscale('log')  # Use log scale due to large range of values
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('l1_cache_histogram.png', dpi=300)
    plt.close()
    
    # Create L2 Cache histogram
    plt.figure(figsize=(10, 6))
    plt.bar(categories, l2_values, color='green', alpha=0.7)
    plt.title('L2 Cache Access Histogram (Average)')
    plt.xlabel('Number of Accesses Before Eviction')
    plt.ylabel('Count')
    plt.yscale('log')  # Use log scale due to large range of values
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('l2_cache_histogram.png', dpi=300)
    plt.close()
    
    # Create comparison plot
    plt.figure(figsize=(12, 7))
    
    x = np.arange(len(categories))
    width = 0.4
    
    plt.bar(x - width/2, l1_values, width, label='L1 Cache', color='blue', alpha=0.7)
    plt.bar(x + width/2, l2_values, width, label='L2 Cache', color='green', alpha=0.7)
    
    plt.title('L1 vs L2 Cache Access Histogram (Average)')
    plt.xlabel('Number of Accesses Before Eviction')
    plt.ylabel('Count (log scale)')
    plt.yscale('log')
    plt.xticks(x, categories, rotation=45)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('cache_comparison.png', dpi=300)
    plt.close()
    
    print("Plots saved as 'l1_cache_histogram.png', 'l2_cache_histogram.png', and 'cache_comparison.png'")

def main():
    # Specify your input file
    input_file = '/home/abhinav/btp/mgpusim/scripts-evict/normal/stencil2d/log.txt'  # Use local file name
    
    # Parse cache data
    l2_data, l1_data = parse_cache_data(input_file)
    
    print(f"Found {len(l2_data)} L2 cache entries and {len(l1_data)} L1 cache entries")
    
    # Process data to get averages
    l2_avg = process_cache_data(l2_data)
    l1_avg = process_cache_data(l1_data)
    
    # Print some statistics
    print("\nL2 Cache Average Statistics:")
    total_evictions = l2_avg.get('TotalEvictions', 0)
    print(f"Average total evictions: {total_evictions:.2f}")
    
    print("\nL1 Cache Average Statistics:")
    total_evictions = l1_avg.get('TotalEvictions', 0)
    print(f"Average total evictions: {total_evictions:.2f}")
    
    # Create histograms
    create_histogram(l1_avg, l2_avg)

if __name__ == "__main__":
    main()