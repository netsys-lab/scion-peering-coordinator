FROM python:3.8
ENV PYTHONUNBUFFERED 1

RUN mkdir /peering-coord
COPY . /peering-coord
WORKDIR /peering-coord

RUN pip install --require-hashes -r requirements.txt
RUN pip install appdeps

CMD docker/devel/entrypoint.sh /peering-coord
