"""Repository for organization-domain persistence.

Handles user upsert, organization CRUD, membership checks, and
invite-code lookups.  Each method flushes but never commits.
"""

from __future__ import annotations

import secrets
import string
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import User, Organization, OrganizationMember


def _generate_invite_code(length: int = 8) -> str:
    """Return a URL-safe alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class OrganizationRepo:
    """Thin data-access layer for organization-domain tables."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── User ─────────────────────────────────────────────────────────

    def upsert_user(self, email: str) -> User:
        """Return existing user or create a new one by email."""
        stmt = select(User).where(User.email == email)
        user = self._db.scalars(stmt).first()
        if user:
            return user
        user = User(email=email)
        self._db.add(user)
        self._db.flush()
        return user

    # ── Organization ─────────────────────────────────────────────────

    def create_organization(
        self,
        *,
        name: str,
        owner: User,
    ) -> Organization:
        """Create an organization, generate invite code, add owner as member."""
        org = Organization(
            name=name,
            invite_code=_generate_invite_code(),
            owner_user_id=owner.id,
        )
        self._db.add(org)
        self._db.flush()

        # Owner is automatically a member
        self.add_member(organization_id=org.id, user_id=owner.id)
        return org

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        """Return an organization by primary key."""
        return self._db.get(Organization, organization_id)

    def get_by_invite_code(self, invite_code: str) -> Organization | None:
        """Find an organization by its invite code."""
        stmt = select(Organization).where(Organization.invite_code == invite_code)
        return self._db.scalars(stmt).first()

    def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        """Return all organizations a user is a member of."""
        stmt = (
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    # ── Membership ───────────────────────────────────────────────────

    def is_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return ``True`` if the user belongs to the organization."""
        stmt = (
            select(OrganizationMember.id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            .limit(1)
        )
        return self._db.scalars(stmt).first() is not None

    def add_member(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationMember:
        """Add a user to an organization (idempotent)."""
        if self.is_member(organization_id, user_id):
            stmt = select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            return self._db.scalars(stmt).one()

        member = OrganizationMember(organization_id=organization_id, user_id=user_id)
        self._db.add(member)
        self._db.flush()
        return member
