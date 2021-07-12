"""Database models of entities tied to the IXP"""

import ipaddress
import itertools
import secrets

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from peering_coord.custom_fields import IpAddressField, IpNetworkField, L4PortField
from peering_coord.models.limits import API_TOKEN_BYTES, MAX_LONG_NAME_LENGTH, MAX_SHORT_NAME_LENGTH


class Owner(models.Model):
    """An entity owning SCION ASes."""
    name = models.SlugField(
        verbose_name="Identifier",
        help_text="Uniquely identifies the owner in the API.",
        max_length=MAX_SHORT_NAME_LENGTH,
        unique=True
    )
    long_name = models.CharField(
        verbose_name="Name",
        help_text="Full name of the owner.",
        max_length=MAX_LONG_NAME_LENGTH
    )
    contact = models.TextField(
        help_text="Contact information for administrative purposes.",
        blank=True,
        null=True
    )
    users = models.ManyToManyField(
        User,
        help_text="User accounts with access to this entities ASes."
    )

    def __str__(self):
        return "Owner %s (%s)" % (self.long_name, self.name)

    def fmt_as_list(self) -> str:
        """Returns a formatted list of owned AS for use in views."""
        return ", ".join(str(asys) for asys in self.ases.all())
    fmt_as_list.short_description = "ASes"


class PeeringClient(models.Model):
    """A peering client an entity communicating with the peering coordinator on behalf of its AS.

    Typically, a peering client is deployed alongside a SCION border router to materialize the
    peering links negotiated with the peering coordinator. An AS may have multiple peering clients.

    Each peering deamon manages a number of interfaces connecting an AS to a certain VLAN at the
    IXP.
    """
    asys = models.ForeignKey(
        'AS',
        verbose_name="AS",
        related_name="peering_clients",
        on_delete=models.CASCADE
    )
    name = models.SlugField(
        default="default",
        help_text="A per-AS unique identifier for the border router."
    )
    secret_token = models.CharField(
        verbose_name="API Token",
        help_text="Secrect API authentication token.",
        max_length=2*API_TOKEN_BYTES,
        blank=True # A blank token disables API access.
    )

    class Meta:
        verbose_name = "Peering Client"
        verbose_name_plural = "Peering Clients"
        constraints = [
            models.UniqueConstraint(fields=['asys', 'name'], name="unique_peering_client_name")
        ]

    def __str__(self):
        return "%s-%s" % (self.asys.asn, self.name)

    def fmt_vlan_list(self):
        """Returns a formatted list of VLANs the peering client is connected to for the admin
        interface.
        """
        return ", ".join(vlan.name for vlan in self.get_connected_vlans())
    fmt_vlan_list.short_description = "VLANs"

    @staticmethod
    def gen_secret_token():
        """Generate a random API token."""
        return secrets.token_hex(API_TOKEN_BYTES)

    def get_connected_vlans(self):
        """Returns a list of VLANs this peering deamon is managing links in."""
        return VLAN.objects.filter(id__in=self.interfaces.values_list('vlan')).all()


class VLAN(models.Model):
    """Represents a peering LAN. Every VLAN has its own participants, peering policies, and links.

    A peering client and its AS are considered connected to a VLAN, if there is an Interface between
    them (see `members` field).
    """
    name = models.SlugField(
        verbose_name="Identifier",
        help_text="Uniquely identifies the VLAN.",
        max_length=MAX_SHORT_NAME_LENGTH,
        unique=True
    )
    long_name = models.CharField(
        verbose_name="Name",
        help_text="Verbose name.",
        max_length=MAX_LONG_NAME_LENGTH
    )
    ip_network = IpNetworkField(
        help_text="IP subnet used by the SCION underlay.",
        verbose_name="IP Network"
    )
    members = models.ManyToManyField(
        PeeringClient,
        related_name="vlans",
        through="Interface"
    )

    class Meta:
        verbose_name = "VLAN"
        verbose_name_plural = "VLANs"

    def __str__(self):
        return "VLAN %s (%s)" % (self.long_name, self.name)

    class NoUnusedIps(Exception):
        def __init__(self, vlan_str: str):
            super().__init__("No IPs available in %s.", vlan_str)

    def get_unused_ip(self):
        """Get an unused IP address from the VLAN's subnet.

        :raises NoUnusedIps: There are no unused addresses available anymore.
        """
        ips_in_use = Interface.objects.filter(vlan=self).values_list('public_ip', flat=True)

        for ip in self.ip_network.hosts():
            if ip not in ips_in_use:
                return ip
        else:
            raise self.NoUnusedIps(str(self))


