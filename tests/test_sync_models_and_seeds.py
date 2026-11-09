import pytest
from app.core.seeds import seed_vexxero_defaults, DEFAULT_POS_PERMISSIONS, DEFAULT_POS_ROLES
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.applications.models import Application, ApplicationRole, Permission, role_permissions


@pytest.mark.asyncio
async def test_pos_roles_and_permissions_seeded(db_session):
    # Seed ecosystem defaults in session
    await seed_vexxero_defaults(db_session)

    # Verify VEX-POS is seeded with canonical permissions and roles
    stmt = select(Application).where(Application.code == "VEX-POS")
    res = await db_session.execute(stmt)
    pos_app = res.scalar_one_or_none()
    assert pos_app is not None

    # Verify all pos.* permissions exist
    perm_stmt = select(Permission).where(Permission.application_id == pos_app.id)
    perm_res = await db_session.execute(perm_stmt)
    perms = perm_res.scalars().all()
    perm_codes = {p.code for p in perms}
    for expected_perm in DEFAULT_POS_PERMISSIONS:
        assert expected_perm["code"] in perm_codes

    # Verify standard roles exist with correct role_version and permissions using eager load
    role_stmt = select(ApplicationRole).options(selectinload(ApplicationRole.permissions)).where(ApplicationRole.application_id == pos_app.id)
    role_res = await db_session.execute(role_stmt)
    roles = role_res.scalars().all()
    role_map = {r.code: r for r in roles}

    for expected_role in DEFAULT_POS_ROLES:
        role_code = expected_role["code"]
        assert role_code in role_map
        role = role_map[role_code]
        assert role.role_version >= 1
        
        # Query role permissions directly via association table in async session
        subq = (
            select(Permission.code)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .where(role_permissions.c.role_id == role.id)
        )
        assigned_perm_codes = set((await db_session.execute(subq)).scalars().all())
        for p in expected_role["permissions"]:
            assert p in assigned_perm_codes

