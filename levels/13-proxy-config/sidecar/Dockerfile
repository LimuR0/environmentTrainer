# 企业里那种"唯一出口"的正向代理（HTTP/HTTPS CONNECT 都能走）
FROM --platform=$TARGETPLATFORM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends tinyproxy ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/^Listen 127.0.0.1/Listen 0.0.0.0/' /etc/tinyproxy/tinyproxy.conf \
 && sed -i 's/^Allow 127.0.0.1/Allow 0.0.0.0\/0/' /etc/tinyproxy/tinyproxy.conf \
 && grep -E '^(Port|Listen|Allow)' /etc/tinyproxy/tinyproxy.conf

EXPOSE 8888
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
