#!/bin/bash
# Example script showing how to use the cache eviction analysis tool

# Step 1: Create a directory for each benchmark's output
mkdir -p analysis_results

# Step 2: Run the analysis on log files from different benchmarks
# This assumes log files are named like 'log.txt' and located in normal/{benchmark}/ directories

# Find all benchmark directories
for benchmark_dir in normal/*/; do
    # Extract benchmark name from directory path
    benchmark=$(basename "$benchmark_dir")
    echo "Processing benchmark: $benchmark"
    
    # Check if log.txt exists in this benchmark directory
    if [ -f "$benchmark_dir/log.txt" ]; then
        # Create output directory for this benchmark
        mkdir -p "analysis_results/$benchmark"
        
        # Run the analysis script
        python compare.py \
            --log_file "$benchmark_dir/log.txt" \
            --output_dir "analysis_results/$benchmark"
        
        echo "Completed analysis for $benchmark"
    else
        echo "No log.txt found in $benchmark_dir, skipping"
    fi
done

echo "Analysis complete. Results are available in the analysis_results directory."

# Step 3: Compare results across benchmarks (optional)
# This requires installing the benchmark comparison tool
# python benchmark_comparison_script.py --input_dir analysis_results --output_file benchmark_comparison.png