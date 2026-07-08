from dataclasses import dataclass, field, fields
from enum import StrEnum
from typing import Any, Self, override

from mpt_extension_contrib.custom_notifications import NotificationsContextMixin
from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import AgreementContext


class InstallationActionType(StrEnum):
    """Supported installation side effect intents."""

    NOTIFY_NON_RECOVERABLE_FAILURE = "NotifyNonRecoverableFailure"


@dataclass(frozen=True)
class InstallationAction:
    """Structured installation side effect intent declared by pipeline steps."""

    target: InstallationActionType
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstallationState:
    """Mutable installation state shared across pipeline steps."""

    action: InstallationAction | None = None
    handled: bool = False


@dataclass(kw_only=True)
class InstallationAgreementContext(  # type: ignore[misc]
    NotificationsContextMixin, AgreementContext, ContextAdapter
):
    """Agreement event context extended with the installation workflow state."""

    installation_state: InstallationState = field(default_factory=InstallationState)

    @override
    @classmethod
    def from_context(cls, ctx: AgreementContext) -> Self:
        context_fields = {
            context_field.name: getattr(ctx, context_field.name)
            for context_field in fields(ctx)
            if context_field.init and context_field.name != "installation_state"
        }
        return cls(**context_fields)
