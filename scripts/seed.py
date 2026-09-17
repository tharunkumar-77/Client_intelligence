"""
Seed script — creates the practitioner, default segments, and a login user.
Run once after db init:  python scripts/seed.py [--vertical therapy|hr_advisory]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.practitioner import Practitioner
from app.models.practitioner import Practitioner
from app.models.segment import Segment
VERTICAL_SEGMENTS = {
    "financial_advisory": [
        ("High-Net-Worth Prospect",   "Clients with significant investable assets or high earning potential"),
        ("Growth-Stage Professional", "Early-career professionals on a strong growth trajectory"),
        ("Debt-Restructure Focus",    "Clients whose primary need is debt management and restructuring"),
        ("Retirement Planner",        "Clients focused on retirement readiness and income planning"),
        ("Business Owner",            "Entrepreneurs with complex and intertwined personal/business finances"),
        ("First-Time Investor",       "Beginners entering the investment space for the first time"),
    ],
    "therapy": [
        ("Anxiety & Stress",         "Clients presenting with anxiety or stress-related concerns"),
        ("Depression",               "Clients presenting with depressive symptoms"),
        ("Trauma & PTSD",            "Clients with trauma history or PTSD"),
        ("Relationship Issues",      "Couples or individuals with relationship difficulties"),
        ("Grief & Loss",             "Clients experiencing bereavement or significant loss"),
        ("Life Transitions",         "Clients navigating major life changes"),
        ("Neurodivergent Support",   "Clients seeking support related to neurodivergence"),
    ],
    "hr_advisory": [
        ("Performance Management",   "Employee performance concerns"),
        ("Workplace Grievance",       "Formal or informal workplace grievances"),
        ("Career Development",        "Career growth and development requests"),
        ("Wellbeing & Burnout",       "Employee wellbeing and burnout concerns"),
        ("Disciplinary Matter",       "Disciplinary or compliance-related cases"),
        ("Recruitment Support",       "Hiring and onboarding requests"),
        ("Policy Query",              "Questions about HR policies and procedures"),
    ],
}

VERTICAL_NAMES = {
    "financial_advisory": "Financial Coach",
    "therapy": "Lead Therapist",
    "hr_advisory": "HR Adviser",
}


def seed(vertical: str = "financial_advisory"):
    app = create_app()
    with app.app_context():
        if Practitioner.query.count() > 0:
            print("⚠  Database already seeded — skipping practitioner/segments.")
        else:
            DEFAULT_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "changeme123")
            practitioner = Practitioner(
                email="coach@example.com",
                name=VERTICAL_NAMES.get(vertical, "Practitioner"),
                vertical=vertical,
            )
            practitioner.set_password(DEFAULT_PASSWORD)
            db.session.add(practitioner)
            db.session.flush()

            segments = VERTICAL_SEGMENTS.get(vertical, [])
            for name, description in segments:
                db.session.add(Segment(
                    practitioner_id=practitioner.id,
                    name=name,
                    description=description,
                    ai_derived=False,
                ))

            db.session.commit()
            print(f"✓ Practitioner : {practitioner.name} <{practitioner.email}>")
            print(f"  ID           : {practitioner.id}")
            print(f"  Vertical     : {vertical}")
            print(f"✓ {len(segments)} segments seeded.")

        # ── Auto-heal existing practitioners without passwords ─────────────────
        DEFAULT_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "changeme123")
        repaired = 0
        for p in Practitioner.query.filter(Practitioner.password_hash == None).all():
            p.set_password(DEFAULT_PASSWORD)
            repaired += 1
        if repaired:
            db.session.commit()
            print(f"✓ Repaired {repaired} existing practitioners with default password.")

        print(f"\n✓ Login user credentials:")
        print(f"  Email    : coach@example.com (or your seeded email)")
        print(f"  Password : {DEFAULT_PASSWORD}")
        print(f"  (Change via SEED_USER_PASSWORD env var)")

        print("\n── Ready ──────────────────────────────────────────────")
        print("  python run.py   →   http://localhost:5000/login")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertical", default="financial_advisory",
                        choices=list(VERTICAL_SEGMENTS.keys()))
    args = parser.parse_args()
    seed(args.vertical)
