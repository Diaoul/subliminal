FROM python:3-alpine

MAINTAINER Antoine Bertin <diaoulael@gmail.com>

RUN apk add --no-cache unrar
RUN mkdir -p /usr/src/app /usr/src/cache
WORKDIR /usr/src/app
VOLUME /usr/src/cache

COPY . /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["subliminal", "--cache-dir", "/usr/src/cache"]
CMD ["--help"]
