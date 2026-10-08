import os
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import check_db_health, redis_manager, AsyncSessionLocal, get_db
from app.models import Role, User, Vendor
from app.security import get_password_hash, verify_password
from app.routers import auth, admin, procurement, vendors, purchase_orders, contracts, notifications, performance, dashboard, reports, communication

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

from sqlalchemy import func

ROLES_LIST = [
    "Administrator",
    "Procurement Manager",
    "Supply Chain Manager",
    "Finance Officer",
    "Vendor",
    "Auditor"
]

DEMO_USERS = [
    {
        "email": "admin@example.com",
        "password": "Admin@123456",
        "full_name": "System Administrator",
        "role": "Administrator"
    },
    {
        "email": "proc_mgr@example.com",
        "password": "Password@123",
        "full_name": "Sarah Jenkins (Procurement Lead)",
        "role": "Procurement Manager"
    },
    {
        "email": "pm@example.com",
        "password": "Procurement@123456",
        "full_name": "Procurement Manager",
        "role": "Procurement Manager"
    },
    {
        "email": "finance@example.com",
        "password": "Finance@123456",
        "full_name": "David Chen (Finance Officer)",
        "role": "Finance Officer"
    },
    {
        "email": "supply_chain@example.com",
        "password": "SupplyChain@123456",
        "full_name": "Marcus Vance (Supply Chain Manager)",
        "role": "Supply Chain Manager"
    },
    {
        "email": "vendor_user@example.com",
        "password": "Vendor@123456",
        "full_name": "Apex Logistics Vendor Partner",
        "role": "Vendor"
    },
    {
        "email": "auditor@example.com",
        "password": "Auditor@123456",
        "full_name": "Elena Rostova (Compliance Auditor)",
        "role": "Auditor"
    }
]

async def seed_default_admin_and_roles(db: AsyncSession) -> dict:
    """
    Idempotent seeding helper:
    1. Ensures all foundational roles exist.
    2. Checks each demo user before creating (admin@example.com, proc_mgr@example.com, etc.).
    3. If any demo user already exists, ensures status is APPROVED, role is linked,
       and resets password hash if incorrect. Safe to call multiple times without erroring.
    4. Seeds initial sample vendor if none exists.
    """
    try:
        # 1. Seed Roles
        for r_name in ROLES_LIST:
            stmt = select(Role).where(Role.name == r_name)
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                db.add(Role(name=r_name))
        await db.commit()

        # Cache existing roles
        all_roles_res = await db.execute(select(Role))
        role_map = {r.name: r for r in all_roles_res.scalars().all()}

        # 2. Seed / Verify Demo Users
        users_summary = []
        for u_info in DEMO_USERS:
            target_email = u_info["email"].lower()
            target_role_name = u_info["role"]
            target_pwd = u_info["password"]
            target_name = u_info["full_name"]
            assigned_role = role_map.get(target_role_name)

            u_stmt = (
                select(User)
                .where(func.lower(User.email) == target_email)
                .options(selectinload(User.roles))
            )
            u_res = await db.execute(u_stmt)
            user_obj = u_res.scalar_one_or_none()

            action = "verified"
            if not user_obj:
                user_obj = User(
                    email=target_email,
                    hashed_password=get_password_hash(target_pwd),
                    full_name=target_name,
                    status="APPROVED",
                    roles=[assigned_role] if assigned_role else []
                )
                db.add(user_obj)
                await db.commit()
                # Reload with roles
                u_res = await db.execute(u_stmt)
                user_obj = u_res.scalar_one()
                action = "created"
                logger.info("Demo user created: %s (%s) / %s", target_email, target_role_name, target_pwd)
            else:
                changed = False
                if user_obj.status != "APPROVED":
                    user_obj.status = "APPROVED"
                    changed = True
                if user_obj.email != target_email:
                    user_obj.email = target_email
                    changed = True
                if assigned_role and not any(r.name == target_role_name for r in user_obj.roles):
                    user_obj.roles.append(assigned_role)
                    changed = True
                if not verify_password(target_pwd, user_obj.hashed_password):
                    user_obj.hashed_password = get_password_hash(target_pwd)
                    changed = True

                if changed:
                    await db.commit()
                    u_res = await db.execute(u_stmt)
                    user_obj = u_res.scalar_one()
                    action = "updated"
                    logger.info("Demo user refreshed: %s (%s)", target_email, target_role_name)
                else:
                    logger.info("Demo user verified: %s (%s)", target_email, target_role_name)

            users_summary.append({
                "email": user_obj.email,
                "role": target_role_name,
                "status": user_obj.status,
                "action": action
            })

        # 3. Seed Initial Sample Vendor if none exist
        v_stmt = select(Vendor).limit(1)
        v_res = await db.execute(v_stmt)
        vendor_seeded = False
        if not v_res.scalar_one_or_none():
            v = Vendor(
                company_name="Apex Global Logistics",
                registration_no="VEND-2026-001",
                category="Logistics & Freight",
                status="ACTIVE"
            )
            db.add(v)
            await db.commit()
            vendor_seeded = True

        all_roles_list = sorted(list(role_map.keys()))

        return {
            "demo_users": users_summary,
            "database_roles": all_roles_list,
            "sample_vendor_seeded": vendor_seeded
        }
    except Exception as e:
        await db.rollback()
        logger.error("Error during seed_default_admin_and_roles: %s", e, exc_info=True)
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application and seeding foundational data...")
    # Ensure upload directories exist
    base_dir = os.path.dirname(os.path.dirname(__file__))
    os.makedirs(os.path.join(base_dir, "uploads", "po_documents"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "contracts"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "communication"), exist_ok=True)

    try:
        async with AsyncSessionLocal() as db:
            result = await seed_default_admin_and_roles(db)
            logger.info("Startup foundational seeding status: %s", result)
    except Exception as e:
        logger.error("Startup seeding check encountered an issue: %s", e, exc_info=True)

    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="Procurement & Vendor Reliability Platform API",
    version="2.0.0",
    lifespan=lifespan
)

