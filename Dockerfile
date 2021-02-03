FROM python

RUN pip install flask && \
pip install flask_restful && \
pip install requests && \
pip install flask-cors && \
pip install bs4 && \
pip install notebook

expose 8888

ENTRYPOINT ["jupyter", "notebook", "--allow-root", "--ip", "0.0.0.0"]
