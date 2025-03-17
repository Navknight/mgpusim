#!/bin/bash
cd matrixtranspose
echo normal >> timing_report.txt
{ time ./matrixtranspose -timing -report-all -width=2048 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt