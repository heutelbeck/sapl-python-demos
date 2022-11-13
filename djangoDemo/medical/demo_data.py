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

    head_nurse = Group(name="Head Nurse")
    head_nurse.save()
    head_nurse.permissions.add(view_patient, change_patient)

    doctor = Group(name="Doctor")
    doctor.save()
    doctor.permissions.add(view_patient, change_patient, delete_patient)

    nurse = Group(name="Nurse")
    nurse.save()
    nurse.permissions.add(view_patient, change_patient, add_patient)

    intern = Group(name="Intern")
    intern.save()
    intern.permissions.add(view_patient)

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

    thomas = User(
        username="thomas",
        first_name="Thomas",
        last_name="Thompson",
        email="thomas@example.com",
        is_staff=True,
    )
    thomas.set_password(DEFAULT_PASSWORD)
    thomas.save()
    thomas.groups.add(doctor)

    peter = User(
        username="peter",
        first_name="Peter",
        last_name="Paper",
        email="peter@example.com",
        is_staff=True,
    )
    peter.set_password(DEFAULT_PASSWORD)
    peter.save()
    peter.groups.add(nurse)

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
    alina.groups.add(head_nurse)

    sandra = User(
        username="sandra",
        first_name="Sandra",
        last_name="Simpson",
        email="sandra@example.com",
        is_staff=True,
    )

    sandra.set_password(DEFAULT_PASSWORD)
    sandra.save()
    sandra.groups.add(nurse)
    sandra.groups.add(intern)

    User.objects.create_superuser("admin", "admin@example.com", DEFAULT_PASSWORD)

    # Patients

    dummy = Patient(
        name="Dummy Patient",
        icd11_code="Dummy icd11_code",
        diagnosis_text="Dummy diagnose",
        attending_doctor=julia,
        room_number=99,
        is_related_to_staff=False

    )
    dummy.save()

    lenny = Patient(
        name="Lenny Lankowsky",
        icd11_code="DA63.Z/ME24.90",
        diagnosis_text="Duodenal ulcer with acute haemorrhage.",
        attending_doctor=julia,
        room_number=11,
        is_related_to_staff=False
    )
    lenny.save()

    karl = Patient(
        name="Karl Kartoffel",
        icd11_code="9B71.0Z/5A11",
        diagnosis_text="Type 2 diabetes mellitus",
        attending_doctor=thomas,
        room_number=33,
        is_related_to_staff=False
    )
    karl.save()

    kim = Patient(
        name="Kim Thompson",
        icd11_code="19Z",
        diagnosis_text="broken leg",
        attending_doctor=julia,
        room_number=9,
        is_related_to_staff=True,
    )
    kim.save()