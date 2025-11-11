FROM ghcr.io/shridarpatil/frappe

LABEL org.opencontainers.image.source=https://github.com/djs4000/frappe_whatsapp_waha
MAINTAINER djs4000 <djs4000@gmail.com>
RUN bench get-app https://github.com/djs4000/frappe_whatsapp_waha.git --skip-assets
