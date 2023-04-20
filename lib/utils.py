# Path: utils.py

import phonenumbers
from random import randint
from datetime import datetime, timezone
from uuid import uuid4
from cryptography.hazmat.primitives import hashes


def gen_acct_number():
    nums = ""

    for n in range(11):
        if n < 2:
            nums += str(randint(0, 3))

        else:
            nums += str(randint(0, 9))

    return nums


def hash_password(password:  str):
    _password = password.encode()
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(_password)
    return hasher.finalize().hex()


def get_utc_timestamp():
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()


def get_uuid4():
    return str(uuid4())


def get_uuids(count):
    return [get_uuid4() for _ in range(count)]


def passes_phonenumber_test(phone_number):
    try:
        if phonenumbers.is_valid_number(phonenumbers.parse(phone_number)):
            return True
    except phonenumbers.phonenumberutil.NumberParseException:
        return False
