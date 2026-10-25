from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from django.db.models import Model

ModelT = TypeVar("ModelT", bound=Model)


class BaseValidator(ABC, Generic[ModelT]):
    def __init__(self, obj: ModelT):
        self.obj = obj

    @abstractmethod
    def validate(self) -> None:
        raise NotImplementedError
