# Cache Block Access Histogram Generation
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# Read the CSV data
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'cache_block_access.csv')
df = pd.read_csv(csv_path)

# Extract cache information
cache_info = df.iloc[:len(df[~df['BinSize'].isna()])]

# Skip the blank line
current_line = len(cache_info) + 1

# Extract read access data
read_end = 0
for i in range(current_line, len(df)):
    if pd.isna(df.iloc[i, 0]):
        read_end = i
        break
if read_end == 0:
    read_end = len(df)

read_data = df.iloc[current_line:read_end].copy()
read_data.set_index('Cache', inplace=True)

# Move to write data (skip blank line)
current_line = read_end + 1

# Extract write access data
write_data = df.iloc[current_line:].copy()
write_data.set_index('Cache', inplace=True)

# Create figures for each cache
for cache_name in read_data.index:
    # Get cache info
    cache_row = cache_info[cache_info['Cache'] == cache_name]
    bin_size = int(cache_row['BinSize'].values[0])
    total_evictions = int(cache_row['TotalEvictions'].values[0])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Read access histogram
    read_counts = read_data.loc[cache_name].values
    x = np.arange(len(read_data.columns))
    ax1.bar(x, read_counts, width=0.7, color='skyblue', edgecolor='black')
    ax1.set_xticks(x)
    ax1.set_xticklabels([col.replace('Read ', '') for col in read_data.columns], rotation=45)
    ax1.set_title('Read Accesses Before Eviction')
    ax1.set_xlabel('Number of Read Accesses')
    ax1.set_ylabel('Number of Blocks')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    # Write access histogram
    write_counts = write_data.loc[cache_name].values
    x = np.arange(len(write_data.columns))
    ax2.bar(x, write_counts, width=0.7, color='lightgreen', edgecolor='black')
    ax2.set_xticks(x)
    ax2.set_xticklabels([col.replace('Write ', '') for col in write_data.columns], rotation=45)
    ax2.set_title('Write Accesses Before Eviction')
    ax2.set_xlabel('Number of Write Accesses')
    ax2.set_ylabel('Number of Blocks')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    # Add title with total evictions
    plt.suptitle(f'Cache Block Access Patterns for {cache_name}\\nTotal Evictions: {total_evictions:,}', fontsize=16)
    plt.tight_layout()
    plt.subplots_adjust(top=0.85)

    # Save figure
    fig_path = os.path.join(script_dir, f'{cache_name.replace("/", "_")}_block_access.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f'Generated {fig_path}')

    # Optional: close the figure to save memory
    plt.close(fig)

# Create combined figure for all caches
plt.figure(figsize=(12, 8))
bar_width = 0.8 / len(read_data.index)
positions = np.arange(len(read_data.columns))

for i, cache_name in enumerate(read_data.index):
    offset = (i - len(read_data.index)/2 + 0.5) * bar_width
    plt.bar(positions + offset, read_data.loc[cache_name].values,
            width=bar_width, label=cache_name, alpha=0.7)

plt.title('Read Accesses Before Eviction - All Caches')
plt.xlabel('Number of Read Accesses')
plt.ylabel('Number of Blocks')
plt.xticks(positions, [col.replace('Read ', '') for col in read_data.columns], rotation=45)
plt.legend(loc='best')
plt.grid(axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()

# Save combined figure
fig_path = os.path.join(script_dir, 'all_caches_read_access.png')
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
print(f'Generated {fig_path}')

# Create combined figure for write accesses
plt.figure(figsize=(12, 8))
for i, cache_name in enumerate(write_data.index):
    offset = (i - len(write_data.index)/2 + 0.5) * bar_width
    plt.bar(positions + offset, write_data.loc[cache_name].values,
            width=bar_width, label=cache_name, alpha=0.7)

plt.title('Write Accesses Before Eviction - All Caches')
plt.xlabel('Number of Write Accesses')
plt.ylabel('Number of Blocks')
plt.xticks(positions, [col.replace('Write ', '') for col in write_data.columns], rotation=45)
plt.legend(loc='best')
plt.grid(axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()

# Save combined figure
fig_path = os.path.join(script_dir, 'all_caches_write_access.png')
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
print(f'Generated {fig_path}')

print('All histograms generated successfully!')
