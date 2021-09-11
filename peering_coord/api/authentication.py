"""Token-based authentication for the gRPC API"""

from typing import Tuple

import grpc

from peering_coord.models.ixp import PeeringClient
from peering_coord.scion_addr import ASN


ASN_HEADER_KEY = "asn"
CLIENT_NAME_HEADER_KEY = "client"
TOKEN_HEADER_KEY = "token"


def get_client_from_metadata(metadata) -> Tuple[str, str]:
    """Retrive ASN and peering client name from request metadata.

    :returns: Tuple of ASN and client name as strings. If a value is not set, an empty string is
    returned for that value.
    """
    asn = ""
    client = ""

    for datum in metadata:
        if datum[0] == ASN_HEADER_KEY:
            asn = datum[1]
        elif datum[0] == CLIENT_NAME_HEADER_KEY:
            client = datum[1]

    return (asn, client)


class TokenValidationInterceptor(grpc.ServerInterceptor):
    """Check for a valid API token in the request metadata. Request without proper authentication
    are rejected.
    """
    def __init__(self):
        def abort(_request, context):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication failed.")

        self._abortion = grpc.unary_unary_rpc_method_handler(abort)

    def intercept_service(self, continuation, handler_call_details):
        asn, client = get_client_from_metadata(handler_call_details.invocation_metadata)
        if not asn or not client:
            return self._abortion

        # Retrieve the expected token
        try:
            query = PeeringClient.objects.values_list('secret_token', flat=True)
            token = query.get(asys__asn=ASN(asn), name=client)
        except ValueError:
            return self._abortion
        except PeeringClient.DoesNotExist:
            return self._abortion

        expected_metadata = (TOKEN_HEADER_KEY, token)
        if expected_metadata in handler_call_details.invocation_metadata:
            return continuation(handler_call_details)
        else:
            return self._abortion


# django_grpc_framework expects interceptor instances in its SERVER_INTERCEPTORS setting,
# therefore we create an instance here.
TokenValidatorInterceptorInst = TokenValidationInterceptor()
