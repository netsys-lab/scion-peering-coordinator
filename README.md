SCION Peering Coordinator
=========================
A peering coordination service for SCION ASes. Works as a companion to the
[SCIONLab coordinator](https://github.com/netsec-ethz/scionlab).

Original implementation as an extension to the SCIONLab coordinator: https://github.com/lschulz/scionlab

Dependencies
------------
Install the Python dependencies by running (preferably in a venv)
```bash
pip3 install -r requirements.txt
```

Development
-----------

### Tests
```bash
./manage.py makemigrations
./manage.py migrate
./manage.py test
```

### Running the development server
```bash
./manage.py runserver 127.0.0.1:8000            # first terminal
./manage.py grpcrunserver --dev 127.0.0.1:50051 # second terminal
```

### Running in Docker
Docker and docker-compose must be installed.

```bash
cd docker/devel
docker-compose up
```
Main web interface is at http://localhost:8000
Admin interface is at http://localhost:8000/admin (username: admin, password: admin).
