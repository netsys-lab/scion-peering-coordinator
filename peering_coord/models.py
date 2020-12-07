import ipaddress
import itertools

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from peering_coord.custom_fields import AsnField, IpAddressField, IpNetworkField, L4PortField


#################
### DB Limits ###
#################

MAX_ORGANIZATION_NAME_LENGTH = 128
MAX_ISD_LABEL_LENGTH = 64
MAX_AS_LABEL_LENGTH = 64
MAX_VLAN_NAME_LEN = 64


####################
### Organization ###
####################

class Organization(models.Model):
    """An organization owning one or more SCION ASes."""
    name = models.CharField(
        max_length=MAX_ORGANIZATION_NAME_LENGTH,
        unique=True
    )
    contact = models.TextField()

    def __str__(self):
        return self.name


######################
### SCION Concepts ###
######################

class ISD(models.Model):
    """SCION Isolation Domain"""
    isd_id = models.PositiveIntegerField(
        primary_key=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2**16-1)
        ],
        verbose_name="ID"
    )
    label = models.CharField(max_length=MAX_ISD_LABEL_LENGTH, null=True, blank=True)

    class Meta:
        verbose_name = "ISD"
        verbose_name_plural = "ISDs"

    def __str__(self):
        if self.label is None:
            return "ISD %d" % self.isd_id
        else:
            return "ISD %d (%s)" % (self.isd_id, self.label)


class AS(models.Model):
    """SCION Autonomous System"""
    asn = AsnField(
        verbose_name="ASN",
        unique=True
    )
    isd = models.ForeignKey(
        ISD,
        verbose_name="ISD",
        related_name="ases",
        on_delete=models.CASCADE
    )
    owner = models.ForeignKey(
        Organization,
        related_name="ases",
        on_delete=models.CASCADE
    )
    is_core = models.BooleanField(
        verbose_name="Is Core AS"
    )
    label = models.CharField(
        max_length=MAX_AS_LABEL_LENGTH,
        null=True,
        blank=True)
    accept = models.ManyToManyField(
        "self",
        symmetrical=False,
        through="AcceptedPeers"
    )
    links = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="+",
        through="Link"
    )

    class Meta:
        verbose_name = "AS"
        verbose_name_plural = "ASes"

    def __str__(self):
        if self.label is None:
            return "%d-%s" % (self.isd.isd_id, self.asn)
        else:
            return "%d-%s (%s)" % (self.isd.isd_id, str(self.asn), self.label)


class AcceptedPeers(models.Model):
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
        return "%s -> %s (%s)" % (self.asys, self.peer, self.vlan)


####################
### IXP Concepts ###
####################

class VLAN(models.Model):
    """Represents a VPLS peering LAN. Every VLAN has its own participants, peering policies, and
    links.
    """
    name = models.CharField(
        max_length=MAX_VLAN_NAME_LEN,
        unique=True
    )
    ip_network = IpNetworkField(
        verbose_name="IP Network"
    )
    members = models.ManyToManyField(
        AS,
        related_name="vlans",
        through="VlanMembership"
    )

    class Meta:
        verbose_name = "VLAN"
        verbose_name_plural = "VLANs"

    def __str__(self):
        return self.name

    class AddressExhaustion(Exception):
        def __init__(self):
            super().__init__("VLAN IP addresses exhausted.")

    def get_unused_ip(self):
        """Get an unused IP address from the VLAN's subnet.

        :raises AddressExhaustion: There are no free addresses available anymore.
        """
        ips_in_use = VlanMembership.objects.filter(vlan=self).values_list('public_ip', flat=True)

        for ip in self.ip_network.hosts():
            if ip not in ips_in_use:
                return ip
        else:
            raise self.AddressExhaustion()


