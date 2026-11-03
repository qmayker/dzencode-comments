from enum import StrEnum
from logging import getLogger

from core.cache import CacheService
from django.core.cache import cache
from django.db.models import QuerySet
from django.views.generic import ListView

from commenting.forms import CommentCreateForm
from commenting.models import Comment
from commenting.services.models.comment.cache import CommentListCacheData

from .enums import FileTypeEnum

logger = getLogger("comments")


class OrderingType(StrEnum):
    ASC = "asc"
    DESC = "desc"

    @property
    def prefix(self) -> str:
        return "-" if self == OrderingType.DESC else ""

    def build_ordering_name(self, field_name: str):
        return f"{self.prefix}{field_name}"


class CommentListView(ListView):
    model = Comment
    template_name = "commenting/comment/list.html"
    context_object_name = "comment_list"
    paginate_by = 25
    ordering_fields = {
        "username": "author__username",
        "email": "author__email",
        "created": "created_at",
    }

    def _get_ordering(self, field: str | None, ordering_type: str | None):
        if field not in self.ordering_fields:
            return
        try:
            selected_ordering = OrderingType(ordering_type)
        except ValueError:
            return
        ordering_field = self.ordering_fields[field]
        return selected_ordering.build_ordering_name(ordering_field)

    def get_queryset(self) -> QuerySet[Comment]:
        return (
            super()
            .get_queryset()
            .main_comments()
            .prefetch_related(
                "replies__author",
                "replies__target_comment__author",
            )
        )

    def paginate_queryset(self, queryset: QuerySet[Comment], page_size: int):
        pagination = super().paginate_queryset(queryset, page_size)
        if pagination is None:
            return None

        paginator, page, object_list, is_paginated = pagination
        ordering = self.get_ordering()
        cache_data = CommentListCacheData(
            kwargs={
                "version": str(cache.get(CommentListCacheData.version_key, 0)),
                "ordering": ",".join(ordering) if ordering else "default",
                "page": str(page.number),
            }
        )
        cache_service: CacheService[list[Comment]] = CacheService(cache_data)
        cached_comments = cache_service.get_value()
        if cached_comments is not None:
            page.object_list = cached_comments
            return paginator, page, cached_comments, is_paginated

        comments = list(object_list)
        cache_service.set_value(comments)
        page.object_list = comments
        return paginator, page, comments, is_paginated

    def get_ordering(self):
        ordering = self._get_ordering(
            self.request.GET.get("field"), self.request.GET.get("orderingType")
        )
        if ordering is None:
            return super().get_ordering()
        return [ordering]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentCreateForm()
        context["comment_reply_form"] = CommentCreateForm(auto_id="reply_%s")
        context["file_type_enum"] = FileTypeEnum
        return context
