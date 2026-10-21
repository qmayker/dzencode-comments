from django.core import validators


class UserNameValidator(validators.RegexValidator):
    regex = r"^[a-zA-Z0-9]+$"
    message = "User Name must contain only Latin letters and digits."
    flags = 0
