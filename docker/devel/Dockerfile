FROM python:3.8
ENV PYTHONUNBUFFERED 1

ARG COORD_UID=1000
ARG COORD_GID=1000

RUN apt-get update && apt-get upgrade -y

RUN groupadd -g ${COORD_GID:?} coord
RUN useradd -m -s /bin/bash -u ${COORD_UID:?} -g coord -G sudo coord

RUN mkdir /home/coord/peering-coord
COPY --chown=coord:coord . /home/coord/peering-coord

RUN pip install --require-hashes -r /home/coord/peering-coord/requirements.txt
RUN pip install appdeps

USER coord
WORKDIR /home/coord/peering-coord
RUN ./manage.py collectstatic --no-input
CMD docker/devel/webserver.sh
