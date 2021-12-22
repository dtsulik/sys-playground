#!/bin/bash

echo "Initializing db"

/usr/sbin/kea-admin db-init mysql -u root \
    -p $MYSQL_ROOT_PASSWORD -n $MYSQL_DATABASE -h db

/usr/sbin/kea-dhcp4 -c /etc/kea/kea-dhcp4.conf
