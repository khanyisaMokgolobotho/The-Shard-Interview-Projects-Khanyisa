import argparse
import sys
import uuid
from datetime import datetime, timezone, timedelta

from app.db.session import SessionLocal, Base, engine
from app.models.user import Role, User
from app.models.customer import Customer
from app.models.ticket import Ticket, Message
from app.core.security import hash_password
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# create-admin
# ---------------------------------------------------------------------------

def cmd_create_admin(args):
    """
    Bootstrap the first admin user.

    Why this can't be done through the API:
      POST /auth/register requires an existing admin to authorise it.
      The first admin must be created out-of-band — that's this command.

    Security:
      We prompt for the password interactively so it never appears
      in shell history or process listings.
    """
    import getpass

    db = SessionLocal()
    try:
        # Ensure admin role exists
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="System administrator")
            db.add(admin_role)
            db.flush()

        email = args.email or input("Admin email: ").strip()
        full_name = args.name or input("Full name: ").strip()

        # Check if user already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"ERROR: A user with email '{email}' already exists.")
            sys.exit(1)

        if args.password:
            password = args.password
        else:
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("ERROR: Passwords do not match.")
                sys.exit(1)

        if len(password) < 8:
            print("ERROR: Password must be at least 8 characters.")
            sys.exit(1)

        admin = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        print(f"\n✓ Admin user created successfully.")
        print(f"  Email : {email}")
        print(f"  Name  : {full_name}")
        print(f"  Role  : admin")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------

