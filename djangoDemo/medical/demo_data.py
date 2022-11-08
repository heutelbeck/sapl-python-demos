import logging
import os

from django.contrib.auth.models import User, Group, Permission

from .models import Patient

NAME_LENNY = "Lenny"
NAME_JULIA = "Julia"
NAME_THOMAS = "Thomas"
NAME_ALINA = "Alina"
NAME_JANINA = "Janina"
NAME_KARL = "Karl"

DEFAULT_PASSWORD = "password"

logger = logging.getLogger(__name__)


def initialize_database():
    """
    the method initialize_database runs the first time , an Database created and
    create demoData
    """
    if os.environ.get("RUN_MAIN", None) != "true":
        return

    if len(User.objects.all()) > 1:  # Anonymous user is contained by default
        logger.info("Users are already initialized. Skipping demo data creation.")
        return

    logger.info("No users present. Creating demo data...")
    # Permissions
    add_patient = Permission.objects.filter(codename="add_patient").first()
    view_patient = Permission.objects.filter(codename="view_patient").first()
    change_patient = Permission.objects.filter(codename="change_patient").first()
    delete_patient = Permission.objects.filter(codename="delete_patient").first()

    # Groups

    assistant_doctor = Group(name="Assistants Doctors")
    assistant_doctor.save()
    assistant_doctor.permissions.add(view_patient, change_patient, delete_patient)

    doctor = Group(name="Doctors")
    doctor.save()
    doctor.permissions.add(view_patient, change_patient, delete_patient)

    nurse = Group(name="Nurses")
    nurse.save()
    nurse.permissions.add(view_patient, change_patient, add_patient)

    # Staff

    julia = User(
        username="julia",
        first_name="Julia",
        last_name="August",
        email="julia@example.com",
        is_staff=True,
    )
    julia.set_password(DEFAULT_PASSWORD)
    julia.save()
    julia.groups.add(doctor)

    peter = User(
        username="peter",
        first_name="Peter",
        last_name="Paper",
        email="peter@example.com",
        is_staff=True,
    )
    peter.set_password(DEFAULT_PASSWORD)
    peter.save()
    peter.groups.add(assistant_doctor)

    alina = User(
        username="alina",
        first_name="Alina",
        last_name="Aurich",
        email="alina@example.com",
        is_staff=True,
    )
    alina.set_password(DEFAULT_PASSWORD)
    alina.save()
    alina.groups.add(nurse)

    User.objects.create_superuser("admin", "admin@example.com", DEFAULT_PASSWORD)

    # Patients

    lenny = Patient(
        name="Lenny Lankowsky",
        icd11Code="DA63.Z/ME24.90",
        diagnosisText="Duodenal ulcer with acute haemorrhage.",
        attendingDoctor=julia,
        roomNumber=11,
        is_related_to_staff=False
    )
    lenny.save()

    karl = Patient(
        name="Karl Kartoffel",
        icd11Code="9B71.0Z/5A11",
        diagnosisText="Type 2 diabetes mellitus",
        attendingDoctor=peter,
        roomNumber=33,
        is_related_to_staff=False
    )
    karl.save()
