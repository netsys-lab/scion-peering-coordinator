from unittest import TestCase as PythonTestCase

from peering_coord.scion_addr import ASN


class AsnTest(PythonTestCase):
    """Test the parsing and deparsing of SCION AS numbers."""
    TEST_CASES = [
        ("0", 0),
        ("1", 1),
        (str(2**32-1), 2**32-1),
        ("1:0:0", 2**32),
        ("1:1:1", 0x100010001),
        ("ffff:ffff:ffff", 2**48-1)
    ]

    def test_asn_parsing(self):
        for string, integer in self.TEST_CASES:
            with self.subTest(string=string, integer=integer):
                self.assertEqual(int(ASN(string)), integer)

        with self.assertRaisesRegex(ValueError, r"Out of range"):
            ASN(-1)
        with self.assertRaisesRegex(ValueError, r"Out of range"):
            ASN(2**48)
        with self.assertRaisesRegex(ValueError, r"^Invalid decimal ASN"):
            ASN(str(2**32))
        with self.assertRaisesRegex(ValueError, r"^Invalid hexadecimal ASN"):
            ASN("ffff:fffff:ffff")
        with self.assertRaisesRegex(ValueError, r"Wrong number of colon-separated groups"):
            ASN("ff:ff:ff:ff:ff:ff")

    def test_asn_deparsing(self):
        for string, integer in self.TEST_CASES:
            with self.subTest(string=string, integer=integer):
                self.assertEqual(str(ASN(integer)), string)
