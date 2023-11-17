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

    "transfer": {
        'subject': "Transfer Notification",
        'mail_from': settings.mail_from,
        'template_name': "transfer.html",
    },

    "login": {
        'subject': "Login Notification",
        'mail_from': settings.mail_from,
        'template_name': "sign_in.html",
    },

    "password_change": {
        'subject': "Password Change Notification",
        'mail_from': settings.mail_from,
        'template_name': "password_change.html",
    },

    "transfer_failed": {
        'subject': "Transfer Failed",
        'mail_from': settings.mail_from,
        'template_name': "transfer_failed.html",

    }


}
