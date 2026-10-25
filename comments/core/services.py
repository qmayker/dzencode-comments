from abc import ABC, abstractmethod
from typing import ClassVar

from django.db.models import Model

from .validators import BaseValidator


class BaseService[M: Model](ABC):
    @abstractmethod
    def save(self) -> M:
        raise NotImplementedError


class BaseModelService[M: Model](BaseService[M], ABC):
    validator_class: ClassVar[type[BaseValidator[M]] | None] = None

    def __init__(self, obj: M):
        self.obj = obj

    def clean(self) -> None:
        pass

    def validate(self) -> None:
        if self.validator_class is not None:
            self.validator_class(self.obj).validate()

    def save(self, validate: bool = True) -> M:
        if validate:
            self.validate()
        self.clean()
        self.obj.save()
        return self.obj
