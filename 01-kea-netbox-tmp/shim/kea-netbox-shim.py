#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import requests
import sys
import getopt
import pymysql
import ipaddress
import json
import urllib
import ssl

version = "0.1.1"
http_port = 80
db_host = "127.0.0.1"
db_port = 3306
db_user = "root"
db_pass = "password"
db_name = "kea"
nb_host = "https://127.0.0.1"
nb_token = ''

class S(BaseHTTPRequestHandler):
    # ===========================================================================
    def _set_response(self):
    # ===========================================================================
        self.send_response(200)
        self.end_headers()

    # ===========================================================================
    def do_GET(self):
    # ===========================================================================
        self.send_response(405)

    # ===========================================================================
    def do_POST(self):
    # ===========================================================================
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_body = post_data.decode('utf-8')
        if 'ip' in self.path:
            kea_handle_ip(post_body)
        elif 'mac' in self.path:
            kea_handle_mac(post_body)
        else:
            logging.error("Unknown request path: %s, request_body %s", self.path, post_body)
        self._set_response()

class kea_db:
    # ===========================================================================
    def __init__(self):
    # ===========================================================================
        self.open_database()
        self.mycursor = self.mydb.cursor()

    # ===========================================================================
    @staticmethod
    def mac2int(mac):
    # ===========================================================================
        return int(mac.replace(':', ''),16)

    # ===========================================================================
    @staticmethod
    def int2mac(i):
    # ===========================================================================
        if type(i) == str:
            i = int(i, 16)
            s = hex(i).strip('0x').zfill(12)
            s = re.sub(r'(..)(?=[^$])', r'\1:', s)
            return s

    # ===========================================================================
    @staticmethod
    def ip2int(ip):
    # ===========================================================================
        return int(ipaddress.ip_address(ip))

    # ===========================================================================
    @staticmethod
    def int2ip(i):
    # ===========================================================================
        return str(ipaddress.ip_address(i))

    # ===========================================================================
    @staticmethod
    def ip2hex(ip):
    # ===========================================================================
        return hex(int(ipaddress.ip_address(ip))).strip('0x').zfill(8)

    # ===========================================================================
    @staticmethod
    def ip_list2hex(ip_list):
    # ===========================================================================
        return ''.join(map(kea_db.ip2hex, ip_list))

    # ===========================================================================
    @staticmethod
    def hex_2ip_list(h):
    # ===========================================================================
        return map(lambda t: str(ipaddress.ip_address(int(t, 16))), h)

    # ===========================================================================
    def getHostId(self, mac_address):
    # ===========================================================================
        self.mycursor.execute(f"""select host_id from hosts 
                    where dhcp_identifier =
                    UNHEX('{mac_address.replace(':', '')}');""")
        return self.mycursor.fetchall()

    # ===========================================================================
    def delete_from_database(self, mac_address):
    # ===========================================================================
        hosts_id = self.getHostId(mac_address)
        for host_id in [t[0] for t in hosts_id]:
            self.mycursor.execute(f"delete from dhcp4_options where host_id={host_id};")
            self.mycursor.execute(f"delete from dhcp6_options where host_id={host_id};")
            self.mycursor.execute(f"delete from hosts     where host_id={host_id};")
            self.mydb.commit()

    # ===========================================================================
    def update_database(self, old_mac_address, new_mac_address):
    # ===========================================================================
        hosts_id = self.getHostId(old_mac_address)
        for host_id in [t[0] for t in hosts_id]:
            logging.info('mac UPDATE query: update hosts set dhcp_identifier=UNHEX(REPLACE(\'%s\', \':\', \'\')) where host_id=%d;', new_mac_address, host_id)
            self.mycursor.execute(f"update hosts set dhcp_identifier=UNHEX(REPLACE('{new_mac_address}', ':', '')) where host_id={host_id};")
            self.mydb.commit()

    # ===========================================================================
    def insert_record_to_hosts(self, mac_address, identifier_type, dhcp4_subnet_id, ipv4_address, hostname):
    # ===========================================================================
        sql_insert   = f"""INSERT INTO hosts (dhcp_identifier,
                                            dhcp_identifier_type,
                                            dhcp4_subnet_id,
                                            ipv4_address,
                                            hostname)
                            VALUES (          UNHEX(REPLACE('{mac_address}', ':', '')),
                                            (SELECT type FROM host_identifier_type
                                                    WHERE name='{identifier_type}'),
                                            {dhcp4_subnet_id},
                                            INET_ATON('{ipv4_address}'),
                                            '{hostname}');"""

        logging.info('Insert query: %s', sql_insert)

        self.delete_from_database(mac_address)
        self.mycursor.execute(sql_insert)
        self.mycursor.execute("SELECT LAST_INSERT_ID(); ")
        host_id = self.mycursor.fetchone()
        return host_id[0]

    # ===========================================================================
    def set_option(self, host_id, option, value, scope_name='subnet'):
    # ===========================================================================
    # Option codes:  https://www.iana.org/assignments/bootp-dhcp-parameters/bootp-dhcp-parameters.txt
    # space:   # see https://docs.infoblox.com/display/NAG8/About+IPv4+DHCP+Options
        if option == "": return
        if option not in ['routers', 'domain-name-servers']:
            print(f"Option {option} not currently supported")
            sys.exit()

        option_codes = {'routers':             3,
                        'domain-name-servers': 6,
                    }

        dns_options_list = value.replace(' ', '').split(',')
        sql_dns = f"""INSERT INTO dhcp4_options (code, value, space, host_id, scope_id)
                    VALUES ({option_codes[option]},
                            UNHEX('{self.ip_list2hex(dns_options_list)}'),
                            'dhcp4',
                            {host_id},
                            (SELECT scope_id FROM dhcp_option_scope
                                WHERE scope_name = '{scope_name}'));"""
        logging.info('Options query: %s', sql_dns)
        self.mycursor.execute(sql_dns)

    # ===========================================================================
    def print_host_database(self):
    # ===========================================================================
        sql = """SELECT hosts.host_id,
                        hex(hosts.dhcp_identifier),
                        hosts.dhcp_identifier_type, 
                        hosts.dhcp4_subnet_id,
                        hosts.ipv4_address,
                        hosts.hostname
                FROM hosts """
        self.mycursor.execute(sql)
        for host_id, mac, _, subnet_id, addr, hostname, in self.mycursor:
            print(host_id, self.int2mac(mac), subnet_id, self.int2ip(addr), hostname, sep='\t')

    # ===========================================================================
    def print_option_database(self):
    # ===========================================================================
        sql = """SELECT hosts.host_id,
                        hex(hosts.dhcp_identifier),
                        hosts.ipv4_address,
                        hosts.hostname,
                        dhcp4_options.code,
                        hex(dhcp4_options.value),
                        dhcp4_options.space,
                        dhcp4_options.scope_id
            FROM hosts INNER JOIN dhcp4_options
                ON hosts.host_id=dhcp4_options.host_id;"""
        self.mycursor.execute(sql)
        for host_id, mac, addr, hostname, code, value, space, scope_id in self.mycursor:
            value_list = re.findall(r'(........)', value) if value else []
            print(f"{host_id:<7} {self.int2mac(mac):<20} {self.int2ip(addr):<10} {code:>5} {space:>5} {scope_id:>5}   {hostname:<15}", *self.hex_2ip_list(value_list))

    # ===========================================================================
    def open_database(self):
    # ===========================================================================
        self.mydb = pymysql.connect(host=db_host,
                                    port=db_port,
                                    user=db_user,
                                    password=db_pass,
                                    database=db_name)

