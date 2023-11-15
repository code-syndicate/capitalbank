from pydantic import BaseSettings, HttpUrl, AnyUrl


class Settings(BaseSettings):
    debug:  bool = True
    app_name:  str = "Capital Security Bank Limited"
    app_id: str = "capital-security"
    db_name = "capital-security"
    allowed_origins: list[HttpUrl] = ["http://127.0.0.1:7004"]
    base_url: str = "http://localhost:8002"
    db_url: AnyUrl = "mongodb://localhost:4000"
    db_username: str = "default"
    db_password: str = "root"
    password_salt: str = "iamasalt"
    mail_username: str = "WaltonExpress"
    mail_password: str = "mail_pass"
    mail_from: str = "WaltonExpressteam@WaltonExpress.com"
    mail_port: int = 587
    mail_server:  str = "https://mail.com"
    mail_starttls: bool = False
    mail_ssl_tls:  bool = True
    mail_display_name: str = "WaltonExpress"
    mail_domain:  str = "https://mail.com"
    mail_domain_username:  str = "admin"
    totp_length: int = 6
    totp_time_step: int = 2
    sms_api_key: str = ""
    sms_api_url: HttpUrl = "https://sms.com"
    jwt_secret_key: str = "jwtsecretkey"
    jwt_access_token_expiration_hours: int = 1
    per_page: int = 5
    session_cookie_name: str = "capital_security_session"

    class Config:
        env_file = ".env"
