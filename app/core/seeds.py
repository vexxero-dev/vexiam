from app.domains.applications.models import Application, ApplicationType
from app.domains.subscriptions.models import Plan
from sqlalchemy import select

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

    await session.commit()