# ===========================================================================
def kea_handle_mac(post_body):
# ===========================================================================
    logging.info('Got mac request with data:\n%s\n', post_body)
    obj = json.loads(post_body)

    if 'mac' not in obj:
        logging.info('Invalid request')
        return

    if 'del' in obj['command']:
        logging.info('Got del request with arguments: MAC:%s', obj['mac'])
        Kea_DB = kea_db()
        Kea_DB.delete_from_database(obj['mac'])
        Kea_DB.mydb.commit()
        Kea_DB.mycursor.close()
        Kea_DB.mydb.close()
    elif 'update' in obj['command']:
        logging.info('Got update request with arguments: MAC:%s', obj['old_mac'], obj['new_mac'])
        Kea_DB = kea_db()
        Kea_DB.update_database(obj['old_mac'], obj['new_mac'])
        Kea_DB.mydb.commit()
        Kea_DB.mycursor.close()
        Kea_DB.mydb.close()

# ===========================================================================
def kea_handle_ip(post_body):
# ===========================================================================
    logging.info('Got ip request with data:\n%s\n', post_body)
    obj = json.loads(post_body)

    if 'interface_url' not in obj or 'ip-address' not in obj:
        logging.info('Invalid request')
        return

    interface_url = nb_host + obj['interface_url']
    logging.info('interface url: %s\n', interface_url)
    hdr = { 'Authorization': 'Token ' + nb_token}
    req = urllib.request.Request(interface_url, headers=hdr)
    response = urllib.request.urlopen(req, context=ssl._create_unverified_context())
    interface = json.loads(response.read())
    ipaddress = str(obj['ip-address']).split('/')[0]

    if 'add' in obj['command']:
        logging.info('Got add request with arguments: IP:%s MAC:%s Hostname:%s',
            ipaddress, interface['mac_address'], obj['dns_name'])
        Kea_DB = kea_db()
        Kea_DB.insert_record_to_hosts(interface['mac_address'], 'hw-address', 0,
            ipaddress, obj['dns_name'])
        Kea_DB.mydb.commit()
        Kea_DB.mycursor.close()
        Kea_DB.mydb.close()
    elif 'del' in obj['command']:
        logging.info('Got del request with arguments: IP:%s MAC:%s', ipaddress,
            interface['mac_address'])
        Kea_DB = kea_db()
        Kea_DB.delete_from_database(interface['mac_address'])
        Kea_DB.mydb.commit()
        Kea_DB.mycursor.close()
        Kea_DB.mydb.close()
    else:
        logging.info('Ignoring unknown request')
        return

