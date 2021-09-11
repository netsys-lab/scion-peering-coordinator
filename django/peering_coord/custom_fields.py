"""Custom Django model fields"""

import ipaddress

from typing import Optional, Union
from django.db import models
from django.core.exceptions import ValidationError
from django.forms import CharField

from peering_coord.scion_addr import ASN


IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


class AsnField(models.Field):
    """Model field holding an AS number. ASNs are stored as 64-bit integersin the DB."""
    description = "AS number"

    def get_internal_type(self):
        return "BigIntegerField"

    def formfield(self, **kwargs):
        defaults = {'form_class': CharField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value: Optional[int], expression, connection) -> Optional[ASN]:
        if value is None:
            return value
        return ASN(value)

    def get_prep_value(self, value: ASN) -> int:
        return int(value)

    def to_python(self, value: Union[None, int, str, ASN]) -> Optional[ASN]:
        if isinstance(value, ASN):
            return value
        if value is None:
            return value
        try:
            return ASN(value)
        except ValueError as e:
            raise ValidationError("Invalid AS number: '%(value)s'. Error: %(msg)s",
                code='invalid_asn', params={'value': value, 'msg': str(e)})


class IpAddressField(models.Field):
    """IPv4/6 address as ipaddress.IPv4Address or ipaddress.IPv6Address.
    Stored in the DB as char(39).
    """
    description = "IP address"

    def db_type(self, connection):
        return 'char(39)'

    def formfield(self, **kwargs):
        defaults = {'form_class': CharField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value: Optional[str], expression, connection) -> Optional[IpAddress]:
        if value is None:
            return value
        # FIXME: rstrip is required to make this work with Postgres for some reason
        return ipaddress.ip_address(value.rstrip())

    def get_prep_value(self, value: IpAddress) -> str:
        return value.exploded

    def value_to_string(self, obj) -> str:
        return self.get_prep_value(self.value_from_object(obj))

    def to_python(self, value: Union[None, str, IpAddress]) -> Optional[IpAddress]:
        if isinstance(value, ipaddress.IPv4Address) or isinstance(value, ipaddress.IPv6Address):
            return value
        if value is None:
            return value
        try:
            return ipaddress.ip_address(value)
        except ValueError as e:
            raise ValidationError("Invalid IP address: '%(value)s'. Error: %(msg)s",
                code='invalid_ip', params={'value': value, 'msg': str(e)})


class IpNetworkField(models.Field):
    """IPv4/6 network definition as ipaddress.IPv4Network or ipaddress.IPv6Network.
    Stored in the DB as char(48).
    """
    description = "IP network"

    def db_type(self, connection):
        return 'char(48)'

    def formfield(self, **kwargs):
        defaults = {'form_class': CharField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value: Optional[str], expression, connection) -> Optional[IpNetwork]:
        if value is None:
            return value
        # FIXME: rstrip is required to make this work with Postgres for some reason
        return ipaddress.ip_network(value.rstrip())

    def get_prep_value(self, value: IpNetwork) -> str:
        return value.exploded

    def value_to_string(self, obj) -> str:
        return self.get_prep_value(self.value_from_object(obj))

    def to_python(self, value: Union[None, str, IpAddress]) -> Optional[IpNetwork]:
        if isinstance(value, ipaddress.IPv4Network) or isinstance(value, ipaddress.IPv6Network):
            return value
        if value is None:
            return value
        try:
            return ipaddress.ip_network(value)
        except ValueError as e:
            raise ValidationError("Invalid IP network definition: '%(value)s'. Error: %(msg)s",
                code='invalid_ip', params={'value': value, 'msg': str(e)})


class L4PortField(models.IntegerField):
    """L4 port number."""
    description = "L4 port"

    def validate(self, value, model_instance):
        if value < 0 or value >= 2**16:
            raise ValidationError("Invalid L4 port: %(value)d",
                code='invalid_port', params={'value': value})
