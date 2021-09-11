"""Custom path converters for the URL dispatcher"""

from peering_coord.scion_addr import ASN


class AsnConverter:
    """Matches ASNs with colons replaced by hyphens."""
    regex = "(([0-9a-f]{1,4}-[0-9a-f]{1,4}-[0-9a-f]{1,4}))|([0-9]+)"

    def to_python(self, value: str) -> ASN:
        # ValueError is thrown to indicate no match.
        return ASN(value.replace("-", ":"))

    def to_url(self, value: ASN) -> str:
        return str(value).replace(":", "-")
