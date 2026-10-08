"""
Standalone demo users and foundational roles seeding script.
Can be executed directly via terminal or Railway Console:
    python seed_admin.py
"""
import asyncio
from app.database import AsyncSessionLocal
from app.main import seed_default_admin_and_roles

async def main():
    print("==================================================")
    print("ProcureFlow: Seeding Foundational Roles & Demo Users")
    print("==================================================")
    async with AsyncSessionLocal() as db:
        res = await seed_default_admin_and_roles(db)
        print("Database Roles:", res["database_roles"])
        print("\nDemo Accounts Status:")
        for u in res["demo_users"]:
            print(f"  [{u['action'].upper():<9}] {u['email']:<26} | Role: {u['role']:<22} | Status: {u['status']}")
        print(f"\nSample Vendor Seeded: {res['sample_vendor_seeded']}")
        print("==================================================")
        print("Verification complete! Ready for login with all demo roles.")

if __name__ == "__main__":
    asyncio.run(main())
