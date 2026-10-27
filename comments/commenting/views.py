from enum import StrEnum

from django.db.models import QuerySet
from django.views.generic import ListView

from commenting.forms import CommentCreateForm
from commenting.models import Comment


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
        return super().get_queryset().main_comments()

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
        return context
