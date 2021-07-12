import ipaddress

from django.db.models import Count, Sum, Q
from django.test import TestCase

from peering_coord.models.ixp import Owner, VLAN, PeeringClient, Interface
from peering_coord.models.scion import ISD, AS, Link
from peering_coord.models.policies import (DefaultPolicy, AsPeerPolicy, DefaultPolicy,
    IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.peering_policy import update_accepted_peers, update_links
from peering_coord.scion_addr import ASN


def _add_as_policy(vlan, asys, peer_as, accept):
    """Add an AS peering policy and apply it.

    :returns: The newly created policy instance.
    """
    policy = AsPeerPolicy.objects.create(vlan=vlan, asys=asys, peer_as=peer_as, accept=accept)
    update_accepted_peers(vlan, asys)
    update_links(vlan, asys)
    return policy

def _add_owner_policy(vlan, asys, peer_owner, accept):
    """Add an Owner peering policy and apply it.

    :returns: The newly created policy instance.
    """
    policy = OwnerPeerPolicy.objects.create(vlan=vlan, asys=asys, peer_owner=peer_owner, accept=accept)
    update_accepted_peers(vlan, asys)
    update_links(vlan, asys)
    return policy

def _add_isd_policy(vlan, asys, peer_isd, accept):
    """Add an ISD peering policy and apply it.

    :returns: The newly created policy instance.
    """
    policy = IsdPeerPolicy.objects.create(vlan=vlan, asys=asys, peer_isd=peer_isd, accept=accept)
    update_accepted_peers(vlan, asys)
    update_links(vlan, asys)
    return policy

def _add_default_policy(vlan, asys, accept):
    """Add a default policy and apply it.

    :returns: The newly created policy instance.
    """
    policy = DefaultPolicy.objects.create(vlan=vlan, asys=asys, accept=accept)
    update_accepted_peers(vlan, asys)
    update_links(vlan, asys)
    return policy

def _delete_policy(policy):
    """Delete a peering policy and apply the changes."""
    policy.delete()
    update_accepted_peers(policy.vlan, policy.asys)
    update_links(policy.vlan, policy.asys)

def _count_links(asys):
    """Count the total number of links of AS `asys`."""
    query = asys.query_interfaces().annotate(num_links=Count('links')).aggregate(Sum('num_links'))
    return query.get('num_links__sum')

def _link_exists(test_case, vlan, link_type, interface_a, interface_b):
    """Check whether there is a link between the given interfaces.

    :param test_case: Test case running the check.
    :param vlan: VLAN to check for links.
    :param link_type: Expected link type.
    :returns: True, if a link exists, False if not.
    """
    dir1 = Link.objects.filter(interface_a=interface_a, interface_b=interface_b).exists()
    dir2 = Link.objects.filter(interface_a=interface_b, interface_b=interface_a).exists()

    test_case.assertFalse(dir1 and dir2, "Link exists in both directions")
    return dir1 or dir2

def _links_exists(test_case, vlan, link_type, as_a, as_b):
    """Check whether the interfaces of `as_a` and `as_b` are linked in the given VLAN.

    :param test_case: Test case running the check.
    :param vlan: VLAN to check for links.
    :param link_type: Expected link type.
    :returns: True, if a link exists, False if not.
    """
    links = Link.objects.filter(
        Q(interface_a__vlan=vlan)
        & (Q(interface_a__peering_client__asys=as_a, interface_b__peering_client__asys=as_b)
         | Q(interface_a__peering_client__asys=as_b, interface_b__peering_client__asys=as_a)))

    # There should be links from every interface of AS A to every interface of AS B for interfaces
    # in the same vlan.
    interface_count_a = as_a.query_interfaces().filter(vlan=vlan).count()
    interface_count_b = as_b.query_interfaces().filter(vlan=vlan).count()
    test_case.assertLessEqual(len(links), interface_count_a * interface_count_b)

    # Make sure the link type is as expected.
    for link in links:
        test_case.assertEqual(link.link_type, link_type)

    return len(links) > 0


class PeeringPoliciesTest(TestCase):
    """Tests the creation/deletion of links according to peering policies."""

    @classmethod
    def setUpTestData(cls):
        # VLANs
        cls.vlan = [
            VLAN.objects.create(
                name="prod", long_name="Production",
                ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
            VLAN.objects.create(
                name="test", long_name="Testing",
                ip_network=ipaddress.IPv4Network("10.1.0.0/16")),
        ]

        # Owners
        cls.owner = [
            Owner.objects.create(name="owner1", long_name="Owner 1", contact=""),
            Owner.objects.create(name="owner2", long_name="Owner 2", contact=""),
            Owner.objects.create(name="owner3", long_name="Owner 3", contact=""),
            Owner.objects.create(name="owner4", long_name="Owner 4", contact=""),
        ]

        # ISDs
        cls.isd = [
            ISD.objects.create(isd_id=1, name="Region 1"),
            ISD.objects.create(isd_id=2, name="Region 2"),
            ISD.objects.create(isd_id=3, name="Region 3"),
        ]

        # ASes
        cls.asys = [
            AS.objects.create(asn=ASN("ff00:0:0"), isd=cls.isd[0], name="AS 0", owner=cls.owner[0], is_core=True),
            AS.objects.create(asn=ASN("ff00:0:1"), isd=cls.isd[0], name="AS 1", owner=cls.owner[0], is_core=False),
            AS.objects.create(asn=ASN("ff00:0:2"), isd=cls.isd[0], name="AS 2", owner=cls.owner[1], is_core=True),
            AS.objects.create(asn=ASN("ff00:0:3"), isd=cls.isd[0], name="AS 3", owner=cls.owner[2], is_core=False),
            AS.objects.create(asn=ASN("ff00:0:4"), isd=cls.isd[1], name="AS 4", owner=cls.owner[2], is_core=False),
            AS.objects.create(asn=ASN("ff00:0:5"), isd=cls.isd[1], name="AS 5", owner=cls.owner[3], is_core=False),
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

    def test_as_policies(self):
        """Test AS-level peering policies."""
        # Accept 1-ff00:0:0 -> 1-ff00:0:2
        allow_0_to_2 = _add_as_policy(self.vlan[0], self.asys[0], self.asys[2], True)
        self.assertEqual(self.asys[0].accept.count(), 1)
        self.assertEqual(self.asys[0].accept.first(), self.asys[2])
        self.assertEqual(Link.objects.count(), 0)

        # Reject 1-ff00:0:1 -> 1-ff00:0:3
        _add_as_policy(self.vlan[0], self.asys[1], self.asys[3], False)
        self.assertEqual(self.asys[1].accept.count(), 0)
        self.assertEqual(Link.objects.count(), 0)

        # Accept 1-ff00:0:2 -> 1-ff00:0:0
        _add_as_policy(self.vlan[0], self.asys[2], self.asys[0], True)
        self.assertEqual(self.asys[2].accept.count(), 1)
        self.assertEqual(self.asys[2].accept.first(), self.asys[0])
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, self.vlan[0], Link.Type.CORE, self.asys[0], self.asys[2]))

        # Accept 1-ff00:0:3 -> 1-ff00:0:1
        _add_as_policy(self.vlan[0], self.asys[3], self.asys[1], True)
        self.assertEqual(self.asys[3].accept.count(), 1)
        self.assertEqual(self.asys[3].accept.first(), self.asys[1])
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, self.vlan[0], Link.Type.CORE, self.asys[0], self.asys[2]))

        # Remove (Accept 1-ff00:0:0 -> 1-ff00:0:2)
        _delete_policy(allow_0_to_2)
        self.assertEqual(self.asys[0].accept.count(), 0)
        self.assertEqual(Link.objects.count(), 0)

    def test_default_policy(self):
        """Test the default (accept all) policy."""
        # 1-ff00:0:0 -> Accept all
        # 1-ff00:0:1 -> Accept all
        # 1-ff00:0:2 -> Accept all
        # 1-ff00:0:4 -> Accept all
        _add_default_policy(self.vlan[0], self.asys[0], True)
        self.assertEqual(self.asys[0].accept.count(), 5)
        _add_default_policy(self.vlan[0], self.asys[1], True)
        self.assertEqual(self.asys[0].accept.count(), 5)
        _add_default_policy(self.vlan[0], self.asys[2], True)
        self.assertEqual(self.asys[0].accept.count(), 5)
        _add_default_policy(self.vlan[0], self.asys[4], True)
        self.assertEqual(self.asys[0].accept.count(), 5)
        self.assertEqual(Link.objects.count(), 4)

        # Reject 1-ff00:0:0 -> ISD 2
        _add_isd_policy(self.vlan[0], self.asys[0], self.isd[1], False)
        self.assertEqual(self.asys[0].accept.count(), 3)
        self.assertEqual(Link.objects.count(), 4)

        # Reject 1-ff00:0:0 -> Owner 2
        _add_owner_policy(self.vlan[0], self.asys[0], self.owner[1], False)
        self.assertEqual(self.asys[0].accept.count(), 2)
        self.assertEqual(Link.objects.count(), 3)

        # Reject 1-ff00:0:0 -> 1-ff00:0:1
        _add_as_policy(self.vlan[0], self.asys[0], self.asys[1], False)
        self.assertEqual(self.asys[0].accept.count(), 1)
        self.assertEqual(Link.objects.count(), 2)

    def test_vlan_isolation(self):
        """Make sure policies are separeted according to VLAN."""
        # VLAN 0: Accept 1-ff00:0:0 -> 1-ff00:0:2
        _add_as_policy(self.vlan[0], self.asys[0], self.asys[2], True)
        # VLAN 1: Accept 1-ff00:0:2 -> 1-ff00:0:0
        _add_as_policy(self.vlan[1], self.asys[2], self.asys[0], True)

        # VLAN 0: Accept 1-ff00:0:2 -> 1-ff00:0:0
        _add_as_policy(self.vlan[0], self.asys[2], self.asys[0], True)
        # VLAN 1: Reject 1-ff00:0:0 -> 1-ff00:0:2
        _add_as_policy(self.vlan[1], self.asys[0], self.asys[2], False)

        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, self.vlan[0], Link.Type.CORE, self.asys[0], self.asys[2]))

    def test_isd_policies(self):
        """Test ISD peering policies and their interaction with AS policies."""
        vlan = self.vlan[0]

        # Accept 1-ff00:0:1 -> ISD 1
        allow_1_to_isd1 = _add_isd_policy(vlan, self.asys[1], self.isd[0], True)
        self.assertEqual(self.asys[1].accept.count(), 3)
        self.assertEqual(Link.objects.count(), 0)

        # Accept 1-ff00:0:3 -> ISD 1
        _add_isd_policy(vlan, self.asys[3], self.isd[0], True)
        self.assertEqual(self.asys[1].accept.count(), 3)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))

        # Accept 2-ff00:0:4 -> ISD 1
        _add_isd_policy(vlan, self.asys[4], self.isd[0], True)
        self.assertEqual(self.asys[4].accept.count(), 4)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))

        # Accept 1-ff00:0:1 -> ISD 2
        _add_isd_policy(vlan, self.asys[1], self.isd[1], True)
        self.assertEqual(self.asys[1].accept.count(), 5)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))

        # Accept 1-ff00:0:3 -> ISD 2
        _add_isd_policy(vlan, self.asys[3], self.isd[1], True)
        self.assertEqual(self.asys[3].accept.count(), 5)
        self.assertEqual(Link.objects.count(), 3)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[3], self.asys[4]))

        # Reject 1-ff00:0:3 -> 2-ff00:0:4 (AS reject has precedence over ISD accept)
        _add_as_policy(vlan, self.asys[3], self.asys[4], False)
        self.assertEqual(self.asys[3].accept.count(), 4)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))

        # Remove (Accept 1-ff00:0:1 -> ISD 1)
        _delete_policy(allow_1_to_isd1)
        self.assertEqual(self.asys[1].accept.count(), 2)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))

        # Reject 1-ff00:0:1 -> ISD 1
        _add_isd_policy(vlan, self.asys[1], self.isd[0], False)
        self.assertEqual(self.asys[1].accept.count(), 2)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))

        # Accept 1-ff00:0:1 -> 1-ff00:0:3 (AS accept has precedence over ISD reject)
        _add_as_policy(vlan, self.asys[1], self.asys[3], True)
        self.assertEqual(self.asys[1].accept.count(), 3)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))

    def test_priority(self):
        """Test priority of AS-level over Owner-level over ISD-level policies."""
        vlan = self.vlan[0]

        # Accept 2-ff00:0:4 -> 1-ff00:0:1
        # Accept 2-ff00:0:5 -> 1-ff00:0:1
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys[4], peer_as=self.asys[1], accept=True)
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys[5], peer_as=self.asys[1], accept=True)
        update_accepted_peers(vlan, self.asys[4])
        update_accepted_peers(vlan, self.asys[5])
        # Accept 1-ff00:0:1 -> ISD 2
        _add_isd_policy(vlan, self.asys[1], self.isd[1], True)
        self.assertEqual(self.asys[1].accept.count(), 2)
        self.assertEqual(_count_links(self.asys[1]), 2)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[4]))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[5]))

        # Reject 1-ff00:0:1 -> Owner 3
        _add_owner_policy(vlan, self.asys[1], self.owner[2], False)
        self.assertEqual(self.asys[1].accept.count(), 1)
        self.assertEqual(_count_links(self.asys[1]), 1)
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys[1], self.asys[5]))

        # Reject 1-ff00:0:1 -> 2-ff00:0:5
        _add_as_policy(vlan, self.asys[1], self.asys[5], False)
        self.assertEqual(self.asys[1].accept.count(), 0)
        self.assertEqual(_count_links(self.asys[1]), 0)


class ExampleTopologyTest(TestCase):
    """Test a small example topology."""
    @classmethod
    def setUpTestData(cls):
        # VLANs
        cls.vlan = [
            VLAN.objects.create(name="prod", long_name="Production",
                ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
        ]

        # Owners
        cls.owner = [
            Owner.objects.create(name="owner1", long_name="Owner 1", contact=""),
            Owner.objects.create(name="owner2", long_name="Owner 2", contact=""),
        ]

        # ISDs
        cls.isd = [
            ISD.objects.create(isd_id=1, name="Region 1"),
            ISD.objects.create(isd_id=2, name="Region 2"),
        ]

        # ASes
        cls.asys = {
            'A': AS.objects.create(asn=ASN("ff00:0:0"), isd=cls.isd[0], name="AS 0", owner=cls.owner[0], is_core=True),
            'B': AS.objects.create(asn=ASN("ff00:0:1"), isd=cls.isd[1], name="AS 1", owner=cls.owner[0], is_core=True),
            'C': AS.objects.create(asn=ASN("ff00:0:2"), isd=cls.isd[0], name="AS 2", owner=cls.owner[0], is_core=True),
            'D': AS.objects.create(asn=ASN("ff00:0:3"), isd=cls.isd[1], name="AS 3", owner=cls.owner[0], is_core=False),
            'E': AS.objects.create(asn=ASN("ff00:0:4"), isd=cls.isd[1], name="AS 4", owner=cls.owner[0], is_core=False),
            'F': AS.objects.create(asn=ASN("ff00:0:5"), isd=cls.isd[0], name="AS 5", owner=cls.owner[1], is_core=False),
            'G': AS.objects.create(asn=ASN("ff00:0:6"), isd=cls.isd[1], name="AS 6", owner=cls.owner[1], is_core=False),
            'H': AS.objects.create(asn=ASN("ff00:0:7"), isd=cls.isd[1], name="AS 7", owner=cls.owner[0], is_core=False),
        }

        # Peering Clients
        clients = []
        for asys in cls.asys.values():
            clients.append(PeeringClient.objects.create(asys=asys, name="default"))

        # Interfaces
        for vlan in cls.vlan:
            for daemon, ip in zip(clients, cls.vlan[0].ip_network.hosts()):
                Interface.objects.create(peering_client=daemon, vlan=vlan, public_ip=ip,
                    first_port=50000, last_port=51000)

    def test_example(self):
        vlan = self.vlan[0]

        # AS-level policies
        # B accept C
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['B'], peer_as=self.asys['C'], accept=True)
        # C accept B, D
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['C'], peer_as=self.asys['B'], accept=True)
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['C'], peer_as=self.asys['D'], accept=True)
        # D accept C, E
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['D'], peer_as=self.asys['C'], accept=True)
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['D'], peer_as=self.asys['E'], accept=True)
        # E reject G, H
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['E'], peer_as=self.asys['G'], accept=False)
        AsPeerPolicy.objects.create(vlan=vlan, asys=self.asys['E'], peer_as=self.asys['H'], accept=False)

        # Owner-level policies
        # F accept [F, G]
        OwnerPeerPolicy.objects.create(vlan=vlan, asys=self.asys['F'], peer_owner=self.owner[1], accept=True)
        # G accept [F, G]
        OwnerPeerPolicy.objects.create(vlan=vlan, asys=self.asys['G'], peer_owner=self.owner[1], accept=True)

        # ISD-level policies
        # E accept ISD 2
        IsdPeerPolicy.objects.create(vlan=vlan, asys=self.asys['E'], peer_isd=self.isd[1], accept=True)
        # G accept ISD 2
        IsdPeerPolicy.objects.create(vlan=vlan, asys=self.asys['G'], peer_isd=self.isd[1], accept=True)
        # H accept ISD 2
        IsdPeerPolicy.objects.create(vlan=vlan, asys=self.asys['H'], peer_isd=self.isd[1], accept=True)

        for asys in self.asys.values():
            update_accepted_peers(vlan, asys)
        for asys in self.asys.values():
            update_links(vlan, asys)

        self.assertEqual(Link.objects.count(), 4)
        self.assertTrue(_links_exists(self, vlan, Link.Type.CORE, self.asys['B'], self.asys['C']))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys['D'], self.asys['E']))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys['F'], self.asys['G']))
        self.assertTrue(_links_exists(self, vlan, Link.Type.PEERING, self.asys['G'], self.asys['H']))


class MultiClientTest(TestCase):
    """Test multiple peering clients per AS and multiple interfaces per client."""
    @classmethod
    def setUpTestData(cls):
        # VLANs
        cls.vlan = {
            'VLAN1': VLAN.objects.create(name="vlan1", long_name="VLAN 1",
                ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
            'VLAN2': VLAN.objects.create(name="vlan2", long_name="VLAN 2",
                ip_network=ipaddress.IPv4Network("10.1.0.0/16")),
        }

        # Owners
        cls.owner = [
            Owner.objects.create(name="owner1", long_name="Owner 1", contact=""),
            Owner.objects.create(name="owner2", long_name="Owner 2", contact=""),
        ]

        # ISDs
        cls.isd = [
            ISD.objects.create(isd_id=1, name="Region 1"),
        ]

        # ASes
        cls.asys = {
            'A': AS.objects.create(asn=ASN("ff00:0:0"), isd=cls.isd[0], name="AS A",
                owner=cls.owner[0], is_core=False),
            'B': AS.objects.create(asn=ASN("ff00:0:1"), isd=cls.isd[0], name="AS B",
                owner=cls.owner[1], is_core=False),
        }

        # Peering Clients
        cls.client = {
            'A-1': PeeringClient.objects.create(asys=cls.asys['A'], name="1"),
            'A-2': PeeringClient.objects.create(asys=cls.asys['A'], name="2"),
            'B-1': PeeringClient.objects.create(asys=cls.asys['B'], name="1"),
            'B-2': PeeringClient.objects.create(asys=cls.asys['B'], name="2"),
            'B-3': PeeringClient.objects.create(asys=cls.asys['B'], name="3")
        }

        # Interfaces
        hosts1 = cls.vlan['VLAN1'].ip_network.hosts()
        hosts2 = cls.vlan['VLAN2'].ip_network.hosts()
        cls.interface = {
            'A-1-VLAN1': Interface.objects.create(peering_client=cls.client['A-1'], vlan=cls.vlan['VLAN1'],
                public_ip=next(hosts1), first_port=50000, last_port=51000),
            'A-2-VLAN1': Interface.objects.create(peering_client=cls.client['A-2'], vlan=cls.vlan['VLAN1'],
                public_ip=next(hosts1), first_port=50000, last_port=51000),
            'A-2-VLAN2': Interface.objects.create(peering_client=cls.client['A-2'], vlan=cls.vlan['VLAN2'],
                public_ip=next(hosts2), first_port=51000, last_port=52000),
            'B-1-VLAN1': Interface.objects.create(peering_client=cls.client['B-1'], vlan=cls.vlan['VLAN1'],
                public_ip=next(hosts1), first_port=50000, last_port=51000),
            'B-2-VLAN1': Interface.objects.create(peering_client=cls.client['B-1'], vlan=cls.vlan['VLAN1'],
                public_ip=next(hosts1), first_port=51000, last_port=52000),
            'B-2-VLAN2': Interface.objects.create(peering_client=cls.client['B-2'], vlan=cls.vlan['VLAN2'],
                public_ip=next(hosts2), first_port=50000, last_port=51000),
            'B-3-VLAN2': Interface.objects.create(peering_client=cls.client['B-2'], vlan=cls.vlan['VLAN2'],
                public_ip=next(hosts2), first_port=51000, last_port=52000),
        }

    def test_interface_connections(self):
        """Test m*n interface connections."""

        # AS A accepts AS B in VLAN 1
        # AS B accepts AS A in VLAN 1
        _add_as_policy(self.vlan['VLAN1'], self.asys['A'], self.asys['B'], True)
        _add_as_policy(self.vlan['VLAN1'], self.asys['B'], self.asys['A'], True)

        self.assertEqual(Link.objects.count(), 4)
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-1-VLAN1'], self.interface['B-1-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-1-VLAN1'], self.interface['B-2-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-2-VLAN1'], self.interface['B-1-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-2-VLAN1'], self.interface['B-2-VLAN1']))

        # AS A accepts AS B in VLAN 2
        # AS B accepts AS A in VLAN 2
        _add_as_policy(self.vlan['VLAN2'], self.asys['A'], self.asys['B'], True)
        _add_as_policy(self.vlan['VLAN2'], self.asys['B'], self.asys['A'], True)

        self.assertEqual(Link.objects.count(), 6)
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-1-VLAN1'], self.interface['B-1-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-1-VLAN1'], self.interface['B-2-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-2-VLAN1'], self.interface['B-1-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN1'], Link.Type.PEERING,
            self.interface['A-2-VLAN1'], self.interface['B-2-VLAN1']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN2'], Link.Type.PEERING,
            self.interface['A-2-VLAN2'], self.interface['B-2-VLAN2']))
        self.assertTrue(_link_exists(self, self.vlan['VLAN2'], Link.Type.PEERING,
            self.interface['A-2-VLAN2'], self.interface['B-3-VLAN2']))
