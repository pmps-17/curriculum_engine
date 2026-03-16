"""Repository for workspace-domain persistence.

Handles user upsert, workspace CRUD, membership checks, and
invite-code lookups.  Each method flushes but never commits.
"""

from __future__ import annotations

import secrets
import string
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import User, Workspace, WorkspaceMember


def _generate_invite_code(length: int = 8) -> str:
    """Return a URL-safe alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class WorkspaceRepo:
    """Thin data-access layer for workspace-domain tables."""

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

    # ── Workspace ────────────────────────────────────────────────────

    def create_workspace(
        self,
        *,
        name: str,
        owner: User,
    ) -> Workspace:
        """Create a workspace, generate invite code, add owner as member."""
        ws = Workspace(
            name=name,
            invite_code=_generate_invite_code(),
            owner_user_id=owner.id,
        )
        self._db.add(ws)
        self._db.flush()

        # Owner is automatically a member
        self.add_member(workspace_id=ws.id, user_id=owner.id)
        return ws

    def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Return a workspace by primary key."""
        return self._db.get(Workspace, workspace_id)

    def get_by_invite_code(self, invite_code: str) -> Workspace | None:
        """Find a workspace by its invite code."""
        stmt = select(Workspace).where(Workspace.invite_code == invite_code)
        return self._db.scalars(stmt).first()

    def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """Return all workspaces a user is a member of."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    # ── Membership ───────────────────────────────────────────────────

    def is_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return ``True`` if the user belongs to the workspace."""
        stmt = (
            select(WorkspaceMember.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .limit(1)
        )
        return self._db.scalars(stmt).first() is not None

    def add_member(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceMember:
        """Add a user to a workspace (idempotent)."""
        if self.is_member(workspace_id, user_id):
            stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            return self._db.scalars(stmt).one()

        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id)
        self._db.add(member)
        self._db.flush()
        return member
