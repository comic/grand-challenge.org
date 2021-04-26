from base64 import urlsafe_b64encode

import pytest
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.hashes import SHA512

from grandchallenge.workspaces.crypters import FernetCrypter


def test_algorithm_name():
    c = FernetCrypter()
    assert c.algorithm_name == "PBKDF2HMAC_SHA256"


def test_generate_key():
    c = FernetCrypter()
    key = c.generate_key(salt="salt", secret_key="SECRET")
    assert urlsafe_b64encode(key._signing_key) == b"2ihUqFoFwLfwxDwWuxQO1A=="
    assert (
        urlsafe_b64encode(key._encryption_key) == b"_uHHwauJF0pu29u1Z_qXsA=="
    )


def test_encrypt_same_password(mocker):
    mocker.patch(
        "grandchallenge.workspaces.crypters.get_random_string",
        return_value="salt",
    )
    c = FernetCrypter()
    e1 = c.encrypt(data="secrets", secret_key="mysecret")
    e2 = c.encrypt(data="secrets", secret_key="mysecret")
    assert e1 != e2


def test_decyption_with_wrong_password():
    c = FernetCrypter()
    encrypted = c.encrypt(data="secrets", secret_key="mysecret")
    with pytest.raises(InvalidToken):
        c.decrypt(encoded=encrypted, secret_key="wrong")


def test_decryption():
    c = FernetCrypter()
    encrypted = c.encrypt(data="secrets", secret_key="mysecret")
    assert c.decrypt(encoded=encrypted, secret_key="mysecret") == "secrets"


def test_wrong_algorithm():
    c = FernetCrypter()
    encrypted = c.encrypt(data="secrets", secret_key="mysecret")

    c.algorithm = SHA512

    with pytest.raises(ValueError):
        c.decrypt(encoded=encrypted, secret_key="mysecret")


def test_wrong_iterations():
    c = FernetCrypter()
    encrypted = c.encrypt(data="secrets", secret_key="mysecret")

    c.iterations = 1

    with pytest.raises(ValueError):
        c.decrypt(encoded=encrypted, secret_key="mysecret")


def test_separator_in_salt(mocker):
    mocker.patch(
        "grandchallenge.workspaces.crypters.get_random_string",
        return_value="$alt",
    )
    c = FernetCrypter()

    with pytest.raises(ValueError):
        c.encrypt(data="secrets", secret_key="mysecret")
