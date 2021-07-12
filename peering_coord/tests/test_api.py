import grpc
import ipaddress
from django_grpc_framework.test import RPCTestCase

from google.protobuf.empty_pb2 import Empty
from peering_coord.api import info_pb2, info_pb2_grpc, peering_pb2, peering_pb2_grpc
from peering_coord.api.authentication import ASN_HEADER_KEY
from peering_coord.api.serializers import PolicyProtoSerializer
from peering_coord.models.ixp import Owner, VLAN, PeeringClient, Interface
from peering_coord.models.scion import ISD, AS
from peering_coord.scion_addr import ASN


def _set_up_test_data(cls):
    # Owners
    cls.owner = [
        Owner.objects.create(name="owner1", long_name="Owner Name 1", contact="Contact Info A"),
        Owner.objects.create(name="owner2", long_name="Owner 2", contact="Contact Info B"),
        Owner.objects.create(name="owner3", long_name="Owner 3", contact="Contact Info C"),
    ]

    # ISDs
    cls.isd = [
        ISD.objects.create(isd_id=1, name="Region 1"),
        ISD.objects.create(isd_id=2, name="Region 2"),
    ]

    # ASes
    cls.asys = [
        AS.objects.create(
            asn=ASN("ff00:0:0"), isd=cls.isd[0], name="AS 0", owner=cls.owner[0], is_core=True),
        AS.objects.create(
            asn=ASN("ff00:0:1"), isd=cls.isd[0], name="AS 1", owner=cls.owner[0], is_core=False),
        AS.objects.create(
            asn=ASN("ff00:0:2"), isd=cls.isd[0], name="AS 2", owner=cls.owner[0], is_core=True),
        AS.objects.create(
            asn=ASN("ff00:0:3"), isd=cls.isd[0], name="AS 3", owner=cls.owner[1], is_core=False),
        AS.objects.create(
            asn=ASN("ff00:0:4"), isd=cls.isd[1], name="AS 4", owner=cls.owner[1], is_core=False),
        AS.objects.create(
            asn=ASN("ff00:0:5"), isd=cls.isd[1], name="AS 5", owner=cls.owner[1], is_core=False),
    ]

    # VLANs
    cls.vlan = [
        VLAN.objects.create(
            name="prod", long_name="Production", ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
        VLAN.objects.create(
            name="test", long_name="Testing", ip_network=ipaddress.IPv4Network("10.1.0.0/16")),
    ]

    # Peering Clients
    clients = []
    for asys in cls.asys:
        clients.append(PeeringClient.objects.create(asys=asys, name="default"))

    # Interfaces
    for vlan in cls.vlan:
        for daemon, ip in zip(clients, vlan.ip_network.hosts()):
            Interface.objects.create(peering_client=daemon, vlan=vlan, public_ip=ip,
                first_port=50000, last_port=51000)


class InfoServiveTest(RPCTestCase):
    """Test the informational API."""

    @classmethod
    def setUpTestData(cls):
        _set_up_test_data(cls)

        cls.owners = [
            info_pb2.Owner(name="owner1", long_name="Owner Name 1",
                asns=["ff00:0:0", "ff00:0:1", "ff00:0:2"]),
            info_pb2.Owner(name="owner2", long_name="Owner 2",
                asns=["ff00:0:3", "ff00:0:4", "ff00:0:5"]),
            info_pb2.Owner(name="owner3", long_name="Owner 3",
                asns=[])
        ]

    def test_get_owner(self):
        stub = info_pb2_grpc.InfoStub(self.channel)

        response = stub.GetOwner(info_pb2.GetOwnerRequest(name="owner3"))
        self.assertEqual(response, self.owners[2])

        response = stub.GetOwner(info_pb2.GetOwnerRequest(asn="ff00:0:3"))
        self.assertEqual(response, self.owners[1])

        response = stub.GetOwner(info_pb2.GetOwnerRequest(name="owner1", asn="ff00:0:0"))
        self.assertEqual(response, self.owners[0])

        with self.assertRaises(grpc.RpcError) as cm:
            response = stub.GetOwner(info_pb2.GetOwnerRequest(asn="invalid"))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

        with self.assertRaises(grpc.RpcError) as cm:
            response = stub.GetOwner(info_pb2.GetOwnerRequest(name="owner1", asn="ff00:0:4"))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_search_owner(self):
        stub = info_pb2_grpc.InfoStub(self.channel)

        response = list(stub.SearchOwner(info_pb2.SearchOwnerRequest(long_name="test")))
        self.assertEqual(len(response), 0)

        response = list(stub.SearchOwner(info_pb2.SearchOwnerRequest(long_name="name")))
        self.assertEqual(len(response), 1)
        self.assertTrue(self.owners[0] in response)

        response = list(stub.SearchOwner(info_pb2.SearchOwnerRequest(long_name="owner")))
        self.assertEqual(len(response), len(self.owners))
        for owner in self.owners:
            self.assertTrue(owner in response)


class PeeringServiceTest(RPCTestCase):
    """Test the peering API."""

    @staticmethod
    def _create(policy: peering_pb2.Policy) -> peering_pb2.Policy:
        serializer = PolicyProtoSerializer(message=policy)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return policy

    @classmethod
    def setUpTestData(cls):
        _set_up_test_data(cls)
        cls.as_polices = [
            cls._create(peering_pb2.Policy(vlan="prod", accept=False, asn="ff00:0:0", peer_asn="ff00:0:1")),
            cls._create(peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_asn="ff00:0:4")),
            cls._create(peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_asn="ff00:0:5")),
        ]
        cls.other_as_policy = cls._create(peering_pb2.Policy(
            vlan="prod", accept=True, asn="ff00:0:1", peer_asn="ff00:0:0"))

        cls.owner_policies = [
            cls._create(peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_owner="owner1")),
            cls._create(peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_owner="owner3"))
        ]

        cls.isd_policies = [
            cls._create(peering_pb2.Policy(vlan="prod", accept=False, asn="ff00:0:0", peer_isd="2"))
        ]

        cls.all_policies = cls.as_polices + cls.owner_policies + cls.isd_policies

        cls.other_vlan_policy = cls._create(peering_pb2.Policy(
            vlan="test", accept=True, asn="ff00:0:0", peer_asn="ff00:0:1"))

    def test_default_policy(self):
        stub = peering_pb2_grpc.PeeringStub(self.channel)
        call_cred = [(ASN_HEADER_KEY, "ff00:0:0")]

        # Create
        default_policy = peering_pb2.Policy(vlan="prod", asn="ff00:0:0", accept=True)
        response = stub.CreatePolicy(default_policy, metadata=call_cred)
        self.assertEqual(default_policy, response)

        # List without filter
        request = peering_pb2.ListPolicyRequest(vlan="prod")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), len(self.all_policies) + 1)
        self.assertTrue(default_policy in response)
        for policy in self.all_policies:
            self.assertTrue(policy in response)

        # List filtering for default policies
        request = peering_pb2.ListPolicyRequest(vlan="prod", peer_everyone=Empty())
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 1)
        self.assertIsNone(response[0].WhichOneof('peer'))

        # Destroy
        stub.DestroyPolicy(default_policy, metadata=call_cred)
        request = peering_pb2.ListPolicyRequest(vlan="prod", peer_everyone=Empty())
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 0)

    def test_list(self):
        stub = peering_pb2_grpc.PeeringStub(self.channel)
        call_cred = [(ASN_HEADER_KEY, "ff00:0:0")]

        response = list(stub.ListPolicies(peering_pb2.ListPolicyRequest(), metadata=call_cred))
        self.assertEqual(len(response), len(self.all_policies) + 1)
        for policy in self.all_policies:
            self.assertTrue(policy in response)
        self.assertTrue(self.other_vlan_policy in response)

        request = peering_pb2.ListPolicyRequest(vlan="prod", asn="ff00:0:0")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), len(self.all_policies))
        for policy in self.all_policies:
            self.assertTrue(policy in response)

        request = peering_pb2.ListPolicyRequest(vlan="prod", accept=False)
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 2)
        self.assertTrue(self.as_polices[0] in response)
        self.assertTrue(self.isd_policies[0] in response)

        request = peering_pb2.ListPolicyRequest(vlan="prod", accept=False, peer_asn="ff00:0:1")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 1)
        self.assertTrue(self.as_polices[0] in response)

        request = peering_pb2.ListPolicyRequest(vlan="prod", accept=False, peer_asn="ff00:0:4")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 0)

        request = peering_pb2.ListPolicyRequest(peer_owner="owner1")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 1)
        self.assertTrue(self.owner_policies[0] in response)

        request = peering_pb2.ListPolicyRequest(peer_isd="2")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 1)
        self.assertTrue(self.isd_policies[0] in response)

        request = peering_pb2.ListPolicyRequest(vlan="prod", accept=True, peer_asn="ff00:0:1")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(len(response), 0)

        with self.assertRaises(grpc.RpcError) as cm:
            request = peering_pb2.ListPolicyRequest(asn="ff00:0:1")
            response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

    def test_create_delete(self):
        stub = peering_pb2_grpc.PeeringStub(self.channel)
        call_cred = [(ASN_HEADER_KEY, "ff00:0:0")]

        # Create policy
        policy = peering_pb2.Policy(vlan="test", asn="ff00:0:0", accept=True, peer_asn="ff00:0:2")
        response = stub.CreatePolicy(policy, metadata=call_cred)
        self.assertEqual(policy, response)

        request = peering_pb2.ListPolicyRequest(vlan="test", asn="ff00:0:0", accept=True, peer_asn="ff00:0:2")
        response = list(stub.ListPolicies(request, metadata=call_cred))
        self.assertTrue(len(response), 1)
        self.assertEqual(policy, response[0])

        with self.assertRaises(grpc.RpcError) as cm:
            response = stub.CreatePolicy(policy, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.ALREADY_EXISTS)

        with self.assertRaises(grpc.RpcError) as cm:
            response = stub.CreatePolicy(self.other_as_policy, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

        with self.assertRaises(grpc.RpcError) as cm:
            request = peering_pb2.Policy(vlan="test", asn="ff00:0:0", accept=True, peer_asn="ff00:0:0")
            response = stub.CreatePolicy(request, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

        # Destroy policy
        stub.DestroyPolicy(policy, metadata=call_cred)

        request = peering_pb2.ListPolicyRequest(vlan="test", asn="ff00:0:0", accept=True, peer_asn="ff00:0:2")
        self.assertEqual(list(stub.ListPolicies(request, metadata=call_cred)), [])

        with self.assertRaises(grpc.RpcError) as cm:
            stub.DestroyPolicy(policy, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

        with self.assertRaises(grpc.RpcError) as cm:
            response = stub.DestroyPolicy(self.other_as_policy, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

        with self.assertRaises(grpc.RpcError) as cm:
            request = peering_pb2.Policy(vlan="test", asn="ff00:0:0", accept=True, peer_asn="ff00:0:0")
            response = stub.DestroyPolicy(request, metadata=call_cred)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_set(self):
        stub = peering_pb2_grpc.PeeringStub(self.channel)
        call_cred = [(ASN_HEADER_KEY, "ff00:0:0")]

        # Invalid policies with rollback
        policies = [peering_pb2.Policy(vlan="prod", accept=False, asn="ff00:0:0", peer_asn="ff00:0:0")]
        response = stub.SetPolicies(peering_pb2.SetPoliciesRequest(policies=policies), metadata=call_cred)
        self.assertEqual(list(response.rejected_policies), policies)
        self.assertEqual(len(response.rejected_policies), len(response.errors))

        response = list(stub.ListPolicies(peering_pb2.ListPolicyRequest(), metadata=call_cred))
        self.assertEqual(len(response), len(self.all_policies) + 1)
        for policy in self.all_policies:
            self.assertTrue(policy in response)
        self.assertTrue(self.other_vlan_policy in response)

        # Delete all policies in one VLAN
        request = peering_pb2.SetPoliciesRequest(policies=[], vlan="test")
        response = stub.SetPolicies(request, metadata=call_cred)
        self.assertEqual(len(response.rejected_policies), 0)
        self.assertEqual(len(response.rejected_policies), 0)

        response = list(stub.ListPolicies(peering_pb2.ListPolicyRequest(vlan="prod"), metadata=call_cred))
        self.assertEqual(len(response), len(self.all_policies))
        response = list(stub.ListPolicies(peering_pb2.ListPolicyRequest(vlan="test"), metadata=call_cred))
        self.assertEqual(len(response), 0)

        # Replace some policies despite errors
        policies = [
            peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_asn="ff00:0:0"),
            peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_asn="ff00:0:1"),
            peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:0", peer_asn="ff00:0:1")]
        request = peering_pb2.SetPoliciesRequest(policies=policies, continue_on_error=True)
        response = stub.SetPolicies(request, metadata=call_cred)
        rejected = list(response.rejected_policies)
        self.assertEqual(len(rejected), 2)
        self.assertTrue(policies[0] in rejected)
        self.assertTrue(policies[2] in rejected)

        response = list(stub.ListPolicies(peering_pb2.ListPolicyRequest(vlan="prod"), metadata=call_cred))
        self.assertEqual(len(response), 1)
        self.assertTrue(policies[1] in response)

        # Permission error
        policies = [peering_pb2.Policy(vlan="prod", accept=True, asn="ff00:0:1", peer_asn="ff00:0:0")]
        request = peering_pb2.SetPoliciesRequest(policies=policies)
        response = stub.SetPolicies(request, metadata=call_cred)
        self.assertEqual(list(response.rejected_policies), policies)
        self.assertEqual(len(response.errors), 1)
