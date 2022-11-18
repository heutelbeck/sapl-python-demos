from typing import Optional

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from sapl_base.decorators import pre_enforce, post_enforce


class PatientQuerySet(models.QuerySet):

    async def auth_user_view_all_patients(self):
        """
        This queryset filter a list of all the patients

        @return: a list , containing all Patient objects in the database
        """
        return await sync_to_async(lambda: list(self.all()))()

    async def get_patient_by_pk(self, patient_pk: int):
        """
        Retrieve a single Patient object from the database, which has the provided id

        @param patient_pk: id of the object, which are retrieved from the database
        @return: Patient object, which has the given provided id, or None
        """
        try:
            return await self.aget(id=patient_pk)
        except ObjectDoesNotExist:
            return None

    @pre_enforce
    async def delete_patient(self, patient):
        """
        Delete the provided Patient object from the database

        This method is pre_enforced to make sure, that the User trying to delete this Patient has permission to delete
        the object.

        Only the attending doctor has permission to delete his own patient, but no-one is allowed to delete the patient
        with the id=1

        The policy which can apply for a call to this method is "attending doctor can delete his patient" and can be
        found in the file patient_queryset.sapl

        @param patient: Patient object, which will be deleted from the database
        """
        return await sync_to_async(lambda: patient.delete())()

    @pre_enforce
    async def update_patient_general_data(self, patient, attending_doctor: Optional[str],
                                          room_number: Optional[int]):
        """
        Update the attending doctor and the room number of the given Patient object.

        Only the Head Nurse can update all general data of a patient and those patients, which are related to the staff.
        Nurses can update the room Number of a patient and those patients whose room number is changed to a number,
        less than 10 will have julia assigned as the attending doctor.

        The policies which can apply to pre_enforce these restrictions are:
        "head nurse can update patients related to staff", "nurse can update general data of a patient",
        "change attending doctor for room"
        and can be found in the filepatient_queryset.sapl

        @param patient: Patient object, which will be modified
        @param attending_doctor: Name of the new attending doctor
        @param room_number: New room number of the patient
        @return: The modified Patient Object
        """
        if room_number:
            patient.room_number = room_number
        if attending_doctor:
            patient.attending_doctor = attending_doctor
        await sync_to_async(lambda: patient.save())()
        return patient

    @pre_enforce
    async def update_patient_medical_data(self, patient, diagnose: Optional[str], icd11: Optional[str]):
        """
        Update the medical data of a patient.

        Only the attending doctor of a patient can change his medical data.
        The policy to pre_enforce this restriction is "attending doctor can update patient" and can be found in the file
        patient_queryset.sapl
        @param patient: Patient object, which will be modified
        @param diagnose: New diagnose of the patient
        @param icd11: New icd11code of the patient
        @return: The modified Patient Object
        """
        if diagnose:
            patient.diagnosis_text = diagnose
        if icd11:
            patient.icd11_code = icd11
        await sync_to_async(lambda: patient.save())()
        return patient


class PatientManager(models.Manager):
    """
    This class is the manager for the patient model and access to the django orm by object_patients.
    the patient-manager connects the model and the pep of the sapl-module.
    """

    def get_queryset(self):
        """
        This method returns an instance of the Queryset for the Patient model

        @return: Queryset of the Patient model
        """
        return PatientQuerySet(self.model, using=self._db)

    @pre_enforce
    async def auth_user_view_all_patients(self):
        """
        Authenticated Users are allowed to see all Patients

        This method is pre_enforced with SAPL to verify, that the requesting User is authenticated and to add
        obligations, which filter certain patients.

        Polices which can apply for this method can be found in the file patient_manager.sapl and are
        "filter patients related to staff", "Doctor can only see his own patients" and
        "Patients related to staff are visible for the head nurse".
        """
        queryset = self.get_queryset()
        return await queryset.auth_user_view_all_patients()

    @post_enforce
    async def find_patient_by_pk(self, patient_pk):
        """
        Finds a patient by his pk and returns the object.

        This method is post_enforced, to verify that the requesting User is allowed to see the data of the patient to
        whom the given pk belongs.

        Policies, which can apply for a call of this method are: "Doctor can see their patients",
        "hide patients related to staff", "Head Nurse can see all patients",
        "hide diagnose of patients related to staff from head nurse".

        @return: An Instance of the Patient which belongs the given patient_pk.
        """
        queryset = self.get_queryset()
        return await queryset.get_patient_by_pk(patient_pk)

    @pre_enforce
    async def delete_patient(self, patient_pk: int):
        """
        Delete the patient with the given patient_pk.

        To prevent deletion of patients from Users, who are not allowed to delete them, or to protect patients,
        which aren't allowed to be deleted at all, this method is pre_enforced.

        A policy which can apply for a call to this method is: "permit doctor to delete patients".
        This policy gives Permission to delete a User only to the attending doctor of the patient.
        Additionally, the patient with the pk=1 is protected and can't be deleted.

        @param patient_pk: Id of the patient, who will be deleted
        """
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.delete_patient(patient)

    @pre_enforce
    async def update_patient_data(self, patient_pk: int, attending_doctor: Optional[str], room_number: Optional[int]):
        """
        Update the general data of a patient.

        Only Users of the group "Nurse" are allowed to make requests, to update the general data of a patient.
        The room number can be changed by every Nurse, but only the Head Nurse can change the attending doctor.
        Attempts to change data of the patient with the id=1 are forbidden.

        These policies are enforced with a pre_enforce annotation. The applicable policies are:
        "Nurse can change patients room", "Only head nurse can change attending doctor" and can be found in the file
        patient_manager.sapl

        @param patient_pk: id of the patient, which data shall be changed
        @param attending_doctor: the name of the new attending doctor
        @param room_number: the new room number
        """
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.update_patient_general_data(patient, attending_doctor, room_number)

    @pre_enforce
    async def update_patient_medical_data(self, patient_pk: int, diagnose: Optional[str], icd11: Optional[str]):
        """
        Update the medical data of a patient.

        Only Users of the group "Doctor" are allowed to make requests, to update the medical data of a patient.

        This method is pre_enforce with the policy "permit doctor to update diagnose", which can be found in the file
        patient_manager.sapl

        @param patient_pk: id of the patient, which data shall be changed
        @param diagnose: new diagnose of the patient
        @param icd11: new icd11code of the patient
        """
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.update_patient_medical_data(patient, diagnose, icd11)
