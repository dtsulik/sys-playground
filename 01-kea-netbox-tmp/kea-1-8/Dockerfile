FROM ubuntu:impish-20210722 as builder

ENV DEBIAN_FRONTEND noninteractive
RUN apt update && apt install kea-* mysql-client -y
RUN mkdir /run/kea
COPY 01-entrypoint.sh /01-entrypoint.sh
EXPOSE 67/udp
EXPOSE 68/udp
ENTRYPOINT ["/01-entrypoint.sh"]