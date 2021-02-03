FROM python

RUN pip install flask && \
pip install flask_restful && \
pip install requests && \
pip install flask-cors && \
pip install bs4 && \
pip install python-telegram-bot && \
pip install notebook


COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod 775 /entrypoint.sh

expose 8888

ENTRYPOINT /entrypoint.sh
