#!/bin/bash

# Create the target directories
mkdir -p normal

# Define the benchmarks to copy
benchmarks=(
    "bfs"
    "bitonicsort"
    "conv2d"
    "fir"
    "matrixmultiplication"
    "simpleconvolution"
    "stencil2d"
)

# Source directory
source_dir="../samples"

echo "Copying benchmarks from $source_dir to normal/ and prefetcher/ directories..."

# Copy the specified folders to the 'normal' directory
for benchmark in "${benchmarks[@]}"; do
    if [ -d "$source_dir/$benchmark" ]; then
        echo "Copying $benchmark to normal/"
        cp -r "$source_dir/$benchmark" normal/

        # Verify the binary exists and make it executable
        if [ -f "$source_dir/$benchmark/$benchmark" ]; then
            chmod +x "normal/$benchmark/$benchmark"
            echo "  ✓ Binary found and made executable"
        else
            echo "  ✗ Binary not found in $source_dir/$benchmark"
        fi
    else
        echo "Warning: $source_dir/$benchmark does not exist."
    fi
done

echo "Copying complete."
