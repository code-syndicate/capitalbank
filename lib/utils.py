# Path: utils.py

import phonenumbers
from random import randint
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from cryptography.hazmat.primitives import hashes


def gen_card_number():
    nums = ""

    for n in range(16):
        if n < 6:
            nums += str(randint(0, 3))

        else:
            nums += str(randint(0, 9))

        k = ("".join(nums.split(" "))).strip()
        if len(k) % 4 == 0 and len(k) != 16 and len(k) != 0:
            nums += "   "

    return nums


def gen_cvv():
    nums = ""

    for n in range(3):
        nums += str(randint(0, 9))

    return nums


def gen_pin():
    nums = ""

    for n in range(4):
        nums += str(randint(0, 9))

    return nums


def gen_card_expiry_date():
    now = datetime.now()
    new_date = now + timedelta(days=(365*3))

    return new_date.strftime("%m / %y")


def gen_acct_number():
    nums = ""

    for n in range(12):
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