class VlanMembership(models.Model):
    """Membership relation between ASes and VLANs."""
    vlan = models.ForeignKey(
        VLAN,
        verbose_name="VLAN",
        on_delete=models.CASCADE
    )
    asys = models.ForeignKey(
        AS,
        verbose_name="AS",
        on_delete=models.CASCADE
    )
    public_ip = IpAddressField(
        verbose_name="IP Address"
    )
    first_br_port = L4PortField(
        verbose_name="First BR Port",
        help_text="First UDP port to assign to SCION links.",
        null=True,
        blank=True
    )
    last_br_port = L4PortField(
        verbose_name="Last BR Port",
        help_text="One past the last UDP port to assign to SCION links.",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "VLAN Membership"
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys'], name="unique_vlan_membership")
        ]

    def __str__(self):
        return "%s is a member of %s" % (self.asys, self.vlan)

    def clean(self):
        # This seems to run before the fields are converted to their Python representation, so we
        # have to parse the IP address for the model level validation.
        try:
            public_ip = ipaddress.ip_address(self.public_ip)
        except ValueError:
            return # IP is invalid, will be caught later

        try:
            if public_ip not in self.vlan.ip_network:
                raise ValidationError(
                    "IP address %(public_ip)s is not from the VLANs valid subnet.",
                    code='invalid_public_ip', params={'public_ip': public_ip})
        except VLAN.DoesNotExist:
            return # vlan is empty, will be caught during form validation.

        try:
            if VlanMembership.objects.filter(
                Q(vlan=self.vlan) & ~Q(asys=self.asys) & Q(public_ip=public_ip)):
                raise ValidationError("IP address %(public_ip)s is in use by another AS.",
                    code='public_ip_in_use', params={'public_ip': public_ip})
        except VLAN.DoesNotExist:
            return # vlan is empty, will be caught during form validation.

    class PortExhaustion(Exception):
        def __init__(self, vlan: VLAN, asys: AS):
            super().__init__("AS %s (VLAN %s): Border router ports exhausted." % (asys, vlan))

    def get_free_br_port(self) -> int:
        """Returns a free border router port.

        :raises PortExhaustion: No free ports available.
        """
        if self.first_br_port is None or self.last_br_port is None:
            raise self.PortExhaustion(self.vlan, self.asys)
        ports = sorted(
            [pair[0] for pair in Link.objects.filter(as_a=self.asys).values_list('br_port_a')] +
            [pair[0] for pair in Link.objects.filter(as_b=self.asys).values_list('br_port_b')]
        )
        for i, j in itertools.zip_longest(ports, range(self.first_br_port, self.last_br_port)):
            if i != j:
                return j
        else:
            raise self.PortExhaustion(self.vlan, self.asys)


#############
### Links ###
#############

class LinkManager(models.Manager):
    def create(self, *, vlan: VLAN, as_a: AS, as_b: AS):
        """Create a link between `as_a` and `as_b`. The link type is determined from the AS types.

        :param vlan: VLAN the links is created in.
        :raises ValidationError: If `as_a` and `as_b` are of different types (core and non-core).
        """
        # Figure out which link type to use.
        if as_a.is_core and as_b.is_core:
            link_type = Link.CORE
        elif not as_a.is_core and not as_b.is_core:
            link_type = Link.PEERING
        else:
            raise ValidationError("Cannot link core and non-core AS.",
                code='core_non_core_conflict')

        br_port_a = self._get_vlan_membership(vlan, as_a).get_free_br_port()
        br_port_b = self._get_vlan_membership(vlan, as_b).get_free_br_port()

        super().create(vlan=vlan, link_type=link_type,
            as_a=as_a, as_b=as_b,
            br_port_a=br_port_a, br_port_b=br_port_b)

    @staticmethod
    def _get_vlan_membership(vlan: VLAN, asys: AS) -> VlanMembership:
        try:
            return VlanMembership.objects.get(vlan=vlan, asys=asys)
        except VlanMembership.DoesNotExist:
            raise ValidationError("%(asys)s is not a member of %(vlan)s.",
                code='not_a_vlan_member',
                params={'asys': asys, 'vlan': vlan})


