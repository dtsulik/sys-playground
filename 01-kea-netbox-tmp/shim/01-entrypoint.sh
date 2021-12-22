#!/bin/bash

./kea-netbox-shim.py -m db -p 8800 -u root \
    -s $MYSQL_ROOT_PASSWORD -d $MYSQL_DATABASE -t $NETBOX_TOKEN \
    -n $NETBOX_URL_WITHOUT_TRAILING_SLASH
