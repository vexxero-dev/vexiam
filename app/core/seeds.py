from app.domains.applications.models import Application, ApplicationType
from app.domains.subscriptions.models import Plan, OwnerType
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
        "code": "STARTER",
        "name": "Starter Plan",
        "description": "Ideal for single-location businesses starting out.",
        "max_seats": 3,
        "max_devices": 1,
        "price_cents": 2900,
        "currency": "USD",
        "billing_interval": "month",
        "owner_type": OwnerType.ORGANIZATION,
    },
    {
        "code": "GROWTH",
        "name": "Growth Business",
        "description": "Multi-terminal operations with expanding teams and full ecosystem access.",
        "max_seats": 10,
        "max_devices": 3,
        "price_cents": 7900,
        "currency": "USD",
        "billing_interval": "month",
        "owner_type": OwnerType.ORGANIZATION,
    },
    {
        "code": "ENTERPRISE",
        "name": "Enterprise Suite",
        "description": "High-velocity multi-branch enterprise deployment with tailored device seat quotas.",
        "max_seats": 50,
        "max_devices": 15,
        "price_cents": 19900,
        "currency": "USD",
        "billing_interval": "month",
        "owner_type": OwnerType.ORGANIZATION,
    },
]


async def seed_vexxero_defaults(session):
    # Seed default applications
    for app_data in DEFAULT_ECOSYSTEM_APPS:
        stmt = select(Application).where(Application.code == app_data["code"])
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            app = Application(
                code=app_data["code"],
                name=app_data["name"],
                description=app_data["description"],
                type=app_data["type"],
                is_active=True,
            )
            session.add(app)

    # Seed default plans
    for plan_data in DEFAULT_PLANS:
        stmt = select(Plan).where(Plan.code == plan_data["code"])
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            plan = Plan(
                code=plan_data["code"],
                name=plan_data["name"],
                description=plan_data["description"],
                max_seats=plan_data["max_seats"],
                max_devices=plan_data["max_devices"],
                price_cents=plan_data["price_cents"],
                currency=plan_data["currency"],
                billing_interval=plan_data["billing_interval"],
                owner_type=plan_data["owner_type"],
                is_active=True,
            )
            session.add(plan)

    await session.commit()
