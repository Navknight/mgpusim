#!/bin/bash

# List of all benchmarks
declare -a benchmarks=("bfs" "bitonicsort" "conv2d" "fir" "matrixmultiplication" "simpleconvolution" "stencil2d")
declare -A params=(
    ["bfs"]="-node=131072"
    ["bitonicsort"]="-length=1048576"
    ["conv2d"]="-W=1024 -H=1024"
    ["fir"]="-length=19824640"
    ["matrixmultiplication"]="-x=2048 -y=2048 -z=1024"
    ["simpleconvolution"]="-width=4096 -height=4096"
    ["stencil2d"]="-row=2048 -col=2048 -iter=10"
)

# Configuration
MAX_PARALLEL_JOBS=7  # Allow 5 jobs (about 50GB total)
MIN_FREE_MEM=5       # Ensure at least 5GB free before starting new job
MAX_RETRIES=3        # Maximum number of retries for failed benchmarks
LOG_FILE="benchmark_runs.log"

# Arrays to store failed jobs for retry
declare -a failed_jobs=()

# Function to get available memory in GB
get_free_memory() {
    free -g | awk '/^Mem:/ {print $7}'
}

# Function to count running background jobs
count_jobs() {
    jobs -p | wc -l
}

# Function to run a benchmark with error handling
run_benchmark() {
    local benchmark=$1
    local pvalue=$2  # will be "normal" or a number
    local retry_count=$3

    # Wait for resources
    while [[ $(count_jobs) -ge $MAX_PARALLEL_JOBS || $(get_free_memory) -lt $MIN_FREE_MEM ]]; do
        echo "Waiting for resources. Running jobs: $(count_jobs), Free memory: $(get_free_memory)GB"
        sleep 30
    done

    echo "Starting $benchmark $pvalue (attempt $retry_count)" | tee -a $LOG_FILE

    if [[ "$pvalue" == "normal" ]]; then
        (
            cd normal/$benchmark
            echo normal >> timing_report.txt
            { time ./$benchmark -timing -report-all ${params[$benchmark]}; } >>log.txt 2>> timing_report.txt
            exit_code=$?
            if [[ $exit_code -ne 0 ]]; then
                echo "FAILED: $benchmark $pvalue (exit code $exit_code)" | tee -a $LOG_FILE
                # Return failure info to parent process
                exit 1
            else
                echo "Completed $benchmark $pvalue at $(date)" | tee -a $LOG_FILE
                exit 0
            fi
        ) &

        # Store the PID and job info
        pid=$!
        job_info="$benchmark:$pvalue:$retry_count:$pid"
        wait $pid || failed_jobs+=("$job_info")

    else
        (
            cd normal/$benchmark
            echo "prefetcher-$pvalue" >> timing_report_$pvalue.txt
            { time ./$benchmark -timing -report-all -l1-prefetcher=$pvalue -metric-file-name=$pvalue ${params[$benchmark]}; } >>log_$pvalue.txt 2>> timing_report_$pvalue.txt
            exit_code=$?
            if [[ $exit_code -ne 0 ]]; then
                echo "FAILED: $benchmark prefetcher-$pvalue (exit code $exit_code)" | tee -a $LOG_FILE
                # Return failure info to parent process
                exit 1
            else
                echo "Completed $benchmark prefetcher-$pvalue at $(date)" | tee -a $LOG_FILE
                exit 0
            fi
        ) &

        # Store the PID and job info
        pid=$!
        job_info="$benchmark:$pvalue:$retry_count:$pid"
        wait $pid || failed_jobs+=("$job_info")
    fi
}

echo "Starting benchmark runs at $(date)" | tee -a $LOG_FILE

# Process all benchmarks
for benchmark in "${benchmarks[@]}"; do
    echo "Processing $benchmark" | tee -a $LOG_FILE

    # Run normal configuration
    run_benchmark "$benchmark" "normal" 1

    # Run all prefetcher configurations
    for pvalue in 1 2 4 8 16 32; do
        run_benchmark "$benchmark" "$pvalue" 1
    done
done

# Wait for all background jobs to finish
wait

# Process failed jobs
retry_count=2
while [[ ${#failed_jobs[@]} -gt 0 && $retry_count -le $MAX_RETRIES ]]; do
    echo "Retrying ${#failed_jobs[@]} failed jobs (attempt $retry_count)" | tee -a $LOG_FILE

    # Make a copy of failed jobs and reset the array
    failed_copy=("${failed_jobs[@]}")
    failed_jobs=()

    for job in "${failed_copy[@]}"; do
        IFS=':' read -r benchmark pvalue attempt pid <<< "$job"
        echo "Retrying $benchmark $pvalue (previous attempt $attempt failed)" | tee -a $LOG_FILE
        run_benchmark "$benchmark" "$pvalue" $retry_count
    done

    # Wait for retry jobs to finish
    wait

    # Increment retry counter
    ((retry_count++))
done

if [[ ${#failed_jobs[@]} -gt 0 ]]; then
    echo "WARNING: ${#failed_jobs[@]} jobs still failed after $MAX_RETRIES attempts:" | tee -a $LOG_FILE
    for job in "${failed_jobs[@]}"; do
        IFS=':' read -r benchmark pvalue attempt pid <<< "$job"
        echo "  - $benchmark $pvalue" | tee -a $LOG_FILE
    done
fi

echo "All benchmark runs completed at $(date)" | tee -a $LOG_FILE
