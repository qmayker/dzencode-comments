from django.core import validators


class UserNameValidator(validators.RegexValidator):
    regex = r"^[a-zA-Z0-9]+$"
    message = "Имя пользователя должно содержать только латинские буквы и цифры."
    flags = 0
