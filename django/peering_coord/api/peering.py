"""Implementation of the gRPC peering coordination service."""

import io
import ipaddress
import threading
import typing
from typing import Optional, Tuple

import grpc
from google.protobuf.empty_pb2 import Empty
from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django_grpc_framework.services import Service

from peering_coord import peering_policy
from peering_coord.api import peering_pb2
from peering_coord.api.authentication import get_client_from_metadata
from peering_coord.api.client_connection import (
    ClientConnections, ClientRegistry, create_link_update)
from peering_coord.api.serializers import PolicyProtoSerializer
from peering_coord.models.ixp import VLAN, Interface, PeeringClient
from peering_coord.models.policies import (
    AsPeerPolicy, DefaultPolicy, IsdPeerPolicy, OwnerPeerPolicy)
from peering_coord.models.scion import AS
from peering_coord.scion_addr import ASN


class TransactionRollback(Exception):
    pass


class PeeringService(Service):

    def StreamChannel(self, request_iterator, context):
        """Server side of the persistent bidirectional gRPC stream peering clients maintain with the
        coordinator.

        Since bidirectional gRPC streams in Python use blocking generators for sending and
        receiving, an additional thread just for reading request from the stream is created for
        every connection. The request listener threads forwards received requests to the main thread
        handling the connection via the associated ClientConnection object.
        """
        asn, client_name = get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn)

        # Register the connection
        try:
            conn = ClientRegistry.createConnection(asn, client_name)
        except KeyError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except ClientConnections.AlreadyConnected as e:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, str(e))
        except:
            context.abort(grpc.StatusCode.INTERNAL, "Internal error")

        # Enqueue link create messages for all existing links.
        client = PeeringClient.objects.get(asys__asn=asn, name=client_name)
        for interface in Interface.objects.filter(peering_client=client).all():
            for link in interface.query_links().all():
                if link.interface_a == interface:
                    update = create_link_update(peering_pb2.LinkUpdate.Type.CREATE,
                        link_type=link.link_type,
                        local_interface=link.interface_a, local_port=link.port_a,
                        remote_interface=link.interface_b, remote_port=link.port_b)
                else:
                    update = create_link_update(peering_pb2.LinkUpdate.Type.CREATE,
                        link_type=link.link_type,
                        local_interface=link.interface_b, local_port=link.port_b,
                        remote_interface=link.interface_a, remote_port=link.port_a)
                conn.send_link_update(update)

        # Launch a new thread to listen for requests from the client.
        def stream_listener():
            for request in request_iterator:
                conn.stream_request_received(request)
            conn.request_stream_closed()
        listener = threading.Thread(
            target=stream_listener,
            name="gRPC stream listener for {}-{}".format(asn, client_name))
        listener.start()

        # Run the event loop to process requests and generate responses.
        for response in conn.run():
            yield response

        ClientRegistry.destroyConnection(conn)
        listener.join()

    @transaction.atomic
    def SetPortRange(self, request, context):
        """Set the UDP port range used for SCION underlay connections."""
        asn_str, _ = get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn_str)

        # Validate arguments and retrieve the interface
        try:
            vlan = VLAN.objects.get(name=request.interface_vlan)
        except VLAN.DoesNotExist:
            context.abort(grpc.StatusCode.NOT_FOUND, "VLAN does not exist")
        try:
            ip = ipaddress.ip_address(request.interface_ip)
        except ValueError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid IP address")
        try:
            interface = Interface.objects.get(vlan=vlan, public_ip=ip)
        except (Interface.DoesNotExist, Interface.MultipleObjectsReturned):
            context.abort(grpc.StatusCode.NOT_FOUND, "Interface not found")

        recreate_links = not (request.first_port <= interface.first_port
                          and request.last_port >= interface.last_port)

        try:
            interface.first_port = request.first_port
            interface.last_port = request.last_port
            interface.save()
        except ValidationError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid port range")

        if recreate_links:
            # Recreate the interface's links with the new ports
            for link in interface.query_links().all():
                link.delete()
            peering_policy.update_links(vlan, AS.objects.get(asn=asn))

    @transaction.atomic
    def ListPolicies(self, request, context):
        """List policies of the AS making the request."""
        asn_str, client = get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn_str)

        # Prepare common selection criteria
        common_selection = {'asys__asn': asn}
        if request.vlan:
            common_selection['vlan__name'] = request.vlan
        if request.asn and request.asn != asn_str:
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
        asn_str, client = get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn_str)

        if request.asn != asn_str:
            context.abort(grpc.StatusCode.PERMISSION_DENIED,
                "Cannot create policies for other ASes")

        serializer = PolicyProtoSerializer(message=request)
        if not serializer.is_valid():
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, _fmt_validation_errors(serializer.errors))

        _assert_policy_write_permission(context, asn, client, request.vlan)

        try:
            policy = serializer.save()
        except ValidationError as e:
            msg, code = _translate_validation_errors(e)
            context.abort(code, msg)

        # Update links and notify clients
        peering_policy.update_accepted_peers(policy.vlan, policy.asys)
        peering_policy.update_links(policy.vlan, policy.asys)

        return serializer.message

    @transaction.atomic
    def DestroyPolicy(self, request, context):
        """Delete a policy."""
        asn_str, client = get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn_str)

        if request.asn != asn_str:
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

        _assert_policy_write_permission(context, asn, client, request.vlan)
        policy.delete()

        # Update links and notify clients
        peering_policy.update_accepted_peers(policy.vlan, policy.asys)
        peering_policy.update_links(policy.vlan, policy.asys)

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
        asn_str, client= get_client_from_metadata(context.invocation_metadata())
        asn = ASN(asn_str)

        # Delete previous policies
        if request.vlan:
            try:
                vlan_id = VLAN.objects.get(name=request.vlan).id
            except VLAN.DoesNotExist:
                context.abort(grpc.StatusCode.NOT_FOUND, "VLAN does not exist")
                _assert_policy_write_permission(context, asn, client, request.vlan)
            _delete_policies(asn, vlan_id)
        else:
            _assert_policy_write_permission(context, asn, client)
            _delete_policies(asn)

        # Create new policies
        rejected_policies = []
        errors = []
        for policy in request.policies:
            serializer = PolicyProtoSerializer(message=policy)

            if policy.asn != asn_str:
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

        # Update links and notify clients
        asys = AS.objects.get(asn=asn)
        for vlan in asys.get_connected_vlans():
            peering_policy.update_accepted_peers(vlan, asys)
            peering_policy.update_links(vlan, asys)

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


def _assert_policy_write_permission(context, asn: ASN, client: str, vlan: Optional[str] = None):
    """Helper function for checking whether a client is allowed to alter the pering policies.
    Triggers an exception to abort the RPC if the client does not have sufficient permissions.

    :param context: gRPC service context
    :param asn: AS the client belongs to.
    :param client: Peering client name.
    :param vlan: VLAN for which write permissions are checked. If None, checks if the client has
                 write access to every VLAN.
    """
    try:
        if not ClientRegistry.has_policy_write_permissions(asn, client, vlan):
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions")
    except:
        context.abort(grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions")
