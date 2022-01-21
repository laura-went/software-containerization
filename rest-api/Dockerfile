# TODO: this might need some optimisations w.r.t layers
FROM python:3.7-alpine

# Add the necessary files
WORKDIR /code
COPY requirements.txt requirements.txt
COPY app.py app.py

# Install flask & psycopg2
RUN pip install -r requirements.txt

# Expose the port used by flask
EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
CMD ["flask", "run"]
