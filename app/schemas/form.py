import inspect
from typing import Type

from fastapi import Form
from pydantic import BaseModel, create_model


def as_form(cls: Type[BaseModel]):
    """
    Adds an `as_form` class method to decorated Pydantic models.
    The `as_form` class method can be used with FastAPI's `Depends`.
    """
    new_params = [
        inspect.Parameter(
            field.alias or name,
            inspect.Parameter.POSITIONAL_ONLY,
            default=Form(
                field.default,
                alias=field.alias or name,
                description=field.description,
                **(field.json_schema_extra or {})
            ),
        )
        for name, field in cls.model_fields.items()
    ]

    async def _as_form(**data):
        return cls(**data)

    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    setattr(cls, "as_form", _as_form)
    return cls 