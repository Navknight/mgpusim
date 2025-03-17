#!/bin/bash
cd matrixmultiplication
echo normal >> timing_report.txt
{ time ./matrixmultiplication -timing -report-all -x=1024 -y=1024 -z=1024 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt