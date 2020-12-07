"""Functions for updating links according to the peering policies.
"""
from django.db import transaction
from django.db.models import Q, QuerySet

from peering_coord.models import *


@transaction.atomic
def update_accepted_peers(vlan: VLAN, asys: AS) -> None:
    """Update the AcceptedPeers relation of ASes accepted for peering.

    :param vlan: Peering VLAN to update.
    :param asys: AS whose accepted peers are updated.
    """
    old = AcceptedPeers.objects.filter(asys=asys).values_list('peer_id')
    new = _get_accepted_peers(vlan, asys)

    # Calculate which peers to add/remove.
    remove = old.difference(new)
    add = new.difference(old)

    # Remove peers which are no longer accepted.
    AcceptedPeers.objects.filter(asys=asys, peer_id__in=remove, vlan=vlan).delete()

    # Add peers which are not accepted at the moment.
    AcceptedPeers.objects.bulk_create([
        AcceptedPeers(asys=asys, peer_id=peer[0], vlan=vlan)
        for peer in add
    ])


@transaction.atomic
def update_links(vlan: VLAN, asys: AS) -> None:
    """Create and delete links of the given AS to reflect the peering accepted by it and its peers.

    Uses accepted peerings from AcceptedPeers relation instead of evaluating the peering policies
    directly. update_accepted_peers() must be called on every ASes whose policies have changed for
    this function to get up-to-date data.

    :param vlan: Peering VLAN to update.
    :param asys: AS whose links are updated.
    """
    # Get currently connected peers.
    peers1 = Link.objects.filter(as_a=asys).values_list('as_b_id')
    peers2 = Link.objects.filter(as_b=asys).values_list('as_a_id')
    peers_old = peers1.union(peers2)

    # Get set of ASes which should be connected.
    peers_new = AcceptedPeers.objects.filter(vlan=vlan, asys__in=asys.accept.all(),
        asys__is_core=asys.is_core, peer=asys).values_list('asys')

    # Calculate which links to add/remove.
    remove = peers_old.difference(peers_new)
    add = peers_new.difference(peers_old)

    # Remove old links.
    Link.objects.filter(
        Q(vlan=vlan) & (Q(as_a=asys, as_b__in=remove) | Q(as_a__in=remove, as_b=asys))).delete()

    # Add new links.
    for peer_id in add:
        peer = AS.objects.get(id=peer_id[0])
        Link.objects.create(vlan=vlan, as_a=asys, as_b=peer)


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

    # Organization-level policies
    org_accept = Organization.objects.filter(
        id__in=OrgPeerPolicy.objects.filter(
            vlan=vlan, asys=asys, accept=True).values_list('peer_org_id'))
    org_reject = Organization.objects.filter(
        id__in=OrgPeerPolicy.objects.filter(
            vlan=vlan, asys=asys, accept=False).values_list('peer_org_id'))

    # ISD-level policies
    isd_accept = IsdPeerPolicy.objects.filter(
        vlan=vlan, asys=asys, accept=True).values_list('peer_isd_id')

    # Put it all together
    # Note: The same AS/Organization/ISD cannot be accepted *and* rejected at the same time.
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

    return accept
