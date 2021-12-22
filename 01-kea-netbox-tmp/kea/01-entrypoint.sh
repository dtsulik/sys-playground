#!/bin/bash

sleep 1

if [[ ! -z $(mysql -u root -h $MYSQL_HOST -p$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE) ]]
then
    echo "Initializing db"
    mysql -u root -h $MYSQL_HOST -p$MYSQL_ROOT_PASSWORD -e "create database kea"
    /usr/sbin/kea-admin db-init mysql -u root \
        -p $MYSQL_ROOT_PASSWORD -n $MYSQL_DATABASE -h $MYSQL_HOST
fi

keactrl start -c /etc/kea/keactrl.conf

tail -f /dev/null
