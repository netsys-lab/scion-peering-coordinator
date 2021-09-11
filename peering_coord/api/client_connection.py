"""Classes for managing the persistent gRPC stream maintained with every peering client.

Peering clients receive push notifications from the coordinator (link updates, etc.) on a
persistent bidirectional gRPC stream. This file contains three classes maintaining these streams:

- ClientConnection represents an individual connection. It purpose is mainly to allow threads
  other than the request handler thread to send notifications on the stream.
- ClientConnections contains all active ClientConnection instances belonging to an AS. It handles
  arbitration of policy write permissions between multiple clients.
- ClientRegistry is a static class keeping track of all ClientConnections instances.
"""

import queue
import threading
from collections import defaultdict
from enum import Enum
from typing import DefaultDict, Dict, Iterator, Optional

from peering_coord.api import peering_pb2
from peering_coord.api.authentication import get_client_from_metadata
from peering_coord.models.ixp import Interface, Link, PeeringClient
from peering_coord.models.scion import AS
from peering_coord.scion_addr import ASN


def create_link_update(update_type: peering_pb2.LinkUpdate.Type, link_type: Link.Type,
    local_interface, local_port, remote_interface, remote_port) -> peering_pb2.LinkUpdate:
    """Creates a link update message for peering clients."""

    update = peering_pb2.LinkUpdate()
    update.type = update_type

    if link_type == Link.Type.PEERING:
        update.link_type = peering_pb2.LinkUpdate.LinkType.PEERING
    elif link_type == Link.Type.CORE:
        update.link_type = peering_pb2.LinkUpdate.LinkType.CORE
    elif link_type == Link.Type.PROVIDER:
        update.link_type = peering_pb2.LinkUpdate.LinkType.PROVIDER

    update.peer_asn = str(remote_interface.peering_client.asys.asn)
    update.local.ip = str(local_interface.public_ip)
    update.local.port = local_port
    update.remote.ip = str(remote_interface.public_ip)
    update.remote.port = remote_port

    return update


class ClientConnection:
    """Represents an active connection to a peering client. Mainly consists of a Queue for
    forwarding commands to the gRPC thread handling the persistent stream.
    """

    class Command(Enum):
        EXIT = 0
        PROCESS_REQUEST = 1
        SEND_RESPONSE = 2

    def __init__(self, name: str, as_connections: 'ClientConnections'):
        self.name = name
        self._as_connections = as_connections
        self._response_queue = queue.SimpleQueue()

    @property
    def asn(self):
        return self._as_connections.asn

    def stream_request_received(self, request: peering_pb2.StreamMessageRequest) -> None:
        """Post a request messages received by the receiver thread to the sender thread."""
        self._response_queue.put((self.Command.PROCESS_REQUEST, request))

    def request_stream_closed(self):
        """Indicate that no more request will be send on the stream, causing the sender thread to
        return from the gRPC call.
        """
        self._response_queue.put((self.Command.EXIT, None))

    def send_arbitration_update(self, update: peering_pb2.ArbitrationUpdate) -> None:
        """Enqueue an arbitration update to be send to the peering client."""
        msg = peering_pb2.StreamMessageResponse()
        msg.arbitration.CopyFrom(update)
        self._response_queue.put((self.Command.SEND_RESPONSE, msg))

    def send_link_update(self, update: peering_pb2.LinkUpdate) -> None:
        """Enqueue a link update to be send to the peering client."""
        msg = peering_pb2.StreamMessageResponse()
        msg.link_update.CopyFrom(update)
        self._response_queue.put((self.Command.SEND_RESPONSE, msg))

    def send_async_error(self, error: peering_pb2.LinkUpdate) -> None:
        """Enqueue an asynchronous error report to be send to the peering client."""
        msg = peering_pb2.StreamMessageResponse()
        msg.error.CopyFrom(error)
        self._response_queue.put((self.Command.SEND_RESPONSE, msg))

    def run(self) -> Iterator[peering_pb2.StreamMessageResponse]:
        """Generator for gRPC response messages. Must be called in the thread handling the stream
        RPC to process requests and generate responses. The generator quits after
        request_stream_closed() has been called by the receiver thread.
        """
        while True:
            command, data = self._response_queue.get()
            if command == self.Command.EXIT:
                return
            elif command == self.Command.PROCESS_REQUEST:
                req_type = data.WhichOneof('request')
                if req_type == "arbitration":
                    self._as_connections.arbitrate(self, data.arbitration)
            elif command == self.Command.SEND_RESPONSE:
                yield data


