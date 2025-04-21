#!/usr/bin/python3

configs = ['normal']
prefetcher_values = [1, 2, 4, 8, 16, 32]

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
    'conv2d': '-W=1024 -H=1024',
    'fir': '-length=19824640',
    'matrixmultiplication': '-x=2048 -y=2048 -z=1024',
    'simpleconvolution': '-width=4096 -height=4096',
    'stencil2d': '-row=2048 -col=2048 -iter=10',
}

# Combined loop for all configurations in the normal folder
for benchmark in benchmarks:
    print(benchmark)
    submit_file_name = 'normal/' + benchmark + ".sh"
    submit_file = open(submit_file_name, "w")
    submit_file.write("#!/bin/bash\n")
    submit_file.write(f"cd {benchmark}\n\n")

    # Normal configuration
    submit_file.write('echo normal >> timing_report.txt\n')
    submit_file.write("{ time ")
    submit_file.write("./" + benchmark + " ")
    submit_file.write("-timing ")
    submit_file.write("-report-all ")
    # submit_file.write("-unified-gpus=1,2,3,4 ")

    # Add benchmark specific parameters
    if benchmark in benchmark_params:
        submit_file.write(benchmark_params[benchmark] + " ")

    submit_file.write(";} >>log.txt 2>> timing_report.txt\n\n")

    # Prefetcher configurations with different values
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

        submit_file.write(f";}} >>log_{pvalue}.txt 2>> timing_report_{pvalue}.txt\n\n")

    submit_file.close()
