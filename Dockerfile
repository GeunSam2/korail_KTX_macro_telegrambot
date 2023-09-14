FROM python:3.7

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/requirements.txt /requirements.txt

RUN chmod 775 /entrypoint.sh
RUN pip install -r /requirements.txt

COPY source /source

EXPOSE 8080 

WORKDIR /source

ENTRYPOINT ["python", "app.py"]