class ClientConnections:
    """Aggregates the individual client connections of an AS and handles election of the primary
    client.
    """

    class AlreadyConnected(Exception):
        def __str__(self):
            return "Connection is already open"

    def __init__(self, asn: ASN):
        self.asn = asn
        self._lock = threading.Lock()
        # Mapping from client name to connection instance.
        self.connections: Dict[str, ClientConnection] = {}
        # Mapping from VLAN (name) to dictionary of client (name) and election ID in that VLAN.
        self._election: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
        # Mapping from VLAN (name) to primary client (name).
        self._primary: Dict[str, str] = {}

    def get_connections(self) -> Iterator[ClientConnection]:
        """Returns an iterator over all active connections."""
        for conn in self.connections.values():
            yield conn

    def create(self, name: str) -> ClientConnection:
        """Register a connection to a new client.

        :raises KeyError: A client of the given name does not exist in the database.
        :raises ClientConnections.AlreadyConnected: The client is already connected.
        """
        with self._lock:
            if not PeeringClient.objects.filter(asys__asn=self.asn, name=name).exists():
                raise KeyError("Client not found in database")

            if name in self.connections:
                raise self.AlreadyConnected()

            conn = ClientConnection(name, self)
            self.connections[name]  = conn
            return conn

    def destroy(self, conn: ClientConnection) -> None:
        """Remove a closed connection."""
        with self._lock:
            # Remove client from election.
            for vlan in self._election.values():
                vlan.pop(conn.name, None)

            # Elect new primary clients where necessary.
            for vlan, client in self._primary.items():
                if client == conn.name:
                    self._arbitrate(vlan)

            del self.connections[conn.name]

    def arbitrate(self, requester: ClientConnection, arbitration: peering_pb2.ArbitrationUpdate):
        """Handle an arbitration request from one of the clients."""
        with self._lock:
            try:
                client = PeeringClient.objects.get(asys__asn=self.asn, name=requester.name)
                interfaces = client.interfaces
            except PeeringClient.DoesNotExist:
                arbitration.status = peering_pb2.ArbitrationUpdate.Status.ERROR
                requester.send_arbitration_update(arbitration)
                return

            if arbitration.HasField("vlan"):
                try:
                    interface = interfaces.get(vlan__name=arbitration.vlan)
                    vlan = interface.vlan.name
                except Interface.DoesNotExist:
                    arbitration.status = peering_pb2.ArbitrationUpdate.Status.ERROR
                    requester.send_arbitration_update(arbitration)
                    return
                self._election[vlan][requester.name] = arbitration.election_id
                self._arbitrate(vlan)
            else:
                for interface in client.interfaces.all():
                    vlan = interface.vlan.name
                    self._election[vlan][requester.name] = arbitration.election_id
                    self._arbitrate(vlan)

    def remove_interface(self, client: str, vlan: str):
        """Called when am interface is removed from a client. Updates the primary client for the
        VLAN is necessary.
        """
        with self._lock:
            if client in self._election[vlan]:
                del self._election[vlan][client]
            if self._primary[vlan] == client:
                self._arbitrate(vlan)

    def remove_client(self, client: str):
        """Called when a client has been delete from the database. Closes the connection to the
        deleted client, if it is still open.
        """
        with self._lock:
            conn = self.connections.get(client)
            if conn is not None:
                conn.request_stream_closed()
                del self.connections[client]

    def is_primary_client(self, client: str, vlan: Optional[str]) -> Optional[str]:
        """Checks whether 'client' is the primary client in the given vlan. If 'vlan' is None,
        checks if the client is primary in all VLANS.
        """
        with self._lock:
            if vlan is not None:
                primary = self._primary.get(vlan)
                return primary is not None and primary == client
            else:
                return all(primary == client for primary in self._primary.values())

    def _arbitrate(self, vlan: str):
        """Select the primary client in the given VLAN and notify all clients with connections to
        the VLAN.
        """
        # Determine primary client
        primary = (None, -2**63)
        for client, election_id in self._election.get(vlan, {}).items():
            if election_id >= primary[1]:
                primary = (client, election_id)
        self._primary[vlan] = primary[0]

        # Notify all clients
        update = peering_pb2.ArbitrationUpdate()
        update.vlan = vlan
        for client, election_id in self._election.get(vlan, {}).items():
            update.election_id = election_id
            if client == primary[0]:
                update.status = peering_pb2.ArbitrationUpdate.Status.PRIMARY
            else:
                update.status = peering_pb2.ArbitrationUpdate.Status.NOT_PRIMARY
            self.connections[client].send_arbitration_update(update)


