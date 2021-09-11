# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
from peering_coord.api import peering_pb2 as peering__coord_dot_api_dot_peering__pb2


class PeeringStub(object):
    """Peering API
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.StreamChannel = channel.stream_stream(
                '/coord.api.Peering/StreamChannel',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.StreamMessageRequest.SerializeToString,
                response_deserializer=peering__coord_dot_api_dot_peering__pb2.StreamMessageResponse.FromString,
                )
        self.SetPortRange = channel.unary_unary(
                '/coord.api.Peering/SetPortRange',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.PortRange.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.ListPolicies = channel.unary_stream(
                '/coord.api.Peering/ListPolicies',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.ListPolicyRequest.SerializeToString,
                response_deserializer=peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
                )
        self.CreatePolicy = channel.unary_unary(
                '/coord.api.Peering/CreatePolicy',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
                response_deserializer=peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
                )
        self.DestroyPolicy = channel.unary_unary(
                '/coord.api.Peering/DestroyPolicy',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )
        self.SetPolicies = channel.unary_unary(
                '/coord.api.Peering/SetPolicies',
                request_serializer=peering__coord_dot_api_dot_peering__pb2.SetPoliciesRequest.SerializeToString,
                response_deserializer=peering__coord_dot_api_dot_peering__pb2.SetPoliciesResponse.FromString,
                )


class PeeringServicer(object):
    """Peering API
    """

    def StreamChannel(self, request_iterator, context):
        """Persistent channel for push-notifications from the coordinator to the clients.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetPortRange(self, request, context):
        """Set the UDP port range used for SCION overlay connections.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ListPolicies(self, request, context):
        """List policies of the AS making the request.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CreatePolicy(self, request, context):
        """Create a new policy.
        Returns the newly create policy.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DestroyPolicy(self, request, context):
        """Delete a policy.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetPolicies(self, request, context):
        """Replace existing polices in one or all VLANs.
        If some of the given policies fail validation, the RPC has no effect unless
        continue_on_error is true.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PeeringServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'StreamChannel': grpc.stream_stream_rpc_method_handler(
                    servicer.StreamChannel,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.StreamMessageRequest.FromString,
                    response_serializer=peering__coord_dot_api_dot_peering__pb2.StreamMessageResponse.SerializeToString,
            ),
            'SetPortRange': grpc.unary_unary_rpc_method_handler(
                    servicer.SetPortRange,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.PortRange.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'ListPolicies': grpc.unary_stream_rpc_method_handler(
                    servicer.ListPolicies,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.ListPolicyRequest.FromString,
                    response_serializer=peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
            ),
            'CreatePolicy': grpc.unary_unary_rpc_method_handler(
                    servicer.CreatePolicy,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
                    response_serializer=peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
            ),
            'DestroyPolicy': grpc.unary_unary_rpc_method_handler(
                    servicer.DestroyPolicy,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
            'SetPolicies': grpc.unary_unary_rpc_method_handler(
                    servicer.SetPolicies,
                    request_deserializer=peering__coord_dot_api_dot_peering__pb2.SetPoliciesRequest.FromString,
                    response_serializer=peering__coord_dot_api_dot_peering__pb2.SetPoliciesResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'coord.api.Peering', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Peering(object):
    """Peering API
    """

    @staticmethod
    def StreamChannel(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_stream(request_iterator, target, '/coord.api.Peering/StreamChannel',
            peering__coord_dot_api_dot_peering__pb2.StreamMessageRequest.SerializeToString,
            peering__coord_dot_api_dot_peering__pb2.StreamMessageResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SetPortRange(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/coord.api.Peering/SetPortRange',
            peering__coord_dot_api_dot_peering__pb2.PortRange.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def ListPolicies(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(request, target, '/coord.api.Peering/ListPolicies',
            peering__coord_dot_api_dot_peering__pb2.ListPolicyRequest.SerializeToString,
            peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def CreatePolicy(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/coord.api.Peering/CreatePolicy',
            peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
            peering__coord_dot_api_dot_peering__pb2.Policy.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def DestroyPolicy(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/coord.api.Peering/DestroyPolicy',
            peering__coord_dot_api_dot_peering__pb2.Policy.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SetPolicies(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/coord.api.Peering/SetPolicies',
            peering__coord_dot_api_dot_peering__pb2.SetPoliciesRequest.SerializeToString,
            peering__coord_dot_api_dot_peering__pb2.SetPoliciesResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
