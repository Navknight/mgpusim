#!/bin/bash

# Configuration arrays
configs=("normal" "prefetcher")
benchmarks=(
  "bfs"
  "conv2d"
  "fir"
  "matrixmultiplication"
  "simpleconvolution"
  "stencil2d"
)

# Array to track which benchmarks have been started
declare -A benchmark_status

# Initialize benchmark status
for config in "${configs[@]}"; do
  for benchmark in "${benchmarks[@]}"; do
    key="${config}_${benchmark}"
    benchmark_status["$key"]=0 # 0 = not started, 1 = running or completed
  done
done

# Function to check available RAM in GB
check_ram() {
  free -g | awk '/^Mem:/{print $7}'
}

# Function to run a benchmark with logging
run_benchmark() {
  local config="$1"
  local benchmark="$2"
  
  # Mark this benchmark as started
  key="${config}_${benchmark}"
  benchmark_status["$key"]=1
  
  (
    echo "Starting benchmark: ${config}/${benchmark} at $(date)" >&2
    bash "${config}/${benchmark}.sh" >"${config}_${benchmark}.log" 2>&1
    echo "Finished benchmark: ${config}/${benchmark} at $(date)" >&2
  ) &
}

# Function to count running benchmarks
count_running_benchmarks() {
  jobs -r | wc -l
}

# Function to get next unstarted benchmark
get_next_benchmark() {
  for config in "${configs[@]}"; do
    for benchmark in "${benchmarks[@]}"; do
      key="${config}_${benchmark}"
      if [ "${benchmark_status[$key]}" -eq 0 ]; then
        echo "${config} ${benchmark}"
        return 0
      fi
    done
  done
  echo "" # Return empty string if no benchmarks are left
}

# Main loop to check RAM and schedule benchmarks
total_benchmarks=$((${#configs[@]} * ${#benchmarks[@]}))
scheduled_benchmarks=0

echo "Starting benchmark scheduler. Total benchmarks to run: $total_benchmarks"
echo "Running on 64GB machine. Will adjust concurrency accordingly."

while [ $scheduled_benchmarks -lt $total_benchmarks ]; do
  # Get available RAM and calculate how many benchmarks we can run
  available_ram=$(check_ram)
  echo "Available RAM: ${available_ram}GB"
  
  # Calculate number of benchmarks to run based on RAM (8GB per benchmark on a 64GB machine)
  num_benchmarks=$((available_ram / 8))
  
  # Cap at maximum 6 benchmarks, minimum 1
  if [ $num_benchmarks -gt 6 ]; then
    num_benchmarks=6
  elif [ $num_benchmarks -lt 1 ]; then
    num_benchmarks=1
  fi
  
  echo "Target number of concurrent benchmarks: $num_benchmarks"
  
  # Check current running benchmarks
  running_benchmarks=$(count_running_benchmarks)
  echo "Currently running benchmarks: $running_benchmarks"
  
  # Schedule new benchmarks if there's capacity
  while [ $running_benchmarks -lt $num_benchmarks ] && [ $scheduled_benchmarks -lt $total_benchmarks ]; do
    # Get next unstarted benchmark
    next_benchmark=$(get_next_benchmark)
    
    # If no more benchmarks to run, break
    if [ -z "$next_benchmark" ]; then
      break
    fi
    
    # Split the result into config and benchmark
    read -r config benchmark <<< "$next_benchmark"
    
    echo "Scheduling benchmark: ${config}/${benchmark}"
    run_benchmark "$config" "$benchmark"
    scheduled_benchmarks=$((scheduled_benchmarks + 1))
    running_benchmarks=$((running_benchmarks + 1))
    echo "Progress: $scheduled_benchmarks/$total_benchmarks benchmarks scheduled"
  done
  
  # If all benchmarks have been scheduled, break the loop
  if [ $scheduled_benchmarks -ge $total_benchmarks ]; then
    break
  fi
  
  # Wait before checking again
  echo "Waiting 30 seconds before next check..."
  sleep 30
done

# Wait for all remaining benchmarks to complete
echo "All benchmarks scheduled. Waiting for completion..."
wait
echo "All benchmarks completed at $(date)"

# Print summary of completed benchmarks
echo "Benchmark execution summary:"
for config in "${configs[@]}"; do
  for benchmark in "${benchmarks[@]}"; do
    if [ -f "${config}_${benchmark}.log" ]; then
      echo "✓ ${config}/${benchmark} completed"
    else
      echo "✗ ${config}/${benchmark} failed or did not run"
    fi
  done
done
