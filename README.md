SCION Peering Coordinator
=========================
A peering coordination service for SCION ASes. Works as a companion to the
[SCIONLab coordinator](https://github.com/netsec-ethz/scionlab).

Original implementation as an extension to the SCIONLab coordinator: https://github.com/lschulz/scionlab

Implementation Status
---------------------
DONE:
- IXP and peering policy models
- Peering policy resolution and link creation
- Admin interface

TODO:
- Communication with client (gRPC)
- Coordinator looking glass (Django views)

Development
-----------
Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

Running the tests:
```bash
./manage.py makemigrations
./manage.py migrate
./manage.py test
```

Run the coordinator in Docker (Docker and docker-compose must be installed):
```bash
cd docker/devel
docker-compose up
```
Admin interface is at http://localhost:8000/admin (username: admin, password: admin).
