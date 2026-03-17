"""Organization-domain models.

Implements multi-tenant organization isolation with invite-code joins:
users → organizations → organization_members.

Documents and analysis runs carry an ``organization_id`` FK so that all
user data is scoped to the organization the user is operating in.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


# ── User ─────────────────────────────────────────────────────────────

class User(TimestampMixin, Base):
    """A platform user identified by email.

    For the POC the backend auto-upserts a ``User`` row whenever
    ``X-User-Email`` is seen for the first time.  When real OAuth
    lands this model gains ``provider``, ``avatar_url``, etc.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # relationships
    owned_organizations: Mapped[list["Organization"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ── Organization ─────────────────────────────────────────────────────

class Organization(TimestampMixin, Base):
    """A tenant organization — all documents & runs are scoped here."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # relationships
    owner: Mapped["User"] = relationship(back_populates="owned_organizations")
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


# ── Organization Member ─────────────────────────────────────────────

class OrganizationMember(TimestampMixin, Base):
    """Join table: which users belong to which organizations.

    No ``role`` column yet — can be added later without schema breakage.
    """

    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )

    # relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
