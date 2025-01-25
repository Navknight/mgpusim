#!/usr/bin/python3

configs = ['normal', 'prefetcher']

benchmarks = [
    # 'aes',
    # 'atax',
    # 'bfs',
    # 'bicg',
    'bitonicsort',
    # 'concurrentkernel',
    # 'concurrentworkload',
    # 'conv2d',
    # 'fastwalshtransform',
    # 'fft',
    'fir',
    'floydwarshall',
    # 'im2col',
    # 'kmeans',
    # 'lenet',
    'matrixmultiplication',
    'matrixtranspose',
    # 'memcopy',
    # 'minerva',
    # 'nbody',
    # 'nw',
    'pagerank',
    # 'relu',
    'simpleconvolution',
    # 'spmv',
    # 'stencil2d',
    # 'vgg16',
    # 'xor',
]

for config in configs:
    for benchmark in benchmarks:
        print(config, benchmark)
        submit_file_name = config + '/' + benchmark + ".sh"
        submit_file = open(submit_file_name, "w")
        submit_file.write("#!/bin/bash\n")
        submit_file.write(f"cd {benchmark}\n")
        # submit_file.write("cd " + benchmark + "\n")
        submit_file.write(f'echo {config} >> timing_report.txt\n')
        submit_file.write("{ time ")
        submit_file.write("./" + benchmark + " ")
        submit_file.write("-timing ")
        submit_file.write("-report-all ")

        if config == 'prefetcher':
            submit_file.write("-use-prefetcher ")

        # Set benchmark specific parameters
        if benchmark == 'aes':
            submit_file.write("-length=65536 -max-inst=100000")  # Similar scale to other benchmarks
        elif benchmark == 'atax':
            submit_file.write("-x=4096 -y=4096 ")
        elif benchmark == 'bfs':
            submit_file.write("-load-graph=./Slashdot0902.txt")  # Similar scale to pagerank
        elif benchmark == 'bicg':
            submit_file.write("-x=8192 -y=8192 ")
        elif benchmark == 'bitonicsort':
            submit_file.write("-length=524288 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
            # submit_file.write("-gpus=1,2,3,4 ")
        elif benchmark == 'concurrentkernel':
            submit_file.write(" ")  # Based on typical concurrent workload parameters
        elif benchmark == 'concurrentworkload':
            submit_file.write("-workload-size=8192 -num-workloads=32 ")  # Similar to other memory-intensive benchmarks
        elif benchmark == 'conv2d':
            submit_file.write("-N=1 -C=1 -H=8192 -W=8192")
        elif benchmark == 'fastwalshtransform':
            submit_file.write("-length=8388608 ")
        elif benchmark == 'fft':
            submit_file.write("-MB=8192 -passes=64 ")  # Similar to other transform benchmarks
        elif benchmark == 'fir':
            submit_file.write("-length=4194304 ")  # Added taps parameter for FIR filter
            submit_file.write("-unified-gpus=1,2,3,4 ")
        elif benchmark == 'floydwarshall':
            submit_file.write("-node=1024 -iter=32 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
        elif benchmark == 'im2col':
            submit_file.write("-N=32 -C=3 -H=1024 -W=1024")  # Similar to conv2d but smaller
        elif benchmark == 'kmeans':
            submit_file.write("-points=524288 -features=32 -clusters=20 ")
        elif benchmark == 'lenet':
            submit_file.write("-epoch=10 ")
            submit_file.write("-max-batch-per-epoch=10 ")
            submit_file.write("-enable-testing=true ")
        elif benchmark == 'matrixmultiplication':
            submit_file.write("-x=1024 -y=1024 -z=1024 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
            # submit_file.write("-gpus=1,2,3,4 ")
        elif benchmark == 'matrixtranspose':
            submit_file.write("-width=2048 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
            # submit_file.write("-gpus=1,2,3,4 ")
        elif benchmark == 'memcopy':
            submit_file.write("")  # Similar to fastwalshtransform
        elif benchmark == 'minerva':
            submit_file.write(
                "-epoch=10 -max-batch-per-epoch=5 -batch-size=128 -enable-testing=true -enable-verification=true ")
        elif benchmark == 'nbody':
            submit_file.write("-particles=2048 -iter=64 ")  # Added iterations similar to other benchmarks
        elif benchmark == 'nw':
            submit_file.write("-length=2048 ")
        elif benchmark == 'pagerank':
            submit_file.write("-node=8192 -sparsity=0.5 -iterations=1 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
        elif benchmark == 'relu':
            submit_file.write("-length=8192")  # Added batch-size similar to neural network benchmarks
        elif benchmark == 'simpleconvolution':
            submit_file.write("-width=1024 -height=1024 ")
            submit_file.write("-unified-gpus=1,2,3,4 ")
        elif benchmark == 'spmv':
            submit_file.write("-dim=2097152 -sparsity=0.00001 ")
        elif benchmark == 'stencil2d':
            submit_file.write("-row=2048 -col=2048 ")
        elif benchmark == 'vgg16':
            submit_file.write("-epoch=10 ")
            submit_file.write("-max-batch-per-epoch=20 ")
            submit_file.write("-batch-size=32 ")
            submit_file.write("-enable-testing=true ")
        elif benchmark == 'xor':
            submit_file.write("")  # Similar scale to other compute benchmarks

        submit_file.write(";} >>log.txt 2>> timing_report.txt")
        submit_file.close()  # Close the file after writing
