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


class RequestEmailOrSMSVerificationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels


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


class ConfirmPasswordResetInput(BaseModel):
    channel: PasswordResetChannels
    email: EmailStr
    token: str = Field(min_length=6, max_length=12)
    new_password: str = Field(min_length=8, max_length=25, alias="newPassword")

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

    class Config:
        allow_population_by_field_name = True


class UserDBModel(UserBaseModel):
    uid: str = Field(default_factory=get_uuid4)
    role: UserRoles = Field(default=UserRoles.USER)
    level : UserLevels = Field(default=UserLevels.BRONZE)
    account_number: Union[str, None] = Field(
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
