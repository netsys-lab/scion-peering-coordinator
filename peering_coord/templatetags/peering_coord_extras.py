from django.template.defaulttags import register


@register.filter
def get_item(dict, key):
    """Get an item from a mapping."""
    print(type(dict), dict)
    return dict.get(key)


@register.filter
def url_format_asn(asn):
    """Format an ASN for inclusing in a URL."""
    return str(asn).replace(":", "-")


@register.filter
def count_peers(asys, vlan):
    """Gets the number of peers connected to an AS in a certain VLAN."""
    # TODO: Cache
    return asys.query_connected_peers(vlan=vlan).count()


@register.filter
def has_access(user, asys):
    """Returns true, if the user has access to the configuration of the given AS."""
    return user.is_superuser or asys.owner.users.filter(id=user.id).exists()
