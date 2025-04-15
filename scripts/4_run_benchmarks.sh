
#!/bin/bash
# Configuration arrays
configs=("prefetcher" "normal")
benchmarks=(
  "bfs"
  "bitonicsort"
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
    benchmark_status["$config/$benchmark"]=0 # 0 = not started, 1 = running or completed
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
  benchmark_status["$config/$benchmark"]=1
  (
    cd "$config" || exit 1
    echo "Starting benchmark: $config/$benchmark at $(date)" >&2
    bash "${benchmark}.sh" >"${benchmark}.log" 2>&1
    echo "Finished benchmark: $config/$benchmark at $(date)" >&2
  ) &
}
# Function to count running benchmarks
count_running_benchmarks() {
  jobs -r | wc -l
}
# Function to get next unstarted benchmark
get_next_benchmark() {
  local config="$1"
  for benchmark in "${benchmarks[@]}"; do
    if [ "${benchmark_status["$config/$benchmark"]}" -eq 0 ]; then
      echo "$benchmark"
      return 0
    fi
  done
  echo "" # Return empty string if no benchmarks are left
}
# Main loop to check RAM and schedule benchmarks
echo "Starting benchmark scheduler."
for config in "${configs[@]}"; do
  scheduled_benchmarks=0
  total_benchmarks=${#benchmarks[@]}
  echo "Running benchmarks for configuration: $config (Total: $total_benchmarks)"

  while [ $scheduled_benchmarks -lt $total_benchmarks ]; do
    available_ram=$(check_ram)
    echo "Available RAM: ${available_ram}GB"
    num_benchmarks=$((available_ram / 6))
    if [ $num_benchmarks -gt 3 ]; then
      num_benchmarks=3
    elif [ $num_benchmarks -lt 1 ]; then
      num_benchmarks=1
    fi
    echo "Target number of concurrent benchmarks: $num_benchmarks"

    running_benchmarks=$(count_running_benchmarks)
    echo "Currently running benchmarks: $running_benchmarks"

    while [ $running_benchmarks -lt $num_benchmarks ] && [ $scheduled_benchmarks -lt $total_benchmarks ]; do
      next_benchmark=$(get_next_benchmark "$config")
      if [ -z "$next_benchmark" ]; then
        break
      fi
      echo "Scheduling benchmark: $config/$next_benchmark"
      run_benchmark "$config" "$next_benchmark"
      scheduled_benchmarks=$((scheduled_benchmarks + 1))
      running_benchmarks=$((running_benchmarks + 1))
      echo "Progress: $scheduled_benchmarks/$total_benchmarks benchmarks scheduled"
    done

    if [ $scheduled_benchmarks -ge $total_benchmarks ]; then
      break
    fi
    echo "Waiting 10 seconds before next check..."
    sleep 10
  done
  wait
done

echo "All benchmarks completed at $(date)"
echo "Benchmark execution summary:"
for config in "${configs[@]}"; do
  for benchmark in "${benchmarks[@]}"; do
    log_file="${config}/${benchmark}.log"
    if [ -f "$log_file" ]; then
      echo "✓ $config/$benchmark completed"
    else
      echo "✗ $config/$benchmark failed or did not run"
    fi
  done
done
