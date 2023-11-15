from models.settings import Settings


settings = Settings()

EMAIL_DEFS = {
    "verify_email": {
        'subject': "Verify Your Email",
        'mail_from': settings.mail_from,
        'template_name': "verify_email.html",
    },


    "password_reset": {
        'subject': "Reset your password",
        'mail_from': settings.mail_from,
        'template_name': "password_reset.html",
    },


}
