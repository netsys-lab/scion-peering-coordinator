"""Peering API"""

import io
import typing
from typing import Optional, Tuple

import grpc
from google.protobuf.empty_pb2 import Empty
from rest_framework import serializers
from django_grpc_framework.services import Service
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction

from peering_coord.api import peering_pb2
from peering_coord.api.authentication import get_client_from_metadata
from peering_coord.api.serializers import PolicyProtoSerializer
from peering_coord.models.ixp import VLAN
from peering_coord.models.policies import (
    DefaultPolicy, AsPeerPolicy, IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.scion_addr import ASN


class TransactionRollback(Exception):
    pass


class PeeringService(Service):

    # TODO: Persistent channel for link updates
    # def StreamChannel(self, request_iterator, context):
    #     pass

    @transaction.atomic
    def ListPolicies(self, request, context):
        """List policies of the AS making the request."""
        my_asn, client = get_client_from_metadata(context.invocation_metadata())

        # Prepare common selection criteria
        common_selection = {'asys__asn': ASN(my_asn)}
        if request.vlan:
            common_selection['vlan__name'] = request.vlan
        if request.asn and request.asn != my_asn:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Cannot list policies of other ASes")
        if request.WhichOneof("accept_") is not None:
            common_selection['accept'] = request.accept

        # Return matching default policies
        if request.WhichOneof('peer') is None or request.peer_everyone:
            for policy in DefaultPolicy.objects.filter(**common_selection):
                yield PolicyProtoSerializer(policy).message

        # Return matching AS policies
        if request.WhichOneof('peer') is None or request.peer_asn:
            policies = AsPeerPolicy.objects.filter(**common_selection)
            if request.peer_asn:
                try:
                    policies = policies.filter(peer_as__asn=ASN(request.peer_asn))
                except ValueError:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid ASN")
            for policy in policies.filter(**common_selection):
                yield PolicyProtoSerializer(policy).message

        # Return matching owner policies
        if request.WhichOneof('peer') is None or request.peer_owner:
            policies = OwnerPeerPolicy.objects.filter(**common_selection)
            if request.peer_owner:
                policies = policies.filter(peer_owner__name=request.peer_owner)
            for policy in policies.filter(**common_selection):
                yield PolicyProtoSerializer(policy).message

        # Return matching ISD policies
        if request.WhichOneof('peer') is None or request.peer_isd:
            policies = IsdPeerPolicy.objects.filter(**common_selection)
            if request.peer_isd:
                try:
                    policies = policies.filter(peer_isd__isd_id=int(request.peer_isd))
                except ValueError:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid ISD")
            for policy in policies.filter(**common_selection):
                yield PolicyProtoSerializer(policy).message

    @transaction.atomic
    def CreatePolicy(self, request, context):
        """Create a new policy."""
        my_asn, client = get_client_from_metadata(context.invocation_metadata())

        if request.asn != my_asn:
            context.abort(grpc.StatusCode.PERMISSION_DENIED,
                "Cannot create policies for other ASes")

        serializer = PolicyProtoSerializer(message=request)
        if not serializer.is_valid():
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, _fmt_validation_errors(serializer.errors))

        try:
            serializer.save()
        except ValidationError as e:
            msg, code = _translate_validation_errors(e)
            context.abort(code, msg)

        return serializer.message

    @transaction.atomic
    def DestroyPolicy(self, request, context):
        """Delete a policy."""
        my_asn, client = get_client_from_metadata(context.invocation_metadata())

        if request.asn != my_asn:
            context.abort(grpc.StatusCode.PERMISSION_DENIED,
                "Cannot delete policies of other ASes")

        serializer = PolicyProtoSerializer(message=request)
        if not serializer.is_valid():
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, _fmt_validation_errors(serializer.errors))
        try:
            policy = serializer.get()
        except ObjectDoesNotExist:
            context.abort(grpc.StatusCode.NOT_FOUND, "Policy does not exist")

        policy.delete()
        return Empty()

    def SetPolicies(self, request, context):
        """Replace existing polices in one or all VLANs."""
        try:
            with transaction.atomic():
                rejected_policies, errors = self._set_policies(request, context)
                if len(errors) > 0 and not request.continue_on_error:
                    # Trigger a rollback of the transaction block, but continue processing the
                    # request.
                    raise TransactionRollback()
        except TransactionRollback:
            pass

        # Build response
        response = peering_pb2.SetPoliciesResponse()
        response.rejected_policies.extend(rejected_policies)
        response.errors.extend( errors)
        return response

    def _set_policies(self, request, context) -> Tuple[
            typing.List[peering_pb2.Policy], typing.List[str]]:
        # Delete old policies. Parse the new ones, and try saving them to the DB.
        # Returns the unsuccessful policies and matching error descriptions.
        # context.abort() is called on fatal errors to abort the RPC and trigger a transaction
        # rollback.
        my_asn, client= get_client_from_metadata(context.invocation_metadata())

        # Delete previous policies
        if request.vlan:
            try:
                _delete_policies(ASN(my_asn), VLAN.objects.get(name=request.vlan).id)
            except VLAN.DoesNotExist:
                context.abort(grpc.StatusCode.NOT_FOUND, "VLAN does not exist")
        else:
            _delete_policies(ASN(my_asn))

        # Create new policies
        rejected_policies = []
        errors = []
        for policy in request.policies:
            serializer = PolicyProtoSerializer(message=policy)

            if policy.asn != my_asn:
                rejected_policies.append(policy)
                errors.append("Policy ASN belongs to foreign AS")
                continue

            if request.vlan and policy.vlan != request.vlan:
                rejected_policies.append(policy)
                errors.append("VLAN excluded by filter")
                continue

            if not serializer.is_valid():
                rejected_policies.append(policy)
                errors.append(_fmt_validation_errors(serializer.errors))
                continue

            try:
                serializer.save()
            except ValidationError as e:
                msg, _ = _translate_validation_errors(e)
                rejected_policies.append(policy)
                errors.append(msg)
                continue

        return rejected_policies, errors


def _delete_policies(asn: ASN, vlan_id: Optional[int] = None):
    """Delete all peering policies of the given AS optionally limited to a certain VLAN."""
    filter = {'asys__asn': asn}
    if vlan_id is not None:
        filter['vlan__id'] = vlan_id

    AsPeerPolicy.objects.filter(**filter).delete()
    OwnerPeerPolicy.objects.filter(**filter).delete()
    IsdPeerPolicy.objects.filter(**filter).delete()


def _fmt_validation_errors(errors: serializers.ValidationError) -> str:
    """Formats a set of serializer validation errors."""
    msg = io.StringIO()
    for field, field_errors in errors.items():
        msg.write("{}:".format(field))
        for error in field_errors:
            msg.write(" {}".format(error))
    return msg.getvalue()


def _translate_validation_errors(validation_error: ValidationError) -> Tuple[str, grpc.StatusCode]:
    """Concatenates Django validaition errors to a single error message and returns an appropriate
    gRPC error code.
    """
    msg = io.StringIO()
    codes = set()

    for field, errors in validation_error.error_dict.items():
        msg.write("{}:".format(field))
        for error in errors:
            codes.add(error.code)
            msg.write(" {}".format(" ".join(error.messages)))

    if 'unique_together' in codes:
        code = grpc.StatusCode.ALREADY_EXISTS
    else:
        code = grpc.StatusCode.INVALID_ARGUMENT

    return msg.getvalue(), code
