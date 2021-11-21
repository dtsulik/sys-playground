#!/bin/bash
while true
do
    du -sb /data | sed -ne 's/^\([0-9]\+\)\t\(.*\)$/node_directory_size_bytes{directory="\2"} \1/p' > /etc/node_exporter/directory_size.prom
    sleep 5
done
