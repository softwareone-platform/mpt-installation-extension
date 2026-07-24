from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self


class InstallOutcome(StrEnum):
    """Outcome of an installation attempt."""

    CREATED = "Created"
    ALREADY_EXISTS = "AlreadyExists"


@dataclass(frozen=True)
class FailedInstallation:
    """A failed installation. ``account_id`` is ``None`` for extension-level failures."""

    extension_id: str
    error: str
    account_id: str | None = None


@dataclass
class InstallationReport:
    """Aggregated result of a bulk installation run."""

    created: int = 0
    already_exists: int = 0
    failures: list[FailedInstallation] = field(default_factory=list)

    @classmethod
    def from_extension_error(cls, extension_id: str, error: BaseException) -> Self:
        """Build a report with a single extension-level failure."""
        report = cls()
        report.failures.append(FailedInstallation(extension_id=extension_id, error=str(error)))
        return report

    @classmethod
    def from_outcomes(
        cls,
        extension_id: str,
        account_ids: Sequence[str],
        outcomes: "Sequence[InstallOutcome | BaseException]",
        already_installed: int = 0,
    ) -> Self:
        """Build a report from the per-account outcomes of installing one extension.

        ``already_installed`` counts accounts skipped up front because they already
        had the extension installed.
        """
        report = cls(already_exists=already_installed)
        for account_id, outcome in zip(account_ids, outcomes, strict=True):
            report.record(account_id=account_id, extension_id=extension_id, outcome=outcome)
        return report

    @classmethod
    def from_product_error(cls, extension_ids: Sequence[str], error: BaseException) -> Self:
        """Build a report with one extension-level failure per extension of the product."""
        report = cls()
        for extension_id in extension_ids:
            report.failures.append(FailedInstallation(extension_id=extension_id, error=str(error)))
        return report

    def merge(self, other: Self) -> None:
        """Fold another report into this one."""
        self.created += other.created
        self.already_exists += other.already_exists
        self.failures.extend(other.failures)

    def record(
        self, *, account_id: str, extension_id: str, outcome: "InstallOutcome | BaseException"
    ) -> None:
        """Count a single installation outcome, capturing failures."""
        if isinstance(outcome, BaseException):
            self.failures.append(
                FailedInstallation(
                    account_id=account_id, extension_id=extension_id, error=str(outcome)
                )
            )
        elif outcome == InstallOutcome.CREATED:
            self.created += 1
        else:
            self.already_exists += 1
