from commenting.models import CommentAuthor

from .create import CommentAuthorService, CreateCommentAuthorService
from .types import AuthorData


def get_or_create(
    username: str, email: str, home_page: str | None = None
) -> CommentAuthor:
    data = AuthorData(email=email, username=username)
    author_obj = CommentAuthor.objects.get_author(data)
    if author_obj is None:
        create_service = CreateCommentAuthorService(
            username=username, email=email, home_page=home_page
        )
        return create_service.create()
    author_service = CommentAuthorService(author_obj)
    if home_page is not None and author_obj.home_page != home_page:
        author_service.update_home_page_url(home_page)
    return author_obj
