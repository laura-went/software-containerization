FROM python:3.8-alpine
RUN mkdir /app
WORKDIR /app/
ADD . /app/
RUN \
 apk add --no-cache bash && \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
RUN pip install -r requirements.txt
ENV STATIC_URL /static
EXPOSE 5000
#CMD ["python", "/app/app.py"]
CMD ["/bin/bash", "entrypoint.sh"]