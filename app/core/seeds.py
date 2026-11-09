from app.domains.applications.models import Application, ApplicationType, ApplicationRole, Permission, role_permissions
from app.domains.subscriptions.models import Plan
from sqlalchemy import select, insert

DEFAULT_ECOSYSTEM_APPS = [
    {
        "code": "VEX-POS",
        "name": "Vexxero Point of Sale",
        "description": "High-throughput retail and café POS with 100% offline-first execution, ESC/POS hardware print routing, and blind cash drawers.",
        "type": ApplicationType.LOCAL_HYBRID,
    },
    {
        "code": "VEX-ERP",
        "name": "Vexxero Enterprise ERP",
        "description": "Centralized business management, multi-warehouse stock replenishment, procurement workflows, and consolidated financials.",
        "type": ApplicationType.WEB,
    },
    {
        "code": "VEX-PMS",
        "name": "Vexxero Property Management System",
        "description": "Hotel, resort, and guest management system with room inventory and booking operations.",
        "type": ApplicationType.WEB,
    },
    {
        "code": "VEX-FINCLOUD",
        "name": "Vexxero FinCloud",
        "description": "Financial analytics, ledger reconciliation, automated VAT/tax reporting, and banking integration.",
        "type": ApplicationType.WEB,
    },
]

DEFAULT_POS_PERMISSIONS = [
    {"code": "pos.sales.view", "name": "View POS Sales", "description": "View active and past sales transactions."},
    {"code": "pos.sales.create", "name": "Create POS Sale", "description": "Ring up items and complete checkout."},
    {"code": "pos.sales.void", "name": "Void POS Sale", "description": "Void existing line items or active transactions."},
    {"code": "pos.discount.apply", "name": "Apply Standard Discount", "description": "Apply standard discounts within allowable limit."},
    {"code": "pos.discount.override", "name": "Manager Discount Override", "description": "Override maximum discount threshold."},
    {"code": "pos.refund.create", "name": "Initiate Refund", "description": "Create refund request for returned goods."},
    {"code": "pos.refund.approve", "name": "Approve Refund", "description": "Approve refund execution and issue payment."},
    {"code": "pos.shift.open", "name": "Open Cashier Shift", "description": "Open cashier register shift with starting float."},
    {"code": "pos.shift.close", "name": "Close Cashier Shift", "description": "Perform blind drop and close register shift."},
    {"code": "pos.day.close", "name": "Close Business Day", "description": "Finalize daily register reconciliation and z-report."},
    {"code": "pos.reports.view", "name": "View POS Reports", "description": "Access operational and shift analytics."},
    {"code": "pos.products.view", "name": "View Catalog Products", "description": "Browse catalog, pricing, and stock items."},
    {"code": "pos.products.manage", "name": "Manage Products", "description": "Create, edit, or adjust local catalog items."},
    {"code": "pos.settings.manage", "name": "Manage POS Settings", "description": "Configure peripherals, receipts, and terminal options."},
]

DEFAULT_POS_ROLES = [
    {
        "code": "ADMIN",
        "name": "POS Administrator",
        "description": "Full administrative control over POS operations, configurations, and overrides.",
        "permissions": [p["code"] for p in DEFAULT_POS_PERMISSIONS],
    },
    {
        "code": "MANAGER",
        "name": "Store Manager",
        "description": "Store operational supervision, approvals, discounts, shifts, and reports.",
        "permissions": [
            "pos.sales.view", "pos.sales.create", "pos.sales.void",
            "pos.discount.apply", "pos.discount.override",
            "pos.refund.create", "pos.refund.approve",
            "pos.shift.open", "pos.shift.close", "pos.day.close",
            "pos.reports.view", "pos.products.view", "pos.products.manage"
        ],
    },
    {
        "code": "CASHIER",
        "name": "Cashier Operator",
        "description": "Frontline sales checkout, standard discounts, and shift operations.",
        "permissions": [
            "pos.sales.view", "pos.sales.create", "pos.discount.apply",
            "pos.shift.open", "pos.shift.close", "pos.products.view"
        ],
    },
]


DEFAULT_PLANS = [
    {
        "app_code": "VEX-POS",
        "code": "POS-STARTER",
        "name": "Starter POS",
        "description": "Single terminal with 3 operator seats.",
        "user_seats": 3,
        "device_seats": 1,
    },
    {
        "app_code": "VEX-POS",
        "code": "POS-GROWTH",
        "name": "Growth POS",
        "description": "Multi-terminal operations with 10 operator seats and 3 terminal activations.",
        "user_seats": 10,
        "device_seats": 3,
    },
    {
        "app_code": "VEX-POS",
        "code": "POS-ENTERPRISE",
        "name": "Enterprise POS",
        "description": "High-velocity multi-terminal setup with 50 operator seats and 15 device activations.",
        "user_seats": 50,
        "device_seats": 15,
    },
]


async def seed_vexxero_defaults(session):
    # 1. Seed default applications
    created_apps = {}
    for app_data in DEFAULT_ECOSYSTEM_APPS:
        stmt = select(Application).where(Application.code == app_data["code"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            app = Application(
                code=app_data["code"],
                name=app_data["name"],
                description=app_data["description"],
                type=app_data["type"],
                is_active=True,
            )
            session.add(app)
            await session.flush()
            created_apps[app_data["code"]] = app.id
        else:
            created_apps[app_data["code"]] = existing.id

    # 2. Seed default plans linked to applications
    for plan_data in DEFAULT_PLANS:
        stmt = select(Plan).where(Plan.code == plan_data["code"])
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            app_id = created_apps.get(plan_data["app_code"])
            if app_id:
                plan = Plan(
                    application_id=app_id,
                    code=plan_data["code"],
                    name=plan_data["name"],
                    description=plan_data["description"],
                    user_seats=plan_data["user_seats"],
                    device_seats=plan_data["device_seats"],
                )
                session.add(plan)

    # 3. Seed default roles and permissions for VEX-POS
    pos_app_id = created_apps.get("VEX-POS")
    if pos_app_id:
        perm_map = {}
        for perm_data in DEFAULT_POS_PERMISSIONS:
            stmt = select(Permission).where(
                Permission.application_id == pos_app_id,
                Permission.code == perm_data["code"]
            )
            result = await session.execute(stmt)
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(
                    application_id=pos_app_id,
                    code=perm_data["code"],
                    name=perm_data["name"],
                    description=perm_data["description"]
                )
                session.add(perm)
                await session.flush()
            perm_map[perm_data["code"]] = perm

        for role_data in DEFAULT_POS_ROLES:
            stmt = select(ApplicationRole).where(
                ApplicationRole.application_id == pos_app_id,
                ApplicationRole.code == role_data["code"]
            )
            result = await session.execute(stmt)
            role = result.scalar_one_or_none()
            if not role:
                role = ApplicationRole(
                    application_id=pos_app_id,
                    code=role_data["code"],
                    name=role_data["name"],
                    description=role_data["description"],
                    role_version=1
                )
                session.add(role)
                await session.flush()

                # Seed role_permissions directly into the association table to avoid lazy-loading issues
                target_perms = [perm_map[p_code] for p_code in role_data["permissions"] if p_code in perm_map]
                for p in target_perms:
                    await session.execute(
                        insert(role_permissions).values(role_id=role.id, permission_id=p.id)
                    )

    await session.commit()