# ===========================================================================
def usage():
# ===========================================================================
    u = """
-h, --help              print this message
-v, --verbose           be verbose
-p, --port              port number listening for http connections, default: 80
-d, --database          database name to use, default: kea
-m, --mysql-host        mysql host ip, default: 127.0.0.1
    --mysql-port        mysql port number, default: 3306
-u, --user              mysql user, default: root
-s, --password          mysql password, default: password
-n, --netbox            netbox host url (please note NOT to include trailing '/'), default: https://127.0.0.1
-t, --token             netbox auth token, default: null
    """
    print("Version: " + version)
    print(u)

# ===========================================================================
def parse_opts():
# ===========================================================================
    global http_port
    global db_host
    global db_port
    global db_user
    global db_pass
    global db_name
    global nb_host
    global nb_token
    token_set = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvp:d:m:u:s:n:t:", ["help", "verbose",
            "port=", "database=", "mysql-host=", "mysql-port=", "user=", "password=",
            "netbox=", "token="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for o, v in opts:
        if o in ("-v", "--verbose"):
            logging.basicConfig(level=logging.DEBUG)
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-p", "--port"):
            http_port = v
        elif o in ("-d", "--database"):
            db_name = v
        elif o in ("-m", "--mysql-host"):
            db_host = v
        elif o in ("--mysql-port"):
            db_port = int(v)
        elif o in ("-u", "--user"):
            db_user = v
        elif o in ("-s", "--password"):
            db_pass = v
        elif o in ("-n", "--netbox"):
            nb_host = v
        elif o in ("-t", "--token"):
            token_set = True
            nb_token = v
        else:
            assert False, "unhandled option"
    logging.basicConfig(level=logging.INFO)
    if token_set == False:
        logging.error('Please provide netbox auth token!')
        sys.exit(1)

    logging.info('Listening on: %s Connecting to DB: %s:%s.\n\tDatabase name: %s, Netbox host: %s',
        http_port, db_host, db_port, db_name, nb_host)


# ===========================================================================
def main(server_class=HTTPServer, handler_class=S):
# ===========================================================================
    logging.info('Starting kea-netbox shim on: %s\n', http_port)
    server_address = ('', int(http_port))
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping kea-netbox shim\n')

if __name__ == '__main__':
    parse_opts()
    main()
