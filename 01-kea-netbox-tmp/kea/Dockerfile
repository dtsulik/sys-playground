FROM ubuntu:impish-20210722 as builder

ARG CFLAGS="-O2 -pthread -pipe -fPIC -fPIE -fomit-frame-pointer "
ARG CXXFLAGS="${CFLAGS} "
ARG LDFLAGS="-Wl,-O2 -Wl,--as-needed -Wl,-z,relro -Wl,-z,now "

ENV DEBIAN_FRONTEND noninteractive
RUN cp /etc/apt/sources.list /etc/apt/sources.list~ \
    && sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list \
    && apt update
RUN apt build-dep kea-common -y
RUN apt install -y git build-essential
RUN git clone https://gitlab.isc.org/isc-projects/kea.git
WORKDIR /kea
RUN autoreconf -if \
    && autoreconf --install \
    && ./configure \
    --with-mysql \
    --disable-rpath \
    --disable-static \
    --prefix=/usr \
    --sysconfdir=/etc \
    CFLAGS="${CFLAGS}" CXXFLAGS="${CFLAGS}" LDFLAGS="${LDFLAGS}"
RUN make install DESTDIR=/tmp/root
RUN ldconfig /
RUN rm -rf /tmp/root/var/run /tmp/root/usr/local/share/man/* /tmp/root/usr/local/include /tmp/root/usr/include \
    /tmp/root/usr/share/doc/kea /tmp/root/usr/local/lib/kea/hooks/*.la \
    /tmp/root/usr/local/lib/*.la /tmp/root/usr/local/include/*

FROM ubuntu:impish-20210722
RUN apt update && apt install -y mysql-client mysql-common liblog4cplus-2.0.5 libmysqlclient21

COPY --from=builder /tmp/root /
RUN ldconfig /

EXPOSE 67/udp 68/udp 547/udp 547/tcp

COPY 01-entrypoint.sh /01-entrypoint.sh

ENTRYPOINT ["/01-entrypoint.sh"]