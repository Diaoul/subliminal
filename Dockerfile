FROM python:3

MAINTAINER Antoine Bertin <diaoulael@gmail.com>

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY . /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["subliminal"]
CMD ["--help"]
