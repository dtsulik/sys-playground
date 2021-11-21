# File and directory size monitoring
This doc explains how to monitor X folder and its contents for size. There are two ways the solution can be deployed:

+ docker-compose
+ direct install to system

The github repositories used:

+ [Filestats](https://github.com/michael-doubez/filestat_exporter)
+ [Prometheus](https://github.com/prometheus/prometheus)
+ [Node exporter](https://github.com/prometheus/node_exporter)
+ [Grafana](https://github.com/grafana/grafana)

## Docker way
### Quick start
To quickly get started set target directory in `.env` file, change direcotry permisions 
```
$ sudo chmod a+w grafana-storage
$ sudo chmod a+w etc/node_exporter
```
and run `docker-compose up --build`

+ The grafana dashboard will be located at http://HOST_IP:3000/
+ This documentation will be served at http://HOST_IP:9001/

Grafana settings can be changed in `grafana.ini` located in `grafana` folder. After change rerun `docker-compose up --build`.

### Details
The chain of information goes in following way:

+ `runner` container which runs a bash script generating a metric for the directory size that prometheus is able to understand.
+ optionaly `filestat` container can export size metrics for all files found in the target directory. Settings on what to match can be tweaked in `etc/filestats/filestats.yaml` under `files:` by adding various `patterns`.
+ next the `node_exporter` consumes this metric and exposes it to prometheus. NOTE that node exporter has all metrics disabled except the text exporter in order not to introduce extra load on system.
+ `prometheus` scrapes this metric and monitors it as usual
+ at the end `grafana` consumes metrics from prometheus and draws some graphs. Sample dashboard definition file can be found in `grafana` directory. Grafana settings can be tweaked in `grafana/grafana.ini` file. After change please run `docker-compose up --build` in order to rebuild docker image

## Direct install to system

Biggest difference from docker method is that instead of `runner` container we are installing a cron to do the same job. Instread of `/data` folder specify the target directory.

Add following to `/etc/crontab`:
```
*/1 * * * *   root du -sb /data | sed -ne 's/^\([0-9]\+\)\t\(.*\)$/node_directory_size_bytes{directory="\2"} \1/p' > /etc/node_exporter/directory_size.prom
```

These 3 services do not come with RPM or DEB packaging and need to be installed directly. Download their binaries and place them in respecive folders.

+ [Filestats](https://github.com/michael-doubez/filestat_exporter/releases)
+ [Prometheus](https://github.com/prometheus/prometheus/releases)
+ [Node exporter](https://github.com/prometheus/node_exporter/releases)

For example:

```
$ wget 'https://github.com/prometheus/prometheus/releases/download/v2.31.1/prometheus-2.31.1.linux-amd64.tar.gz'
$ mkdir prometheus
$ tar xzf prometheus-*.tar.gz -C prometheus --strip-components 1
$ sudo cp prometheus/prometheus /opt/prometheus/prometheus
```
Copy config and service file from this projects directory:
```
$ sudo cp -r etc/prometheus /etc/prometheus
$ sudo cp systemd-services/prometheus.service /usr/lib/systemd/system/
$ sudo systemctl daemon-reload
$ sudo systemctl enable prometheus
$ sudo systemctl start prometheus
```
NOTE: this example assumes you are installing in `/opt/`. If you do install in other directory please update relevant service file located in `systemd-services`.

As for Grafana, it provides various packagings for OS es. [Instructions](https://grafana.com/docs/grafana/latest/installation/rpm/) for RPM based systems.
