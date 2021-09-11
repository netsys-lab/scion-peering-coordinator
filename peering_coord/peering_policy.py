"""Functions for updating links according to peering policies"""

from django.db import transaction
from django.db.models import Q, QuerySet

from peering_coord.api.client_connection import ClientRegistry
from peering_coord.api.peering_pb2 import AsyncError
from peering_coord.models.ixp import VLAN, Interface, Owner
from peering_coord.models.policies import (
    AsPeerPolicy, DefaultPolicy, IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.models.scion import AS, AcceptedPeer, Link


@transaction.atomic
def update_accepted_peers(vlan: VLAN, asys: AS) -> None:
    """Update the AcceptedPeer relation of ASes accepted for peering.

    :param vlan: Peering VLAN to update.
    :param asys: AS whose accepted peers are updated.
    """
    old = AcceptedPeer.objects.filter(vlan=vlan, asys=asys).values_list('peer_id')
    new = _get_accepted_peers(vlan, asys)

    # Calculate which peers to add/remove.
    remove = old.difference(new)
    add = new.difference(old)

    # Remove peers which are no longer accepted.
    AcceptedPeer.objects.filter(vlan=vlan, asys=asys, peer_id__in=remove).delete()

    # Add peers which are not accepted at the moment.
    AcceptedPeer.objects.bulk_create(
        AcceptedPeer(vlan=vlan, asys=asys, peer_id=peer[0]) for peer in add)


def _get_accepted_peers(vlan: VLAN, asys: AS) -> QuerySet:
    """Get the set of ASes `asys` accepts for peering.

    :param vlan: Peering VLAN considered by the query.
    :param asys: AS whose potential peers are retrieved.
    :returns: A `QuerySet` of AS primary keys as returned by `values_list`.
    """
    # AS-level policies
    as_accept = AsPeerPolicy.objects.filter(
        vlan=vlan, asys=asys, accept=True).values_list('peer_as_id')
    as_reject = AsPeerPolicy.objects.filter(
        vlan=vlan, asys=asys, accept=False).values_list('peer_as_id')

    # Owner-level policies
    org_accept = Owner.objects.filter(
        id__in=OwnerPeerPolicy.objects.filter(
            vlan=vlan, asys=asys, accept=True).values_list('peer_owner_id'))
    org_reject = Owner.objects.filter(
        id__in=OwnerPeerPolicy.objects.filter(
            vlan=vlan, asys=asys, accept=False).values_list('peer_owner_id'))

    # ISD-level policies
    isd_accept = IsdPeerPolicy.objects.filter(
        vlan=vlan, asys=asys, accept=True).values_list('peer_isd_id')
    isd_reject = IsdPeerPolicy.objects.filter(
        vlan=vlan, asys=asys, accept=False).values_list('peer_isd_id')

    # Put it all together
    # Note: The same AS/Owner/ISD cannot be accepted *and* rejected at the same time.
    as_accepted_by_org = AS.objects.filter(
        Q(owner_id__in=org_accept) & ~Q(id=asys.id)).values_list('id')
    as_rejected_by_org = AS.objects.filter(
        Q(owner_id__in=org_reject) & ~Q(id=asys.id)).values_list('id')
    as_accepted_by_isd = AS.objects.filter(
        Q(isd_id__in=isd_accept) & ~Q(id=asys.id)).values_list('id')
    accept = as_accept.union(
        as_accepted_by_org.difference(as_reject),
        as_accepted_by_isd.difference(as_rejected_by_org, as_reject)
    )

    # Handle default accept policy
    if DefaultPolicy.objects.filter(vlan=vlan, asys=asys, accept=True).exists():
        as_rejected_by_isd = AS.objects.filter(
            Q(isd_id__in=isd_reject) & ~Q(id=asys.id)).values_list('id')
        as_all = vlan.members.values_list('asys', flat=True).filter(~Q(asys=asys.id)).distinct()
        accept = accept.union(as_all.difference(as_rejected_by_isd, as_rejected_by_org, as_reject))

    return accept


@transaction.atomic
def update_links(vlan: VLAN, asys: AS) -> None:
    """Create and delete links of the given AS to reflect the peering accepted by it and its peers.

    Uses accepted peerings from AcceptedPeer relation instead of evaluating the peering policies
    directly. update_accepted_peers() must be called on every ASes whose policies have changed for
    this function to get up-to-date data.

    :param vlan: Peering VLAN to update.
    :param asys: AS whose links are updated.
    """
    # Get currently connected ASes.
    peers_old = asys.query_connected_peers(vlan=vlan)

    # Get ASes that should be connected.
    peers_new = asys.query_mutually_accepted_peers(vlan=vlan)

    # Calculate which links to add/remove.
    remove = peers_old.difference(peers_new)
    add = peers_new.difference(peers_old)

    # Remove old links.
    Link.objects.filter(
        Q(interface_a__vlan=vlan) # both interfaces are always in the same VLAN
        & (Q(interface_a__peering_client__asys=asys, interface_b__peering_client__asys__in=remove)
         | Q(interface_a__peering_client__asys__in=remove, interface_b__peering_client__asys=asys))
        ).delete()

    # Add new links.
    for peer_id in add:
        peer = AS.objects.get(id=peer_id[0])
        _create_links(vlan, asys, peer)


def _create_links(vlan: VLAN, as_a: AS, as_b: AS):
    """Create links between all interfaces of `as_a` and `as_b` in `vlan`.

    The link type is determined from the AS types.
    """
    # Figure out which link type to use.
    if as_a.is_core and as_b.is_core:
        link_type = Link.Type.CORE
    elif not as_a.is_core and not as_b.is_core:
        link_type = Link.Type.PEERING
    elif as_a.isd == as_b.isd:
        link_type = Link.Type.PROVIDER
        if not as_a.is_core and as_b.is_core:
            as_a, as_b = as_b, as_a
    else:
        error = AsyncError()
        error.code = AsyncError.Code.LINK_CREATION_FAILED
        error.message = "Cannot create a link between ASes {} and {} of incompatible type.".format(
            as_a, as_b
        )
        ClientRegistry.send_async_error(as_a.asn, error)
        ClientRegistry.send_async_error(as_b.asn, error)
        return

    for interface_a in as_a.query_interfaces().filter(vlan=vlan).all():
        for interface_b in as_b.query_interfaces().filter(vlan=vlan).all():
            port_a = port_b = None

            try:
                port_a = interface_a.get_unused_port()
            except Interface.NoUnusedPorts:
                error = AsyncError()
                error.code = AsyncError.Code.LINK_CREATION_FAILED
                error.message = "Allocated port range is exhausted on interface {}.".format(
                    interface_a)
                ClientRegistry.send_async_error(as_a.asn, error)

            try:
                port_b = interface_b.get_unused_port()
            except Interface.NoUnusedPorts:
                error = AsyncError()
                error.code = AsyncError.Code.LINK_CREATION_FAILED
                error.message = "Allocated port range is exhausted on interface {}.".format(
                    interface_b)
                ClientRegistry.send_async_error(as_b.asn, error)

            if port_a and port_b:
                Link.objects.create(link_type,
                    interface_a=interface_a, interface_b=interface_b,
                    port_a=port_a, port_b=port_b)
