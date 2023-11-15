from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from enum import Enum
from typing import Union
from models.settings import Settings
from lib.utils import *


settings = Settings()


class UserRoles(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    NONE = "none"


class AuthProviders(str, Enum):
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    DEFAULT = "DEFAULT"


class Genders(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class PasswordResetChannels(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class TxType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ActionIdentifiers(str, Enum):
    RESET_PASSWORD_VIA_EMAIL = "RESET_PASSWORD_VIA_EMAIL"
    RESET_PASSWORD_VIA_SMS = "RESET_PASSWORD_VIA_SMS"
    VERIFY_ACCOUNT_VIA_EMAIL = "VERIFY_ACCOUNT_VIA_EMAIL"
    VERIFY_ACCOUNT_VIA_PHONE = "VERIFY_ACCOUNT_VIA_PHONE"
    CONFIRM_EMAIL_VERIFICATION = "CONFIRM_EMAIL_VERIFICATION"
    CONFIRM_PHONE_VERIFICATION = "CONFIRM_PHONE_VERIFICATION"


class UserLevels(str, Enum):
    GOLD = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"
    DIAMOND = "DIAMOND"
    PLATINUM = "PLATINUM"


class QueueStatus(str, Enum):
    QUEUED = "QUEUED"
    FAILED = "FAILED"


class TxStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RequestEmailOrSMSVerificationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels


class TransferInputBase(BaseModel):
    amount: float
    description: Union[str, None] = None


class TransferInput1(TransferInputBase):
    receiver: EmailStr


class TransferInput2(TransferInputBase):
    receiver_bank_name: str
    receiver_account_number: str
    receiver_account_name: str
    scope: str


class UserOTP(BaseModel):
    user: EmailStr
    otp: str = Field(default_factory=gen_otp)
    is_valid:  bool = True


class InFiatTransfer(BaseModel):
    tx_id: str = Field(default_factory=get_uuid4)
    amount: float
    txtype: TxType = TxType.DEBIT
    sender: EmailStr
    receiver: EmailStr
    status: TxStatus = TxStatus.PENDING
    created: str = Field(default_factory=get_utc_timestamp)
    updated: str = Field(default_factory=get_utc_timestamp)
    description: Union[str, None] = "Internal Transfer"
    scope: str = "IN"
    approved: bool = False

    class Config:
        allow_population_by_field_name = True


class OutFiatTransfer(BaseModel):
    tx_id: str = Field(default_factory=get_uuid4)
    amount: float
    txtype: TxType = TxType.DEBIT
    sender: EmailStr
    receiver_bank_name: str
    receiver_account_number: str
    receiver_account_name: str
    status: TxStatus = TxStatus.PENDING
    created: str = Field(default_factory=get_utc_timestamp)
    updated: str = Field(default_factory=get_utc_timestamp)
    description: Union[str, None] = "External Transfer"
    scope: str = "OUT"
    approved: bool = False

    class Config:
        allow_population_by_field_name = True


class PasswordResetInput(BaseModel):
    email:  EmailStr
    password:  str = Field(min_length=8, alias="password")
    password2:  str = Field(min_length=8, alias="password2")

    class Config:
        allow_population_by_field_name = True

    @validator('password2')
    def validate_password2(cls, v, values):
        if not v:
            return v

        if values.get("password") != v:
            raise ValueError(" Password fields must match!")

        return v


class PasswordResetStore(PasswordResetInput):
    uid: str = Field(default_factory=get_uuid4)

    class Config:
        allow_population_by_field_name = True


class RequestEmailOrSMSVerificationOutput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    status: QueueStatus = QueueStatus.QUEUED


class VerifyEmailOrSMSConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    token: str = Field(min_length=6, max_length=12)


class RequestAccountConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels


class RequestAccountConfirmationOutput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    status: QueueStatus = QueueStatus.QUEUED


class VerifyAccountConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    token: str = Field(min_length=6, max_length=12)


class RequestPasswordResetInput(BaseModel):
    email: EmailStr
    channel: PasswordResetChannels


class CreateUserViaGoogleAuthInput(BaseModel):
    token: str = Field(min_length=16)


class ATMCard(BaseModel):
    card_type: str = Field(default="DEBIT")
    card_number: str = Field(
        default_factory=gen_card_number, min_length=16, )
    cvv: str = Field(default_factory=gen_cvv, min_length=3, max_length=3)
    expiry_date: str = Field(
        default_factory=gen_card_expiry_date, min_length=7, max_length=7)
    pin: str = Field(default_factory=gen_pin, min_length=4, max_length=4)

    class Config:
        allow_population_by_field_name = True


def create_cards():
    cards = []

    for n in range(1, 3):
        cards.append(ATMCard(card_type="DEBIT" if n % 2 == 0 else "CREDIT"))

    return cards


class BankTransfer(BaseModel):

    bank_name: str = Field(default="GTBank")
    account_name: str = Field(default="John Doe")
    account_number: str = Field(default="0123456789")
    account_type: str = Field(default="SAVINGS")

    sender:  Union[EmailStr, None] = Field(default=None)
    type: str = Field(default="DEBIT")

    class Config:
        allow_population_by_field_name = True


class ChangePasswordInput(BaseModel):
    old_password: str = Field(min_length=8, max_length=25, alias="oldpassword")

    password: str = Field(min_length=8, max_length=25, alias="newpassword")
    password2: str = Field(
        min_length=8, max_length=25, alias="confirmpassword")
    otp: str = Field(default=None, min_length=4, max_length=12)

    class Config:
        allow_population_by_field_name = True


class TOTPDB(BaseModel):
    uid: str = Field(default_factory=get_uuid4, min_length=32)
    action_id: ActionIdentifiers = Field(min_length=8, alias="actionId")
    author: str = Field(min_length=8)
    key: str = Field(min_length=32)
    time_step: int = Field(default=settings.totp_time_step, alias="timeStep")
    created: float = Field(default_factory=get_utc_timestamp)

    class Config:
        allow_population_by_field_name = True


class UserBaseModel(BaseModel):

    """ User Model """
    firstname: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    lastname: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    phone: Union[str, None] = Field(default=None, min_length=8, max_length=15)
    email: EmailStr
    date_of_birth:  Union[str, None] = Field(default=None, alias="dateOfBirth")

    @validator('phone')
    def validate_phone(v, values):
        return v
        value = v

        if value is None:
            return value

        if not passes_phonenumber_test(value):
            raise ValueError("invalid phone number")

        return value

    class Config:
        allow_population_by_field_name = True


class UserInputModel(UserBaseModel):
    password: str = Field(min_length=8, max_length=25)
    password2: str = Field(min_length=8, max_length=25)
    is_admin: bool = Field(default=False, alias="isAdmin")

    class Config:
        allow_population_by_field_name = True


class DeleteUserModel(BaseModel):
    email: EmailStr


class TickTxModel(BaseModel):
    tx_id: str = Field(alias="txId")

    class Config:
        allow_population_by_field_name = True


class UpdateTxModel(BaseModel):
    tx_id: str = Field(alias="txId")
    sender:  str
    receiver: str
    amount:  float
    scope: str
    status: TxStatus
    txtype: TxType
    created: Union[str, None] = Field(default=None, alias="created")

    class Config:
        allow_population_by_field_name = True


class UpdateUserModel(BaseModel):
    uid: str
    balance: float
    credit_limit: float = Field(alias='creditLimit')
    total_expense: float = Field(alias='totalExpense')
    total_income: float = Field(alias='totalIncome')

    class Config:
        allow_population_by_field_name = True


class UserDBModel(UserBaseModel):
    uid: str = Field(default_factory=get_uuid4)
    role: UserRoles = Field(default=UserRoles.USER)
    level: UserLevels = Field(default=UserLevels.BRONZE)
    account_number: str = Field(
        default_factory=gen_acct_number, alias="accountNumber")
    address: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    country: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    avatarUrl: Union[HttpUrl, None] = Field(default=None)
    gender: Union[Genders, None] = None
    activation_channel: Union[PasswordResetChannels, None] = Field(
        default=None, alias="activationChannel")
    is_superuser: bool = Field(default=False, alias="isSuperuser")
    is_verified: bool = Field(default=False, alias="isVerified")
    email_verified: bool = Field(default=False, alias="emailVerified")
    phone_verified: bool = Field(default=False, alias="phoneVerified")
    password_hash: Union[None, str] = Field(
        default=None, min_length=32, alias="passwordHash")
    is_active: bool = Field(default=False, alias="isActive")
    created: float = Field(default_factory=get_utc_timestamp)
    last_login: Union[float, None] = Field(alias="lastLogin", default=None)
    true_last_login: Union[float, None] = Field(
        alias="trueLastLogin", default=None)
    last_updated: float = Field(
        default_factory=get_utc_timestamp, alias="lastUpdated")
    cards: list[ATMCard] = Field(default_factory=create_cards)
    balance: float = Field(default=0.0)
    credit_limit: float = Field(default=0.0)
    total_income: float = Field(default=0.0)
    total_expense: float = Field(default=0.0)

    @validator('phone')
    def validate_phone(v, values):
        return v
        value = v

        if value is None:
            return value

        if not passes_phonenumber_test(value):
            raise ValueError("invalid phone number")

        return value

    class Config:
        allow_population_by_field_name = True


# Authentication Related Models


class AuthSession(BaseModel):
    uid: str = Field(alias="uid", default_factory=get_uuid4)
    user_id: str = Field(alias="userId")
    is_valid: bool = Field(alias="isValid", default=True)
    created: float = Field(default_factory=get_utc_timestamp)
    duration_in_hours: float = Field(alias="durationInHours")
    last_used: Union[float, None] = Field(alias="lastUsed", default=None)
    usage_count: int = Field(alias="usageCount", default=0)

    class Config:
        allow_population_by_field_name = True


class RequestAccessTokenInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=25)

    class Config:
        allow_population_by_field_name = True


class AccessToken(BaseModel):
    access_token: str
    token_type: str

    class Config:
        allow_population_by_field_name = True


class Throttler(BaseModel):
    action: str
    author: str
    action_id: ActionIdentifiers = Field(alias="actionId")
    last_request: Union[float, None] = Field(alias="lastRequest", default=None)
    requests_count: int = Field(alias="requestsCount", default=0)
    pauseRequests: bool = Field(alias="pauseRequests", default=False)

    class Config:
        allow_population_by_field_name = True


class AuthenticationContext(BaseModel):

    session: AuthSession
    user: UserDBModel