class Link(models.Model):
    """Link between two SCION ASes."""
    CORE = 0
    PEERING = 1
    PROVIDER = 2

    _LINK_TYPES = [
        (CORE, "Core Link"),
        (PEERING, "Peering Link"),
        (PROVIDER, "Provider to Customer Link")
    ]

    vlan = models.ForeignKey(
        VLAN,
        verbose_name="VLAN",
        related_name="links",
        on_delete=models.CASCADE
    )
    link_type = models.SmallIntegerField(
        choices=_LINK_TYPES,
        verbose_name="Type"
    )

    as_a = models.ForeignKey(
        AS,
        verbose_name="AS A",
        related_name="+",
        on_delete=models.CASCADE
    )
    br_port_a = L4PortField(
        verbose_name="UDP Port A"
    )

    as_b = models.ForeignKey(
        AS,
        verbose_name="AS B",
        related_name="+",
        on_delete=models.CASCADE
    )
    br_port_b = L4PortField(
        verbose_name="UDP Port B"
    )

    objects = LinkManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['as_a', 'as_b', 'vlan'], name="unique_links")
        ]

    def __str__(self):
        if self.link_type == self.CORE:
            return "Core Link %s <-> %s" % (self.as_a, self.as_b)
        elif self.link_type == self.PEERING:
            return "Peering Link %s <-> %s" % (self.as_a, self.as_b)
        else:
            return "Provider Link %s -> %s" % (self.as_a, self.as_b)


################
### Policies ###
################

class PeeringPolicy(models.Model):
    """Abstract base class for accept/reject peering policies."""
    vlan = models.ForeignKey(
        VLAN,
        verbose_name="VLAN",
        on_delete=models.CASCADE
    )
    asys = models.ForeignKey(
        AS,
        verbose_name="AS",
        on_delete=models.CASCADE
    )
    accept = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        self.full_clean()
        super().save(**kwargs)

    def clean(self):
        try:
            # Make sure the AS is actually connected to the VLAN.
            if not VlanMembership.objects.filter(vlan=self.vlan, asys=self.asys):
                raise ValidationError("%(asys)s is not a member of %(vlan)s.",
                    code='not_a_vlan_member',
                    params={'asys': self.asys, 'vlan': self.vlan})
        except (VLAN.DoesNotExist, AS.DoesNotExist):
            pass # vlan or asys are empty, will be caught during form validation.

    def get_policy_type_str(self) -> str:
        """String representation of the policy type (accept/reject) for the admin interface."""
        if self.accept:
            return "Accept"
        else:
            return "Reject"

    get_policy_type_str.admin_order_field = 'accept'
    get_policy_type_str.short_description = "Type"


class AsPeerPolicy(PeeringPolicy):
    """AS accept/reject policy."""
    peer_as = models.ForeignKey(
        AS,
        verbose_name="Peer AS",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'AS Peering Policy'
        verbose_name_plural = 'AS Peering Policies'
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys', 'peer_as'], name="unique_as_policy")
        ]

    def clean(self):
        super().clean()
        try:
            if self.asys == self.peer_as:
                raise ValidationError("AS and peer AS are identical.", code='peer_with_self')
        except AS.DoesNotExist:
            pass # asys or peer_as are empty, will be caught during form validation.

    def __str__(self):
        if self.accept:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_as, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_as, self.vlan)


class IsdPeerPolicy(PeeringPolicy):
    """ISD accept/accept policy."""
    peer_isd = models.ForeignKey(
        ISD,
        verbose_name="Peer ISD",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'ISD Peering Policy'
        verbose_name_plural = 'ISD Peering Policies'
        constraints = [
            models.UniqueConstraint(fields=['vlan', 'asys', 'peer_isd'], name="unique_isd_policy")
        ]

    def __str__(self):
        if self.accept:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_isd, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_isd, self.vlan)


class OrgPeerPolicy(PeeringPolicy):
    """Organization accept/reject policy."""
    peer_org = models.ForeignKey(
        Organization,
        verbose_name="Peer Organization",
        related_name="+",
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Organization Peering Policy'
        verbose_name_plural = 'Organization Peering Policies'
        constraints = [
            models.UniqueConstraint(
                fields=['vlan', 'asys', 'peer_org'], name="unique_org_policy")
        ]

    def __str__(self):
        if self.reject:
            return "Accept %s -> %s (%s)" % (self.asys, self.peer_org, self.vlan)
        else:
            return "Reject %s -> %s (%s)" % (self.asys, self.peer_org, self.vlan)