def cmd_seed(args):
    """
    Populate the database with realistic development data.

    Creates:
      - 3 roles  (admin, supervisor, agent)
      - 4 users  (1 admin, 1 supervisor, 2 agents)
      - 5 customers with SA phone numbers and ID numbers
      - 8 tickets across different priorities and statuses
      - Ticket messages on some tickets
      - 2 refund requests

    Safe to re-run: checks for existing data before inserting.
    """
    db = SessionLocal()
    try:
        # ── Roles ──────────────────────────────────────────────────────────
        roles = {}
        for name, desc in [
            ("admin", "System administrator"),
            ("supervisor", "Team supervisor — can approve refunds and view all tickets"),
            ("agent", "Support agent — handles customer tickets"),
        ]:
            role = db.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.add(role)
                db.flush()
            roles[name] = role

        print("✓ Roles seeded")

        # ── Users ──────────────────────────────────────────────────────────
        users_data = [
            ("admin@resolveza.co.za",      "System Admin",    "Admin@123!",   "admin"),
            ("supervisor@resolveza.co.za", "Thabo Nkosi",     "Super@123!",   "supervisor"),
            ("agent1@resolveza.co.za",     "Lerato Dlamini",  "Agent@123!",   "agent"),
            ("agent2@resolveza.co.za",     "Sipho Mokoena",   "Agent@123!",   "agent"),
        ]

        users = {}
        for email, name, password, role_name in users_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=name,
                    hashed_password=hash_password(password),
                    role_id=roles[role_name].id,
                    is_active=True,
                )
                db.add(user)
                db.flush()
            users[email] = user

        print("✓ Users seeded")

        # ── Customers ──────────────────────────────────────────────────────
        customers_data = [
            ("Nomsa Zulu",      "nomsa.zulu@gmail.com",      "0821234567", "9001015009087"),
            ("Kagiso Sithole",  "kagiso.sithole@outlook.com","0731234567", "8505125009083"),
            ("Priya Naidoo",    "priya.naidoo@yahoo.com",    "0611234567", "9203045009082"),
            ("Andile Khumalo",  "andile.khumalo@gmail.com",  "0791234567", "7807075009086"),
            ("Fatima Essop",    "fatima.essop@webmail.co.za","0841234567", "9506195009081"),
        ]

        customers = []
        for full_name, email, phone, id_number in customers_data:
            customer = db.query(Customer).filter(Customer.email == email).first()
            if not customer:
                customer = Customer(
                    full_name=full_name,
                    email=email,
                    phone_number=phone,
                    id_number=id_number,
                )
                db.add(customer)
                db.flush()
            customers.append(customer)

        print("✓ Customers seeded")

        # ── Tickets ────────────────────────────────────────────────────────
        agent1 = users["agent1@resolveza.co.za"]
        agent2 = users["agent2@resolveza.co.za"]

        tickets_data = [
            # (customer_idx, category, priority, status, assigned_to, subject, hours_until_sla)
            (0, "DOUBLE_BILLING",   "HIGH",   "OPEN",        None,    "Charged twice for June data bundle", 4),
            (0, "SERVICE_OUTAGE",   "CRITICAL","IN_PROGRESS", agent1,  "No signal for 3 days in Soweto",    1),
            (1, "INCORRECT_CHARGE", "MEDIUM", "OPEN",        None,    "R149 mystery charge on statement",  24),
            (1, "POOR_QUALITY",     "LOW",    "RESOLVED",    agent2,  "Call drops every 5 minutes",        -48),
            (2, "DOUBLE_BILLING",   "HIGH",   "ESCALATED",   agent1,  "Triple-billed for roaming charges", -2),
            (2, "CONTRACT_DISPUTE", "MEDIUM", "IN_PROGRESS", agent2,  "Upgraded contract not applied",     12),
            (3, "INCORRECT_CHARGE", "LOW",    "CLOSED",      agent1,  "Data bundle deducted twice",        -72),
            (4, "SERVICE_OUTAGE",   "CRITICAL","OPEN",       None,    "Business line down — losing revenue",2),
        ]

        tickets = []
        for (cust_idx, category, priority, status,
             assigned_to, subject, sla_hours) in tickets_data:

            ticket = db.query(Ticket).filter(Ticket.subject == subject).first()
            if not ticket:
                sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)
                sla_breached = sla_hours < 0

                ticket = Ticket(
                    customer_id=customers[cust_idx].id,
                    assigned_to=assigned_to.id if assigned_to else None,
                    category=category,
                    priority=priority,
                    status=status,
                    subject=subject,
                    description=f"Customer reported: {subject.lower()}. Requires investigation.",
                    sla_deadline=sla_deadline,
                    sla_breached=sla_breached,
                    resolved_at=datetime.now(timezone.utc) if status in ("RESOLVED", "CLOSED") else None,
                )
                db.add(ticket)
                db.flush()
            tickets.append(ticket)

        print("✓ Tickets seeded")

        # ── Messages ───────────────────────────────────────────────────────
        messages_data = [
            (0, agent1.id, "agent",    "I've reviewed your account. I can see the duplicate charge. Raising a refund request now."),
            (0, None,      "customer", "Thank you, I've been waiting since last month for this to be resolved."),
            (1, agent1.id, "agent",    "Our network team has been notified. The outage is affecting multiple customers in your area."),
        ]

        for ticket_idx, sender_id, sender_type, content in messages_data:
            msg = Message(
                ticket_id=tickets[ticket_idx].id,
                sender_id=sender_id if sender_id else agent1.id,
                sender_type=sender_type,
                content=content,
            )
            db.add(msg)

        print("✓ Messages seeded")

        db.commit()
        print("\n✓ Database seeded successfully.")
        print("\nLogin credentials:")
        print("  admin@resolveza.co.za      Admin@123!")
        print("  supervisor@resolveza.co.za Super@123!")
        print("  agent1@resolveza.co.za     Agent@123!")
        print("  agent2@resolveza.co.za     Agent@123!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# reset-db
# ---------------------------------------------------------------------------

def cmd_reset_db(args):
    """
    Drop all tables and recreate them.

    SAFETY:
      Blocked in production (APP_ENV=production).
      Requires --confirm flag to prevent accidental runs.

    When to use:
      - Alembic migration conflicts during development
      - Starting fresh after schema changes
      - Never in production — use Alembic migrations instead
    """
    if settings.app_env == "production":
        print("ERROR: reset-db is disabled in production.")
        print("Use Alembic migrations: alembic upgrade head")
        sys.exit(1)

    if not args.confirm:
        print("ERROR: This will DELETE ALL DATA.")
        print("Re-run with --confirm to proceed:")
        print("  python -m app.cli reset-db --confirm")
        sys.exit(1)

    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    print("Recreating tables...")
    Base.metadata.create_all(engine)
    print("✓ Database reset complete.")

    if args.seed:
        print("\nSeeding...")
        cmd_seed(args)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="ResolveZA backend administration CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-admin
    p_admin = subparsers.add_parser("create-admin", help="Create the first admin user")
    p_admin.add_argument("--email",    help="Admin email address")
    p_admin.add_argument("--name",     help="Admin full name")
    p_admin.add_argument("--password", help="Password (omit to prompt securely)")
    p_admin.set_defaults(func=cmd_create_admin)

    # seed
    p_seed = subparsers.add_parser("seed", help="Populate DB with development test data")
    p_seed.set_defaults(func=cmd_seed)

    # reset-db
    p_reset = subparsers.add_parser("reset-db", help="Drop and recreate all tables (dev only)")
    p_reset.add_argument("--confirm", action="store_true", help="Required safety flag")
    p_reset.add_argument("--seed",    action="store_true", help="Also run seed after reset")
    p_reset.set_defaults(func=cmd_reset_db)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()