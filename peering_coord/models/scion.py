"""Database models of SCION objects"""

import itertools
from typing import Optional

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from peering_coord.custom_fields import AsnField, L4PortField
from peering_coord.models.ixp import Interface, Owner, VLAN, Link
from peering_coord.models.limits import MAX_LONG_NAME_LENGTH


class ISD(models.Model):
    """Represents a SCION isolation domain."""
    isd_id = models.PositiveIntegerField(
        verbose_name="ID",
        help_text="Integer identifying the ISD.",
        primary_key=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2**16-1)
        ]
    )
    name = models.CharField(
        help_text="A human-readable name for the ISD.",
        max_length=MAX_LONG_NAME_LENGTH
    )

    class Meta:
        verbose_name = "ISD"
        verbose_name_plural = "ISDs"

    def __str__(self):
        return "ISD %d (%s)" % (self.isd_id, self.name)


class AS(models.Model):
    """Represents a SCION AS."""
    asn = AsnField(
        verbose_name="ASN",
        help_text="AS number",
        unique=True
    )
    isd = models.ForeignKey(
        ISD,
        verbose_name="ISD",
        help_text="Every AS is part of a single ISD.",
        related_name="ases",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=MAX_LONG_NAME_LENGTH)
    owner = models.ForeignKey(
        Owner,
        help_text="The entity owning the AS.",
        related_name="ases",
        on_delete=models.CASCADE
    )
    is_core = models.BooleanField(
        verbose_name="Is Core AS",
        help_text="Whether the AS is port of the ISD core."
    )
    accept = models.ManyToManyField(
        "self",
        symmetrical=False,
        through="AcceptedPeer"
    )

    class Meta:
        verbose_name = "AS"
        verbose_name_plural = "ASes"

    def __str__(self):
        return "AS %d-%s (%s)" % (self.isd.isd_id, str(self.asn), self.name)

    def fmt_vlan_list(self):
        """Returns a formatted list of VLANs the AS is connected to for the admin interface."""
        return ", ".join(vlan.name for vlan in self.get_connected_vlans())
    fmt_vlan_list.short_description = "VLANs"

    def is_connected_to_vlan(self, vlan: VLAN) -> bool:
        """Check wheather there is an interface between this AS and the given vlan."""
        for pc in self.peering_clients.all():
            if vlan in pc.get_connected_vlans():
                return True
        return False

    def get_connected_vlans(self):
        """Returns a list of VLANs this AS is connected to."""
        return itertools.chain.from_iterable(
            pc.get_connected_vlans() for pc in self.peering_clients.all())

    def query_interfaces(self):
        """Returns a queryset containing all interfaces of this AS:"""
        return Interface.objects.filter(peering_client__in=self.peering_clients.all())

    def query_connected_peers(self, vlan: Optional[VLAN] = None):
        """Returns a queryset containing the IDs of all connected peers.

        :param vlan: Output is restricted to this VLAN.
        """
        interfaces = self.query_interfaces()
        if vlan:
            interfaces = interfaces.filter(vlan=vlan)
        peers1 = Link.objects.filter(interface_a__in=interfaces).values_list(
            'interface_b__peering_client__asys')
        peers2 = Link.objects.filter(interface_b__in=interfaces).values_list(
            'interface_a__peering_client__asys')
        return peers1.union(peers2)

    def query_mutually_accepted_peers(self, vlan: VLAN):
        """Returns a queryset containing the IDs of all mutually accepted peers.

        :param vlan: Output is restricted to this vlan.
        """
        my_acpted = AcceptedPeer.objects.filter(vlan=vlan, asys=self).values_list('peer')
        mutually_acpted= AcceptedPeer.objects.filter(vlan=vlan, asys__in=my_acpted.all(), peer=self)
        return mutually_acpted.values_list('asys')


class AcceptedPeer(models.Model):
    """Recursive relation between ASes marking the other ASes an AS would accept peering with."""
    asys = models.ForeignKey(AS, related_name="+", on_delete=models.CASCADE)
    peer = models.ForeignKey(AS, related_name="+", on_delete=models.CASCADE)
    vlan = models.ForeignKey(
        "VLAN",
        verbose_name="VLAN",
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['asys', 'peer', 'vlan'], name="unique_peer_relation")
        ]

    def __str__(self):
        return "AcceptedPeer %s -> %s (%s)" % (self.asys, self.peer, self.vlan)
