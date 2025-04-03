#!/usr/bin/python3

configs = ['normal', 'prefetcher']
prefetcher_values = [2, 4, 8, 10, 12, 16]

benchmarks = [
    'bfs',
    'bitonicsort',
    'conv2d',
    'fir',
    'matrixmultiplication',
    'simpleconvolution',
    'stencil2d',
]

# Parameters from the image
benchmark_params = {
    'bitonicsort': '-length=1048576',
    'bfs': '-node=131072',
    'conv2d': '-W=1024 -H=1024',  # Using C2D params for conv2d
    'fir': '-length=19824640',
    'matrixmultiplication': '-x=2048 -y=2048 -z=1024',  # Using MM params
    'simpleconvolution': '-width=4096 -height=4096',  # Using SC params
    'stencil2d': '-row=2048 -col=2048 -iter=10',  # Using ST params
}

# Normal config
for benchmark in benchmarks:
    print('normal', benchmark)
    submit_file_name = 'normal/' + benchmark + ".sh"
    submit_file = open(submit_file_name, "w")
    submit_file.write("#!/bin/bash\n")
    submit_file.write(f"cd {benchmark}\n")
    submit_file.write(f'echo normal >> timing_report.txt\n')
    submit_file.write("{ time ")
    submit_file.write("./" + benchmark + " ")
    submit_file.write("-timing ")
    submit_file.write("-report-all ")
    # submit_file.write("-unified-gpus=1,2,3,4 ")
    
    # Add benchmark specific parameters
    if benchmark in benchmark_params:
        submit_file.write(benchmark_params[benchmark] + " ")
        
    submit_file.write(";} >>log.txt 2>> timing_report.txt\n")
    submit_file.close()

# Prefetcher config with multiple values
for benchmark in benchmarks:
    print('prefetcher', benchmark)
    submit_file_name = 'prefetcher/' + benchmark + ".sh"
    submit_file = open(submit_file_name, "w")
    submit_file.write("#!/bin/bash\n")
    submit_file.write(f"cd {benchmark}\n")
    
    # Create separate command for each prefetcher value
    for pvalue in prefetcher_values:
        metric_name = str(pvalue)
        submit_file.write(f'echo "prefetcher-{pvalue}" >> timing_report_{pvalue}.txt\n')
        submit_file.write("{ time ")
        submit_file.write("./" + benchmark + " ")
        submit_file.write("-timing ")
        submit_file.write("-report-all ")
        submit_file.write(f"-l1-prefetcher={pvalue} ")
        submit_file.write(f"-metric-file-name={metric_name} ")
        # submit_file.write("-unified-gpus=1,2,3,4 ")
        
        # Add benchmark specific parameters
        if benchmark in benchmark_params:
            submit_file.write(benchmark_params[benchmark] + " ")
            
        submit_file.write(f";}} >>log_{pvalue}.txt 2>> timing_report_{pvalue}.txt\n")
    
    submit_file.close()
