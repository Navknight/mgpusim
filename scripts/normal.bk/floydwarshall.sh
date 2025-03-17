#!/bin/bash
cd floydwarshall
echo normal >> timing_report.txt
{ time ./floydwarshall -timing -report-all -node=1024 -iter=32 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt