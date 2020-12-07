import ipaddress

from django.db.models import Q
from django.test import TestCase

from peering_coord.models import *
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

def _add_org_policy(vlan, asys, peer_org, accept):
    """Add an organization peering policy and apply it.

    :returns: The newly created policy instance.
    """
    policy = OrgPeerPolicy.objects.create(vlan=vlan, asys=asys, peer_org=peer_org, accept=accept)
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

def _delete_policy(policy):
    """Delete a peering policy and apply the changes."""
    policy.delete()
    update_accepted_peers(policy.vlan, policy.asys)
    update_links(policy.vlan, policy.asys)

def _link_exists(test_case, vlan, link_type, as_a, as_b):
    """Check whether a link between `as_a` and `as_b` exists in the given VLAN.

    :param test_case: Test case running the check.
    :param link_type: Expected link type.
    :returns: True, if a link exists, False if not.
    """
    links = Link.objects.filter(
        Q(vlan=vlan) & (Q(as_a=as_a, as_b=as_b) | Q(as_a=as_b, as_b=as_a)))

    # Should never have multiple links between the same two ASes.
    test_case.assertLessEqual(len(links), 1)

    # Make sure the link type is as expected.
    if len(links) > 0:
        test_case.assertEqual(links[0].link_type, link_type)

    return len(links) > 0


class PeeringPoliciesTest(TestCase):
    """Tests the creation/deletion of links according to peering policies."""

    @classmethod
    def setUpTestData(cls):
        # VLANs
        cls.vlan = [
            VLAN.objects.create(
                name="Production", ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
            VLAN.objects.create(
                name="Testing", ip_network=ipaddress.IPv4Network("10.1.0.0/16")),
        ]

        # Organizations
        cls.org = [
            Organization.objects.create(name="Organization 1", contact=""),
            Organization.objects.create(name="Organization 2", contact=""),
            Organization.objects.create(name="Organization 3", contact=""),
            Organization.objects.create(name="Organization 4", contact=""),
        ]

        # ISDs
        cls.isd = [
            ISD.objects.create(isd_id=1, label="Region 1"),
            ISD.objects.create(isd_id=2, label="Region 2"),
            ISD.objects.create(isd_id=3, label="Region 3"),
        ]

        # ASes
        cls.asys = [
            AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:0"), is_core=True, owner=cls.org[0]),
            AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:1"), is_core=False, owner=cls.org[0]),
            AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:2"), is_core=True, owner=cls.org[1]),
            AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:3"), is_core=False, owner=cls.org[2]),
            AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:4"), is_core=False, owner=cls.org[2]),
            AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:5"), is_core=False, owner=cls.org[3]),
        ]

        # VLAN Membership
        for asys, ip in zip(cls.asys, cls.vlan[0].ip_network.hosts()):
            VlanMembership.objects.create(vlan=cls.vlan[0], asys=asys, public_ip=ip,
                first_br_port=50000, last_br_port=51000)
            VlanMembership.objects.create(vlan=cls.vlan[1], asys=asys, public_ip=ip,
                first_br_port=50000, last_br_port=51000)

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
        self.assertTrue(_link_exists(self, self.vlan[0], Link.CORE, self.asys[0], self.asys[2]))

        # Accept 1-ff00:0:3 -> 1-ff00:0:1
        _add_as_policy(self.vlan[0], self.asys[3], self.asys[1], True)
        self.assertEqual(self.asys[3].accept.count(), 1)
        self.assertEqual(self.asys[3].accept.first(), self.asys[1])
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_link_exists(self, self.vlan[0], Link.CORE, self.asys[0], self.asys[2]))

        # Remove (Accept 1-ff00:0:0 -> 1-ff00:0:2)
        _delete_policy(allow_0_to_2)
        self.assertEqual(self.asys[0].accept.count(), 0)
        self.assertEqual(Link.objects.count(), 0)

    def test_vlan_isolation(self):
        """Make sure policies are separeted according to VLAN."""
        # VLAN 0: Accept 1-ff00:0:0 -> 1-ff00:0:2
        _add_as_policy(self.vlan[0], self.asys[0], self.asys[2], True)
        # VLAN 1: Accept 1-ff00:0:2 -> 1-ff00:0:0
        _add_as_policy(self.vlan[1], self.asys[2], self.asys[0], True)
        self.assertEqual(Link.objects.count(), 0)
        # VLAN 0: Accept 1-ff00:0:2 -> 1-ff00:0:0
        _add_as_policy(self.vlan[0], self.asys[2], self.asys[0], True)
        # VLAN 1: Reject 1-ff00:0:0 -> 1-ff00:0:2
        _add_as_policy(self.vlan[1], self.asys[0], self.asys[2], False)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_link_exists(self, self.vlan[0], Link.CORE, self.asys[0], self.asys[2]))

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
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))

        # Accept 2-ff00:0:4 -> ISD 1
        _add_isd_policy(vlan, self.asys[4], self.isd[0], True)
        self.assertEqual(self.asys[4].accept.count(), 4)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))

        # Accept 1-ff00:0:1 -> ISD 2
        _add_isd_policy(vlan, self.asys[1], self.isd[1], True)
        self.assertEqual(self.asys[1].accept.count(), 5)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))

        # Accept 1-ff00:0:3 -> ISD 2
        _add_isd_policy(vlan, self.asys[3], self.isd[1], True)
        self.assertEqual(self.asys[3].accept.count(), 5)
        self.assertEqual(Link.objects.count(), 3)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[3], self.asys[4]))

        # Reject 1-ff00:0:3 -> 2-ff00:0:4 (AS reject has precedence over ISD accept)
        _add_as_policy(vlan, self.asys[3], self.asys[4], False)
        self.assertEqual(self.asys[3].accept.count(), 4)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))

        # Remove (Accept 1-ff00:0:1 -> ISD 1)
        _delete_policy(allow_1_to_isd1)
        self.assertEqual(self.asys[1].accept.count(), 2)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))

        # Reject 1-ff00:0:1 -> ISD 1
        _add_isd_policy(vlan, self.asys[1], self.isd[0], False)
        self.assertEqual(self.asys[1].accept.count(), 2)
        self.assertEqual(Link.objects.count(), 1)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))

        # Accept 1-ff00:0:1 -> 1-ff00:0:3 (AS accept has precedence over ISD reject)
        _add_as_policy(vlan, self.asys[1], self.asys[3], True)
        self.assertEqual(self.asys[1].accept.count(), 3)
        self.assertEqual(Link.objects.count(), 2)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[3]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))

    def test_priority(self):
        """Test priority of AS-level over organization-level over ISD-level policies."""
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
        self.assertEqual(self.asys[1].links.count(), 2)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[4]))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[5]))

        # Reject 1-ff00:0:1 -> Organization 3
        _add_org_policy(vlan, self.asys[1], self.org[2], False)
        self.assertEqual(self.asys[1].accept.count(), 1)
        self.assertEqual(self.asys[1].links.count(), 1)
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys[1], self.asys[5]))

        # Reject 1-ff00:0:1 -> 2-ff00:0:5
        _add_as_policy(vlan, self.asys[1], self.asys[5], False)
        self.assertEqual(self.asys[1].accept.count(), 0)
        self.assertEqual(self.asys[1].links.count(), 0)


class ExampleTopologyTest(TestCase):
    """Test a small example topology."""
    @classmethod
    def setUpTestData(cls):
        # VLANs
        cls.vlan = [
            VLAN.objects.create(
                name="Production", ip_network=ipaddress.IPv4Network("10.0.0.0/16")),
        ]

        # Organizations
        cls.org = [
            Organization.objects.create(name="Organization 1", contact=""),
            Organization.objects.create(name="Organization 2", contact=""),
        ]

        # ISDs
        cls.isd = [
            ISD.objects.create(isd_id=1, label="Region 1"),
            ISD.objects.create(isd_id=2, label="Region 2"),
        ]

        # ASes
        cls.asys = {
            'A': AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:0"), is_core=True, owner=cls.org[0]),
            'B': AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:1"), is_core=True, owner=cls.org[0]),
            'C': AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:2"), is_core=True, owner=cls.org[0]),
            'D': AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:3"), is_core=False, owner=cls.org[0]),
            'E': AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:4"), is_core=False, owner=cls.org[0]),
            'F': AS.objects.create(isd=cls.isd[0], asn=ASN("ff00:0:5"), is_core=False, owner=cls.org[1]),
            'G': AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:6"), is_core=False, owner=cls.org[1]),
            'H': AS.objects.create(isd=cls.isd[1], asn=ASN("ff00:0:7"), is_core=False, owner=cls.org[0]),
        }

        # VLAN Membership
        for asys, ip in zip(cls.asys.values(), cls.vlan[0].ip_network.hosts()):
            VlanMembership.objects.create(vlan=cls.vlan[0], asys=asys, public_ip=ip,
                first_br_port=50000, last_br_port=51000)

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

        # Organization-level policies
        # F accept [F, G]
        OrgPeerPolicy.objects.create(vlan=vlan, asys=self.asys['F'], peer_org=self.org[1], accept=True)
        # G accept [F, G]
        OrgPeerPolicy.objects.create(vlan=vlan, asys=self.asys['G'], peer_org=self.org[1], accept=True)

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
        self.assertTrue(_link_exists(self, vlan, Link.CORE, self.asys['B'], self.asys['C']))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys['D'], self.asys['E']))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys['F'], self.asys['G']))
        self.assertTrue(_link_exists(self, vlan, Link.PEERING, self.asys['G'], self.asys['H']))
