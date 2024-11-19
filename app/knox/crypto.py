import binascii
import hashlib
from os import urandom as generate_bytes


def create_token_string():
    auth_token_character_length = 64
    return binascii.hexlify(
        generate_bytes(int(auth_token_character_length / 2))
    ).decode()


def hash_token(token):
    """
    Calculates the hash of a token.
    Token must contain an even number of hex digits or
    a binascii.Error exception will be raised.
    """
    digest = hashlib.sha512()
    digest.update(binascii.unhexlify(token))
    return digest.hexdigest()
