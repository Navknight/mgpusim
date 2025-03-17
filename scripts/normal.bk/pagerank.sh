#!/bin/bash
cd pagerank
echo normal >> timing_report.txt
{ time ./pagerank -timing -report-all -node=8192 -sparsity=0.5 -iterations=1 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt