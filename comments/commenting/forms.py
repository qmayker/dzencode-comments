from captcha.fields import CaptchaField
from django import forms

from commenting.validators import FileFormatData


class CommentCreateForm(forms.Form):
    captcha = CaptchaField()
    additional_file = forms.FileField(
        label="Файл (необов'язково)",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ",".join(
                    f".{extension}"
                    for extension in sorted(
                        FileFormatData.get_all_formats().all_formats
                    )
                )
            }
        ),
    )
    username = forms.CharField(
        label="Ім'я",
        max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Електронна пошта",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    home_page = forms.URLField(
        label="Домашня сторінка",
        required=False,
        widget=forms.URLInput(attrs={"autocomplete": "url"}),
    )
    text = forms.CharField(
        label="Коментар",
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