class Interface(models.Model):
    """Interfaces represent connections from an AS represented by one of its peering clients to a
    VLAN.

    SCION links are created between interfaces. Typically, an interface maps to a single border
    router, but the same border router can also handle multiple interfaces.
    """
    peering_client = models.ForeignKey(
        PeeringClient,
        verbose_name="Peering Client",
        related_name="interfaces",
        on_delete=models.CASCADE
    )
    vlan = models.ForeignKey(
        VLAN,
        verbose_name="VLAN",
        related_name="interfaces",
        on_delete=models.CASCADE
    )
    public_ip = IpAddressField(
        verbose_name="IP Address"
    )
    first_port = L4PortField(
        verbose_name="First BR Port",
        help_text="First UDP port to assign to SCION links.",
        default=50500
    )
    last_port = L4PortField(
        verbose_name="Last BR Port",
        help_text="One past the last UDP port to assign to SCION links.",
        default=51000
    )
    links = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="+",
        through="Link"
    )

    def __str__(self):
        return "%s -> %s" % (self.peering_client, self.vlan)

    def save(self, **kwargs):
        self.full_clean()
        super().save(**kwargs)

    def clean(self):
        # This runs before the fields are converted to their Python representation, so we
        # have to parse the IP address for the model level validation.
        try:
            public_ip = ipaddress.ip_address(self.public_ip)
        except ValueError:
            return # IP is invalid, will be caught later

        # Make sure IP is from the VLAN's subnet.
        try:
            if public_ip not in self.vlan.ip_network:
                raise ValidationError(
                    "IP address %(public_ip)s is not from the VLAN's subnet.",
                    code='invalid_public_ip', params={'public_ip': public_ip})
        except VLAN.DoesNotExist:
            pass # vlan is empty, will be caught during form validation

        # Make sure IP is unused.
        try:
            if Interface.objects.filter(
                Q(vlan=self.vlan) & ~Q(id=self.id) & Q(public_ip=public_ip)).exists():
                raise ValidationError("IP address %(public_ip)s is in use by another interface.",
                    code='public_ip_in_use', params={'public_ip': public_ip})
        except VLAN.DoesNotExist:
            pass # vlan is empty, will be caught during form validation

    class NoUnusedPorts(Exception):
        def __init__(self, interface_str: str):
            super().__init__("No ports available in %s." % interface_str)

    def get_unused_port(self) -> int:
        """Returns an unused port in the interface port range [`first_port`, `last_port`).

        :raises NoUnusedPorts: No free ports available.
        """
        if not self.first_port or not self.last_port:
            raise self.NoUnusedPorts(str(self))
        asys = self.peering_client.asys
        ports = sorted(itertools.chain(
            (pair[0] for pair in
                Link.objects.filter(interface_a__peering_client__asys=asys).values_list('port_a')),
            (pair[0] for pair in
                Link.objects.filter(interface_b__peering_client__asys=asys).values_list('port_b'))
        ))
        for i, j in itertools.zip_longest(ports, range(self.first_port, self.last_port)):
            if i != j:
                return j
        else:
            raise self.NoUnusedPorts(str(self))


class Link(models.Model):
    """Represents a SCION link between two ASes.

    Two ASes can have multiple links of the same type in the same VLAN, if they belong to different
    peering client interfaces, but a single pair of interface does not support multiple links of the
    same type.
    """
    class Type(models.IntegerChoices):
        CORE = 0, "Core Link"
        PEERING = 1, "Peering Link"
        PROVIDER = 2, "Provider to Customer Link"

    link_type = models.SmallIntegerField(
        choices=Type.choices,
        verbose_name="Type",
        help_text="Type of the link in SCION."
    )
    interface_a = models.ForeignKey(
        Interface,
        verbose_name="Interface A",
        related_name="+",
        on_delete=models.CASCADE
    )
    port_a = L4PortField(
        verbose_name="UDP Port A"
    )
    interface_b = models.ForeignKey(
        Interface,
        verbose_name="Interface B",
        related_name="+",
        on_delete=models.CASCADE
    )
    port_b = L4PortField(
        verbose_name="UDP Port B"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['interface_a', 'interface_b'],
                name="unique_links_per_interface"),
            models.CheckConstraint(check=~Q(interface_a=F('interface_b')),
                name="different_interfaces")
        ]

    def __str__(self):
        if self.link_type == self.Type.CORE:
            return "Core Link (%s) <-> (%s)" % (self.interface_a, self.interface_b)
        elif self.link_type == self.Type.PEERING:
            return "Peering Link (%s) <-> (%s)" % (self.interface_a, self.interface_b)
        else:
            return "Provider Link (%s) -> (%s)" % (self.interface_a, self.interface_b)

    def save(self, **kwargs):
        self.full_clean()
        super().save(**kwargs)

    def clean(self):
        if self.interface_a.vlan != self.interface_b.vlan:
            raise ValidationError("Interfaces are from different VLANS.", code='different_vlans')
