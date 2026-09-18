import pytest
from app.models.practitioner import Practitioner
from app.models.client import Client
from app.models.appointment import Appointment
from flask_login import login_user

def test_practitioner_isolation(client, app, db_session):
    # Create two practitioners
    p1 = Practitioner(email="p1@example.com", name="Practitioner 1")
    p1.set_password("password")
    p2 = Practitioner(email="p2@example.com", name="Practitioner 2")
    p2.set_password("password")
    
    db_session.add_all([p1, p2])
    db_session.flush()

    # Create a client for p1
    c1 = Client(practitioner_id=p1.id, name="Client 1", email="c1@ex.com")
    db_session.add(c1)
    db_session.flush()

    # Create an appointment for c1
    appt = Appointment(
        client_id=c1.id,
        practitioner_id=p1.id,
        scheduled_at="2025-01-01T10:00:00+00:00",
        duration_minutes=60,
        status="scheduled"
    )
    db_session.add(appt)
    db_session.commit()

    # Login as p2
    client.post("/login", data={"email": "p2@example.com", "password": "password"})

    # Attempt to modify p1's appointment
    res = client.patch(f"/api/appointments/{appt.id}", json={"duration_minutes": 90})
    assert res.status_code == 404

    # Attempt to delete p1's appointment
    res = client.delete(f"/api/appointments/{appt.id}")
    assert res.status_code == 404

    # Attempt to fetch p1's timeline
    res = client.get(f"/clients/{c1.id}/timeline")
    assert res.status_code == 404
