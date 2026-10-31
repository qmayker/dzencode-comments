from commenting.models import CommentAuthor
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


class CommentAuthorAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        token_string = auth_header.split(" ", 1)[1]

        try:
            token = AccessToken(token_string)
            author_id = token["author_id"]

            author = CommentAuthor.objects.get(pk=author_id)

        except (TokenError, KeyError, CommentAuthor.DoesNotExist):
            raise AuthenticationFailed("Invalid token.")

        return (author, token)
