FROM python:3.12-alpine

LABEL org.opencontainers.image.authors="Antoine Bertin <diaoulael@gmail.com>"

# set version label
ARG BUILD_WITH_UNRAR=false
ARG UNRAR_VERSION=6.2.6

RUN \
if [ "$BUILD_WITH_UNRAR" = true ]; then \
    apk add -U --update --no-cache --virtual=build-dependencies build-base curl && \
    echo "**** install unrar from source ****" && \
    mkdir /tmp/unrar && \
    curl -o /tmp/unrar.tar.gz -L "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" && \
    tar xf /tmp/unrar.tar.gz -C /tmp/unrar --strip-components=1 && \
    cd /tmp/unrar && \
    make && \
    install -v -m755 unrar /usr/local/bin && \
    apk del build-dependencies curl && \
    rm -rf /tmp/unrar /tmp/unrar.tar.gz; \
fi

# install libmediainfo for metadata refiner
RUN apk add --no-cache libmediainfo

WORKDIR /usr/src/app
VOLUME /usr/src/cache

# Add git for setuptools-scm
RUN apk add --no-cache git
RUN \
    --mount=type=bind,source=.,target=. \
    --mount=type=cache,id=pip,target=/root/.cache/pip \
    python -m pip install .

ENTRYPOINT ["subliminal", "--cache-dir", "/usr/src/cache"]
CMD ["--help"]
