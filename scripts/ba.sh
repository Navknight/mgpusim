#!/bin/bash

python block_access_histogram.py ./normal/pagerank/log.txt --output pagerank.png
python block_access_histogram.py ./normal/bitonicsort/log.txt --output bitonicsort.png
python block_access_histogram.py ./normal/fir/log.txt --output fir.png
python block_access_histogram.py ./normal/floydwarshall/log.txt --output floydwarshall.png
python block_access_histogram.py ./normal/kmeans/log.txt --output kmeans.png
python block_access_histogram.py ./normal/matrixtranspose/log.txt --output matrixtranspose.png
python block_access_histogram.py ./normal/matrixmultiplication/log.txt --output matrixmultiplication.png
python block_access_histogram.py ./normal/simpleconvolution/log.txt --output simpleconvolution.png
python block_access_histogram.py ./normal/spmv/log.txt --output spmv.png
python block_access_histogram.py ./normal/stencil2d/log.txt --output stencil2d.png