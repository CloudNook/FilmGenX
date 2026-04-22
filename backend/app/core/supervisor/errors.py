"""Supervisor core error types."""

from __future__ import annotations


class SupervisorRuntimeError(Exception):
    """Base error for supervisor runtime failures."""


class SupervisorInvalidStateError(SupervisorRuntimeError):
    """Raised when a workflow cannot transition from its current state."""


class SupervisorInterruptNotFoundError(SupervisorRuntimeError):
    """Raised when a resume was requested but no interrupt checkpoint exists."""


class SupervisorSessionNotFoundError(SupervisorRuntimeError):
    """Raised when a supervisor session cannot be found."""