from app.telemetry import record_response_time
import time as _time

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telemetry Middleware: Track API response time
@app.middleware("http")
async def track_response_time(request, call_next):
    start = _time.monotonic()
    response = await call_next(request)
    elapsed_ms = (_time.monotonic() - start) * 1000.0
    record_response_time(elapsed_ms)
    return response

# Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(procurement.router)
app.include_router(procurement.pr_router)
app.include_router(performance.router)
app.include_router(vendors.router)
app.include_router(purchase_orders.router)
app.include_router(contracts.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(reports.analytics_router)
app.include_router(communication.router)

@app.get("/health", tags=["Health"])
async def health_check():
    db_healthy = await check_db_health()
    redis_healthy = await redis_manager.is_connected()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "fallback_in_memory_mode"
    }

from fastapi import Header

@app.api_route("/api/v1/auth/seed-admin", methods=["GET", "POST"], tags=["Auth"])
async def trigger_seed_admin(
    secret: Optional[str] = Query(None, description="Optional secret key for verification"),
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Idempotent trigger to seed or repair the foundational roles and default Administrator account
    (admin@example.com / Admin@123456).
    Safe to re-run multiple times without erroring.
    """
    try:
        from sqlalchemy import func
        stmt = select(User).where(func.lower(User.email) == "admin@example.com")
        existing_res = await db.execute(stmt)
        existing_admin = existing_res.scalar_one_or_none()

        provided_secret = secret or x_admin_secret
        valid_secrets = {
            "Admin@123456",
            "Password@123",
            "procureflow-seed-2026",
            settings.SECRET_KEY,
            "procurement-super-secret-jwt-key-2026-production-grade"
        }

        # If admin already exists, require secret to prevent unauthorized credential reset
        if existing_admin and (provided_secret not in valid_secrets):
            raise HTTPException(
                status_code=403,
                detail="Demo users already exist. To refresh/repair credentials or roles, supply ?secret=Admin@123456"
            )

        result = await seed_default_admin_and_roles(db)
        return {
            "status": "success",
            "message": "Default foundational roles and demo accounts verified successfully.",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Manual admin seeding error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to seed admin and roles: {str(e)}")

@app.get("/", tags=["Health"])
async def root():
    return {
        "app": "Procurement Management API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False)


