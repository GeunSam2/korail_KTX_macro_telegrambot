FROM python

RUN pip install flask && \
pip install flask_restful && \
pip install requests && \
pip install flask-cors && \
pip install bs4 && \
pip install python-telegram-bot && \
pip install pyOpenSSL && \
pip install uwsgi && \
pip install notebook

RUN apt-get update && \
apt-get install -y nginx


COPY docker/entrypoint.sh /entrypoint.sh
COPY source /source
COPY nginx/wsgi.conf /etc/nginx/conf.d/wsgi.conf

RUN chmod 775 /entrypoint.sh

expose 8888 8080

ENTRYPOINT /entrypoint.sh
