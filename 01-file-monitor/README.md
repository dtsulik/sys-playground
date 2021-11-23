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
### Quick start
To directly install all components to system run:
```
$ ansible-playbook install-all.yaml
```
You can also separately install collectors on target systems:
```
$ ansible-playbook install-agents.yaml
```

Biggest difference from docker method is that instead of `runner` container we are installing a cron to do the same job. Instread of `/data` folder specify the target directory.

```
*/1 * * * *   root du -sb /data | sed -ne 's/^\([0-9]\+\)\t\(.*\)$/node_directory_size_bytes{directory="\2"} \1/p' > /etc/node_exporter/directory_size.prom
```

## Step by Step guide
### Prerquisite setup
Following example is on freshly installed Centos system:
+ Step 1: Update system and packages:
```
$ sudo yum update -y
```
+ Step 2: install required packages:
```
$ sudo yum install -y epel-release
$ sudo yum install -y yum-utils git ansible
```
+ Step 3a: add docker repo and install docker (Centos 7 or earlier):
```
$ sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/rhel/docker-ce.repo
$ sudo yum install -y docker-ce docker-ce-cli containerd.io
```
+ Step 3b: add docker repo and install docker (Centos 8 stream or later):
```
$ sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
$ sudo dnf install -y docker-ce docker-ce-cli containerd.io
```
+ Step 4: enable and start docker:
```
$ sudo systemctl enable --now docker
```
+ Step 5: if running docker from unprivilleged user (non root) add that user to docker group or skip to 6:
```
$ sudo usermod -aG docker user
```
+ Step 6: install docker-compose:
```
$ sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
$ sudo chmod +x /usr/local/bin/docker-compose
$ sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
```
NOTE: the `ln -s` to `/usr/bin` directory is needed to make `docker-compose` command available to root user for `sudo docker-compose` if it may be needed.

### File monitor setup (Docker way)
+ Step 1: Clone this repo:
```
$ git clone https://github.com/dtsulik/sys-playground.git
```
+ Step 2: Set permissions for directories backing the docker volumes:
```
$ cd sys-playground/01-file-monitor/
$ chmod a+w grafana-storage
$ chmod a+w etc/node_exporter
```
+ Step 3: set target directory (in this case its `/home/user/`):
```
$ echo 'TARGET_DIR=/home/user/' > .env
```
+ Step 4: set current user id:
```
$ echo CURRENT_UID=$(id -u):$(id -g) >> .env
```
+ Step 5: Start the services:
```
$ docker-compose up
```
### File monitor setup (direct install)
+ Step 1: Install ansible community packages
```
$ sudo ansible-galaxy collection install community.general
```
+ Step 2: Install python3 and pip3
```
$ sudo yum install -y python3 python3-pip
```
+ Step 3: install pip module:
```
$ sudo pip3 install github3.py
```
+ Step 4: edit [inventory.yaml](/01-file-monitor/inventory.yaml)
+ Step 5: Run ansible playbook
```
$ sudo ansible-playbook install-all.yaml
```
### Grafana setup (Docker and direct)
+ Step 1: allow Grafana UI in firewall:
```
$ sudo firewall-cmd --add-port=3000/tcp
```
+ Step 2: access Grafana UI at `http://HOST_IP:3000`
```
User: admin
Pass: admin
```
+ Step 3: add Prometheus as datasource:

NOTE: if the prometheus is installed directly to system instead of `prometheus` in address use HOST_IP
* Go to datasources menu
![Grafana datasource](/01-file-monitor/doc/screens/grafana_01.jpg?raw=true "Grafana datasource")

* Select prometheus from list
![Grafana datasource](/01-file-monitor/doc/screens/grafana_02.jpg?raw=true "Grafana datasource")

NOTE: In case of direct install it will be HOST_IP instead of prometheus. For example:

* In URL field insert `http://prometheus:9090`
`http://192.168.10.42:9090`
![Grafana datasource](/01-file-monitor/doc/screens/grafana_03.jpg?raw=true "Grafana datasource")
* Scroll down and click `Save & test`

+ Step 4: import dashboard:
    * Copy conents of [grafana/dashboard.json](/01-file-monitor/grafana/dashboard.json)
    * Click import:
![Grafana dashboard](/01-file-monitor/doc/screens/grafana_04.jpg?raw=true "Grafana dashboard")
    * Paste contents of dashboard.json in `Import via panel json`:
![Grafana dashboard](/01-file-monitor/doc/screens/grafana_05.jpg?raw=true "Grafana dashboard")
    * Press `Load` and then `Import`. Done.

In case ansible fails to install. Here is brief description of how to do it manually.
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
