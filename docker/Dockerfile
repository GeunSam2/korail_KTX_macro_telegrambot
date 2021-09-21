FROM python:3.7

RUN apt-get update && \
apt-get install -y nginx

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/requirements.txt /requirements.txt

RUN chmod 775 /entrypoint.sh
RUN pip install -r /requirements.txt

COPY source /source
COPY nginx/wsgi.conf /etc/nginx/conf.d/wsgi.conf

EXPOSE 8080 
#EXPOSE 8888
# API : 8080 / JUPYTER : 8888

WORKDIR /source

ENTRYPOINT /entrypoint.sh
