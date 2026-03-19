"""Repository for organization-domain persistence.

Handles user upsert, organization CRUD, membership checks, and
invite-code lookups.  Each method flushes but never commits.
"""

from __future__ import annotations

import secrets
import string
import uuid
from typing import Sequence

from sqlalchemy import Row, delete as sa_delete, func, select
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

    def count_members(self, organization_id: uuid.UUID) -> int:
        """Return the total number of members in an organization."""
        stmt = (
            select(func.count())
            .select_from(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
        )
        return self._db.scalar(stmt) or 0

    def remove_member(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove a user from an organization. Returns True if deleted."""
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        member = self._db.scalars(stmt).first()
        if member is None:
            return False
        self._db.delete(member)
        self._db.flush()
        return True

    # ── Mutable fields accepted by update() ────────────────────────
    _MUTABLE_FIELDS: frozenset[str] = frozenset({
        "name", "description",
        "contact_name", "contact_email",
        "country_name", "country_code",
        "state_name", "state_code",
        "city",
    })

    def update(self, org: Organization, **kwargs) -> Organization:
        """Patch mutable fields on an organization. Flushes but does not commit.

        Only fields listed in ``_MUTABLE_FIELDS`` are accepted.
        Any ``None`` value explicitly clears the column.
        """
        for key, value in kwargs.items():
            if key not in self._MUTABLE_FIELDS:
                raise ValueError(f"Field '{key}' is not a mutable organization field.")
            setattr(org, key, value)
        self._db.flush()
        return org

    # ── Member counts (batch) ────────────────────────────────────────

    def member_counts_for_orgs(
        self, organization_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        """Return {org_id: member_count} for a list of org ids."""
        if not organization_ids:
            return {}
        stmt = (
            select(
                OrganizationMember.organization_id,
                func.count().label("cnt"),
            )
            .where(OrganizationMember.organization_id.in_(organization_ids))
            .group_by(OrganizationMember.organization_id)
        )
        rows: Sequence[Row] = self._db.execute(stmt).all()
        return {row[0]: row[1] for row in rows}

    # ── List members ─────────────────────────────────────────────────

    def list_members(
        self, organization_id: uuid.UUID,
    ) -> list[tuple[User, OrganizationMember]]:
        """Return (User, OrganizationMember) pairs for an organization."""
        stmt = (
            select(User, OrganizationMember)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.created_at.asc())
        )
        return list(self._db.execute(stmt).all())

    # ── Delete organization ──────────────────────────────────────────

    def delete_organization(self, organization_id: uuid.UUID) -> None:
        """Hard-delete an organization and clean up all FK references.

        - Nullifies ``organization_id`` on documents and analysis_runs
          (both columns are nullable).
        - Deletes curriculum_sets rows (non-nullable FK).
        - Deletes memberships.
        - Deletes the organization row.
        """
        from app.models.analysis import AnalysisRun
        from app.models.curriculum import Document
        from app.models.curriculum_set import CurriculumSet

        # Nullify org FK on documents and analysis_runs
        self._db.execute(
            Document.__table__.update()
            .where(Document.organization_id == organization_id)
            .values(organization_id=None)
        )
        self._db.execute(
            AnalysisRun.__table__.update()
            .where(AnalysisRun.organization_id == organization_id)
            .values(organization_id=None)
        )

        # Delete curriculum_sets (non-nullable FK)
        self._db.execute(
            sa_delete(CurriculumSet)
            .where(CurriculumSet.organization_id == organization_id)
        )

        # Delete memberships
        self._db.execute(
            sa_delete(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
        )

        # Delete the organization itself
        self._db.execute(
            sa_delete(Organization)
            .where(Organization.id == organization_id)
        )
        self._db.flush()
