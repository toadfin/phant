FROM python:3.11-slim

COPY . .
RUN pip3 install -r requirements.txt

CMD [ "gunicorn", "app:app"]
