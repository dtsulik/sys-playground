# Kea Pdns Netbox Integration

## Dockerizing whole solution

To stuff all of this in docker we will use `shim` container which houses the netbox-kea shim script to also initialize database and all other components.

For bind add this to zone configuration for key named `ddns-key`
```
update-policy {
    grant ddns-key zonesub ANY;
};
```


## Part One: DDNS

There are few key elements to get DDNS working between KEA and PDNS.

1. generate TSIG key for authentication
`pdnsutil generate-tsig-key KEY_NAME hmac-sha256`
2. activate the said key for zone
`pdnsutil activate-tsig-key ZONE_NAME KEY_NAME master`
3. in ddns config file: `/usr/local/etc/kea/kea-dhcp-ddns.conf` add above tsig key
with this config block. Please note that key name must also match.
```json
    "tsig-keys": [
        {
            "name": "KEY_NAME",
            "algorithm": "hmac-sha256",
            "secret": "GENERATED_SECRET_HERE"
        }
    ],
```
4. add zone and dns server config block in same file.
```json
"forward-ddns" : {
        "ddns-domains": [
            {
                "name": "DOMAIN_NAME HERE WITH TRAILING DOT.",
                "key-name": "KEY_NAME",
                "dns-servers": [
                    {
                        "ip-address": "127.0.0.1",
                        "port": 53
                    }
                ]
            }
        ]
},
"reverse-ddns": {
        "ddns-domains": [
            {
                "name": "REVERSE ZONE NAME WITH TRAILING DOT.",
                "key-name": "KEY_NAME",
                "dns-servers": [
                    {
                        "ip-address": "127.0.0.1",
                        "port": 53
                    }
                ]
            }
        ]
    },
```
5. in subnet configuration file: `/usr/local/etc/kea/kea-dhcp4.conf` add following config:
```json
    "dhcp-ddns" : {
        "enable-updates" : true,
        "server-ip" : "127.0.0.1",
        "server-port" : 53001
    },
```
6. in same file under subnet sections make sure to enable ddns with following config block:
```json
    "subnet4": [
        {
            "ddns-send-updates" : true,
            "ddns-qualifying-suffix" : "DOMAIN_NAME HERE WITH TRAILING DOT.",
            ... rest of subnet config
        }
    ]
```
## Part Two: Enable host reservations from MYSQL
This assumes that KEA was built using `--with-mysql` option and mysql is up and running.
* in subnet configuration file: `/usr/local/etc/kea/kea-dhcp4.conf` add following config block:
```json
    "reservations-global": true,
    "hosts-databases": [
        {
            "name": "kea",
            "host": "localhost",
            "password": "PASS",
            "port": 3306,
            "type": "mysql",
            "user": "USER"
        }
    ],
```
NOTE: `"reservations-global": true,` can be enabled per subnet. It instructs kea to look for reservations using `subnet_id` of `0`.
## Part Three: Enable and configure KEA-Netbox shim service
1. add following to the `kea-netbox-shim.service` file at `/usr/lib/systemd/system/`
```
[Unit]
Description=kea-netbox-shim
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
ExecStart=/root/kea-netbox-shim -p PORT -s DB_PASS -t TOKEN -n NETBOX_URL_WITHOUT_TRAILING_SLASH

[Install]
WantedBy=multi-user.target
```
NOTE: Please make sure that netbox host url has no trailing slash
2. enable and start above service
```
systemctl daemon-reload
systemctl enable kea-netbox-shim
systemctl start kea-netbox-shim
```
3. configure following webhooks on netbox:
    * add-ip - in the body template section insert this block:
        ```json
        {
            "command": "reservation-add",
            "ip-address": "{{ data['address'] }}",
            "interface_url": "{{ data['assigned_object']['url'] }}",
            "dns_name": "{{ data['dns_name'] }}"
        }
        ```
    * del-ip - in the body template section insert this block:
        ```json
        {
            "command": "reservation-del",
            "ip-address": "{{ data['address'] }}",
            "interface_url": "{{ data['assigned_object']['url'] }}"
        }
        ```
    * del-mac - in the body template section insert this block:
        ```json
        {
            "command": "reservation-del",
            "mac": "{{ data['mac_address'] }}"
        }
        ```
    * update-mac - in the body template section insert this block:
        ```json
        {
            "command": "reservation-update",
            "mac": "{{ data['mac_address'] }}",
            "old_mac": "{{ snapshots['prechange']['mac_address'] }}",
            "new_mac": "{{ snapshots['postchange']['mac_address'] }}"
        }
        ```
    NOTE: for all hooks in url section make sure shim address has trailing slash, otherwise netbox will ignore it