class ClientRegistry:
    """Static class which keeps track of active client connections with the help of
    ClientConnections and ClientConnection.
    """

    # Mapping from ASN to a collection of all its connected peering clients.
    _ases: Dict[ASN, ClientConnections] = {}

    @staticmethod
    def createConnection(asn: ASN, client_name: str) -> ClientConnection:
        """Create a new client connection object, as reaction to establishing a gRPC connection to
        a client.

        :param asn: ASN of the AS the client belongs to.
        :param client_name: AS-unique name of the client. Only one connection is allowed per client.
        :raises KeyError: ASN or client not found in database.
        :raises ClientConnections.AlreadyConnected: The client is already connected.
        """
        if not AS.objects.filter(asn=asn).exists():
            raise KeyError("ASN not found.")

        if asn not in ClientRegistry._ases:
            ClientRegistry._ases[asn] = ClientConnections(asn)
        connections = ClientRegistry._ases[asn]

        try:
            conn = connections.create(client_name)
        finally:
            if len(connections.connections) == 0:
                del ClientRegistry._ases[asn]

        return conn

    @staticmethod
    def destroyConnection(conn: ClientConnection) -> None:
        """Destroy a client connection object, as reaction to the gRPC connection closing.

        :param conn: Connection to destroy.
        """
        asn = conn.asn
        connections = ClientRegistry._ases[asn]
        connections.destroy(conn)
        if len(connections.connections) == 0:
            del ClientRegistry._ases[asn]

    @staticmethod
    def remove_interface(asn: ASN, client: str, vlan: str):
        ClientRegistry._ases[asn].remove_interface(client, vlan)

    @staticmethod
    def remove_client(asn: ASN, client: str):
        ClientRegistry._ases[asn].remove_client(client)

    @staticmethod
    def get_clients(asn: ASN) -> Optional[ClientConnections]:
        return ClientRegistry._ases.get(asn)

    @staticmethod
    def has_policy_write_permissions(asn: ASN, client: str, vlan: Optional[str]) -> bool:
        return ClientRegistry._ases[asn].is_primary_client(client, vlan)

    @staticmethod
    def send_link_update(asn: ASN, update: peering_pb2.LinkUpdate):
        """Send link updates to all clients of the AS."""
        connections = ClientRegistry._ases.get(asn)
        if connections:
            for conn in connections.get_connections():
                conn.send_link_update(update)

    @staticmethod
    def send_async_error(asn: ASN, error: peering_pb2.AsyncError):
        """Send an asynchronous error report to all clients of the AS."""
        connections = ClientRegistry._ases.get(asn)
        if connections:
            for conn in connections.get_connections():
                conn.send_async_error(error)
