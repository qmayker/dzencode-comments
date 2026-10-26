from abc import ABC
from typing import ClassVar

from django.db.models import Model

from .validators import BaseValidator


class BaseModelService[M: Model](ABC):
    validator_class: ClassVar[type[BaseValidator[M]] | None] = None

    def validate(self) -> None:
        if self.validator_class is None:
            raise NotImplementedError("")
        self.validator_class(self.obj).validate()

    def __init__(self, obj: M):
        self.obj = obj

    def clean(self) -> None:
        pass

    def save(self, update_fields: list[str] | None = None) -> M:
        self.validate()
        self.clean()
        self.obj.save(update_fields=update_fields)
        return self.obj


class BaseModelCreateService[M: Model](BaseModelService[M], ABC):
    model: M

    def create(self) -> M:
        return self.save()
