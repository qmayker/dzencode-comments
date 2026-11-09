from captcha.fields import CaptchaField
from django import forms

from commenting.validators import FileFormatData


class CommentCreateForm(forms.Form):
    captcha = CaptchaField()
    additional_file = forms.FileField(
        label="Файл (необязательно)",
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
        label="Имя",
        max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    home_page = forms.URLField(
        label="Домашняя страница",
        required=False,
        widget=forms.URLInput(attrs={"autocomplete": "url"}),
    )
    text = forms.CharField(
        label="Комментарий",
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
