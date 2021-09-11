"""Implementation of the informational gRPC API provided by the coordinator."""
import grpc
from django_grpc_framework.services import Service
from django.db import transaction

from peering_coord.api import info_pb2
from peering_coord.models.scion import AS
from peering_coord.models.ixp import Owner
from peering_coord.scion_addr import ASN


class InfoServive(Service):
    """Non-essential informational services provided by the coordinator."""

    @transaction.atomic
    def GetOwner(self, request, context):
        """Retrieve information on an AS owner by owner name or by an AS."""
        # Build query
        query = Owner.objects
        if request.name:
            query = query.filter(name=request.name)
        if request.asn:
            try:
                query = query.filter(ases__asn=ASN(request.asn))
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid ASN")

        # Query database
        owner = None
        try:
            owner = query.get()
        except Owner.DoesNotExist:
            context.abort(grpc.StatusCode.NOT_FOUND, "No matching owner found")

        # Build response
        buffer = info_pb2.Owner()
        _fill_owner_protobuf(owner, buffer)
        return buffer

    @transaction.atomic
    def SearchOwner(self, request, context):
        """Search for AS owners matching the given criteria."""
        for owner in Owner.objects.filter(long_name__icontains=request.long_name).all():
            buffer = info_pb2.Owner()
            _fill_owner_protobuf(owner, buffer)
            yield buffer


def _fill_owner_protobuf(owner: Owner, buffer: info_pb2.Owner) -> None:
    """Helper function for filling out Owner buffers."""
    buffer.name = owner.name
    buffer.long_name = owner.long_name
    buffer.asns.extend(str(asn[0]) for asn in AS.objects.filter(owner=owner).values_list('asn'))
