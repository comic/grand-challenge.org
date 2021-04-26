import base64
from typing import Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.utils.crypto import get_random_string


class FernetCrypter:
    derivation = PBKDF2HMAC
    algorithm = SHA256
    iterations = 200_000
    encoding = "utf-8"
    separator = "$"

    @property
    def algorithm_name(self):
        return f"{self.derivation.__name__}_{self.algorithm.__name__}"

    def serialize(self, salt: str, token: str) -> str:
        if self.separator in salt:
            raise ValueError(f"Separator '{self.separator}' found in salt")

        return f"{self.algorithm_name}${self.iterations}${salt}${token}"

    def deserialize(self, encoded: str) -> Tuple[str, str]:
        algorithm_name, iterations, salt, token = encoded.split(
            self.separator, 3
        )

        if algorithm_name != self.algorithm_name:
            raise ValueError("Algorithms do not match")

        if int(iterations) != self.iterations:
            raise ValueError("Iterations do not match")

        return salt, token

    def generate_key(self, *, salt: str, secret_key: str):
        kdf = self.derivation(
            algorithm=self.algorithm(),
            salt=salt.encode(self.encoding),
            iterations=self.iterations,
            length=32,  # Must be 32 for Fernet
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(secret_key.encode(self.encoding))
        )
        return Fernet(key)

    def encrypt(self, *, data: str, secret_key: str) -> str:
        salt = get_random_string(43)  # 256 bits
        token = (
            self.generate_key(salt=salt, secret_key=secret_key)
            .encrypt(data.encode(self.encoding))
            .decode(self.encoding)
        )
        return self.serialize(salt=salt, token=token)

    def decrypt(self, *, encoded: str, secret_key: str) -> str:
        salt, token = self.deserialize(encoded=encoded)
        return (
            self.generate_key(salt=salt, secret_key=secret_key)
            .decrypt(token.encode(self.encoding))
            .decode(self.encoding)
        )
