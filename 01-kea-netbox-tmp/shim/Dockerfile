FROM python:3.8.12-alpine

RUN apk add --no-cache bash
RUN pip install pymysql requests hvac
COPY kea-netbox-shim.py /kea-netbox-shim.py
RUN chmod +x /kea-netbox-shim.py
COPY 01-entrypoint.sh /01-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/01-entrypoint.sh"]