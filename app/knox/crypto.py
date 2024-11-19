import binascii
from os import urandom as generate_bytes

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


def create_token_string():
    auth_token_character_length = 64
    return binascii.hexlify(
        generate_bytes(int(auth_token_character_length / 2))
    ).decode()


def hash_token(token):
    """
    Calculates the hash of a token.
    input is unhexlified

    token must contain an even number of hex digits or a binascii.Error
    exception will be raised
    """
    digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
    digest.update(binascii.unhexlify(token))
    return binascii.hexlify(digest.finalize()).decode()
