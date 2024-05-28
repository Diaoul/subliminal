FROM python:3.9.19-alpine3.20

MAINTAINER Antoine Bertin <diaoulael@gmail.com>

RUN apk add curl

# set version label
ARG UNRAR_VERSION=6.2.6

RUN \
apk add -U --update --no-cache --virtual=build-dependencies \
build-base && \
echo "**** install unrar from source ****" && \
mkdir /tmp/unrar && \
curl -o \
  /tmp/unrar.tar.gz -L \
  "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" && \  
tar xf \
  /tmp/unrar.tar.gz -C \
  /tmp/unrar --strip-components=1 && \
cd /tmp/unrar && \
make && \
install -v -m755 unrar /usr/local/bin 

RUN mkdir -p /usr/src/app /usr/src/cache

WORKDIR /usr/src/app
VOLUME /usr/src/cache

COPY . /usr/src/app
RUN python -m pip install .

RUN apk del py-pip build-base

ENTRYPOINT ["subliminal", "--cache-dir", "/usr/src/cache"]
CMD ["--help"]
