#!/bin/bash

# List of all benchmarks
declare -a benchmarks=( "bitonicsort" "conv2d" "fir" "stencil2d")
declare -A params=(
    #["bfs"]="-node=131072"
    ["bitonicsort"]="-length=1048576"
    ["conv2d"]="-W=1024 -H=1024"
    ["fir"]="-length=19824640"
    #["matrixmultiplication"]="-x=2048 -y=2048 -z=1024"
    #["simpleconvolution"]="-width=4096 -height=4096"
    ["stencil2d"]="-row=2048 -col=2048 -iter=10"
)

# Configuration
MAX_PARALLEL_JOBS=7  # Allow 5 jobs (about 50GB total)
MIN_FREE_MEM=5       # Ensure at least 5GB free before starting new job
MAX_RETRIES=3        # Maximum number of retries for failed benchmarks
LOG_FILE="benchmark_runs.log"

# Queue of jobs to run
declare -a job_queue=()
# Active jobs
declare -A active_jobs=()
# Failed jobs for retry
declare -a failed_jobs=()

# Function to get available memory in GB
get_free_memory() {
    free -g | awk '/^Mem:/ {print $7}'
}

# Function to count running jobs
count_active_jobs() {
    echo ${#active_jobs[@]}
}

# Function to execute a benchmark
execute_benchmark() {
    local benchmark=$1
    local pvalue=$2
    local retry_count=$3
    local job_id="$benchmark:$pvalue:$retry_count"

    if [[ "$pvalue" == "normal" ]]; then
        cd normal/$benchmark
        echo normal >> timing_report.txt
        { time ./$benchmark -timing -report-all ${params[$benchmark]}; } >>log.txt 2>> timing_report.txt
        local exit_code=$?
    else
        cd normal/$benchmark
        echo "prefetcher-$pvalue" >> timing_report_$pvalue.txt
        { time ./$benchmark -timing -report-all -l1-prefetcher=$pvalue -metric-file-name=$pvalue ${params[$benchmark]}; } >>log_$pvalue.txt 2>> timing_report_$pvalue.txt
        local exit_code=$?
    fi

    # Return to original directory
    cd - > /dev/null

    # Return success/failure
    return $exit_code
}

# Function to check and update job status
check_job_status() {
    local jobs_to_remove=()

    for job_id in "${!active_jobs[@]}"; do
        local pid=${active_jobs[$job_id]}

        # Check if job is still running
        if ! ps -p $pid > /dev/null; then
            # Job completed, check exit status
            wait $pid
            local exit_code=$?

            if [[ $exit_code -eq 0 ]]; then
                echo "COMPLETED: $job_id (PID: $pid)" | tee -a $LOG_FILE
            else
                echo "FAILED: $job_id (PID: $pid) with exit code $exit_code" | tee -a $LOG_FILE
                # Parse job info for retry
                IFS=':' read -r benchmark pvalue retry_count <<< "$job_id"
                if [[ $retry_count -lt $MAX_RETRIES ]]; then
                    # Increment retry count
                    retry_count=$((retry_count + 1))
                    failed_jobs+=("$benchmark:$pvalue:$retry_count")
                else
                    echo "Maximum retries reached for $job_id. Giving up." | tee -a $LOG_FILE
                fi
            fi

            # Mark this job for removal from active jobs
            jobs_to_remove+=("$job_id")
        fi
    done

    # Remove completed jobs from active_jobs
    for job_id in "${jobs_to_remove[@]}"; do
        unset active_jobs[$job_id]
    done
}

# Function to start new jobs if resources permit
start_jobs() {
    # First check for completed jobs and update status
    check_job_status

    # While we have capacity and jobs in queue
    while [[ $(count_active_jobs) -lt $MAX_PARALLEL_JOBS &&
              $(get_free_memory) -ge $MIN_FREE_MEM &&
              ${#job_queue[@]} -gt 0 ]]; do

        # Get next job
        local job_info=${job_queue[0]}
        job_queue=("${job_queue[@]:1}") # Remove first element

        IFS=':' read -r benchmark pvalue retry_count <<< "$job_info"
        local job_id="$benchmark:$pvalue:$retry_count"

        echo "Starting $job_id" | tee -a $LOG_FILE

        # Start job in background
        (execute_benchmark "$benchmark" "$pvalue" "$retry_count"; exit $?) &
        local pid=$!

        # Add to active jobs
        active_jobs[$job_id]=$pid

        # Sleep briefly to allow process to start and memory to allocate
        sleep 2
    done
}

# Initialize the job queue
echo "Initializing job queue at $(date)" | tee -a $LOG_FILE

# Add all normal jobs
for benchmark in "${benchmarks[@]}"; do
    job_queue+=("$benchmark:normal:1")
done

# Add all prefetcher jobs
for benchmark in "${benchmarks[@]}"; do
    for pvalue in 1 2 4 8 16 32; do
        job_queue+=("$benchmark:$pvalue:1")
    done
done

echo "Starting benchmark runs at $(date) - ${#job_queue[@]} jobs queued" | tee -a $LOG_FILE

# Process jobs until queue is empty and no active jobs
while [[ ${#job_queue[@]} -gt 0 || $(count_active_jobs) -gt 0 ]]; do
    start_jobs

    # If we can't start more jobs now, wait a bit
    if [[ $(count_active_jobs) -ge $MAX_PARALLEL_JOBS ||
          $(get_free_memory) -lt $MIN_FREE_MEM ]]; then
        echo "Resources limited. Running jobs: $(count_active_jobs), Free memory: $(get_free_memory)GB" | tee -a $LOG_FILE
        sleep 30
    fi
done

# Process any failed jobs
while [[ ${#failed_jobs[@]} -gt 0 ]]; do
    echo "Processing ${#failed_jobs[@]} failed jobs" | tee -a $LOG_FILE

    # Move failed jobs to queue
    job_queue=("${failed_jobs[@]}")
    failed_jobs=()

    # Process retry queue
    while [[ ${#job_queue[@]} -gt 0 || $(count_active_jobs) -gt 0 ]]; do
        start_jobs

        if [[ $(count_active_jobs) -ge $MAX_PARALLEL_JOBS ||
              $(get_free_memory) -lt $MIN_FREE_MEM ]]; then
            sleep 30
        fi
    done
done

echo "All benchmark runs completed at $(date)" | tee -a $LOG_FILE
