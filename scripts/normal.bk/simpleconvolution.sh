#!/bin/bash
cd simpleconvolution
echo normal >> timing_report.txt
{ time ./simpleconvolution -timing -report-all -width=1024 -height=1024 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt