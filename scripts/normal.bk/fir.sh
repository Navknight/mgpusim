#!/bin/bash
cd fir
echo normal >> timing_report.txt
{ time ./fir -timing -report-all -length=4194304 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt