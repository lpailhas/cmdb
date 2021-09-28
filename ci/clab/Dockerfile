# Install python dependencies
FROM python:3.8-buster AS dependencies
WORKDIR /app
ENV PYTHONUSERBASE=/app/python
RUN pip install --user --no-warn-script-location pipenv
COPY Pipfile* ./
RUN env PIP_USER=1 PIPENV_SYSTEM=1 /app/python/bin/pipenv install --deploy


# Compile containerlab
FROM golang:1.16-alpine as containerlab
WORKDIR /app
RUN apk add --no-cache \
        git \
        make \
        gcc \
        musl-dev 
RUN git clone https://github.com/srl-labs/containerlab.git
RUN cd containerlab/ && git checkout v0.16.0 && make

FROM docker:19.03-dind
WORKDIR /app
RUN apk add --no-cache \
        git \
        tar \
        make \
        python3 
ENV PYTHONUSERBASE=/app/python
COPY --from=dependencies $PYTHONUSERBASE $PYTHONUSERBASE
COPY --from=containerlab /app/containerlab /app/containerlab
RUN git clone https://github.com/lpailhas/vrnetlab.git && cd vrnetlab/ && git checkout v0.5.1
#RUN git clone https://github.com/hellt/vrnetlab.git && cd vrnetlab/ && git checkout v0.5.0
ENV PATH="${PYTHONUSERBASE}/bin:${PATH}"
ENTRYPOINT ["python3"]
CMD ["/app/wrapper.py"]

