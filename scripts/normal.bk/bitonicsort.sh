#!/bin/bash
cd bitonicsort
echo normal >> timing_report.txt
{ time ./bitonicsort -timing -report-all -length=524288 -unified-gpus=1,2,3,4 ;} >>log.txt 2>> timing_report.txt