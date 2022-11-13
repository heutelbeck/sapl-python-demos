from typing import Optional

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from sapl_base.decorators import pre_enforce, post_enforce


class PatientQuerySet(models.QuerySet):
    """
    This class provide the query sets for the methods of the Patient-Manager
    """

    async def auth_user_view_all_patients(self):
        """
        This queryset filter a list of all the patients
        """
        return await sync_to_async(lambda: list(self.all()))()

    async def get_patient_by_pk(self, patient_pk: int):
        try:
            return await self.aget(id=patient_pk)
        except ObjectDoesNotExist:
            return None

    @pre_enforce
    async def delete_patient(self, patient):
        return await sync_to_async(lambda: patient.delete())()

    @pre_enforce
    async def update_patient_general_data(self, patient, attending_doctor: Optional[str],
                                          room_number: Optional[int]
                                          ):

        if room_number:
            patient.room_number = room_number
        if attending_doctor:
            patient.attending_doctor = attending_doctor
        await sync_to_async(lambda: patient.save())()
        return patient

    @pre_enforce
    async def update_patient_diagnose(self, patient, diagnose: Optional[str], icd11: Optional[str]):
        if diagnose:
            patient.diagnosis_text = diagnose
        if icd11:
            patient.icd11_code = icd11
        await sync_to_async(lambda: patient.save())()
        return patient


class PatientManager(models.Manager):
    """
    This class is the manager for the patient model and access to the django orm by object_patients.
    the patient-manager connect the model and the pep of the sapl-module.
    """

    def __str__(self):
        """
        This method returns the name of the instance
        """
        return self.name

    def get_queryset(self):
        """
        This method connects to the querysets of the django-orm
        """
        return PatientQuerySet(self.model, using=self._db)

    @pre_enforce
    async def auth_user_view_all_patients(self):
        """
        check if user is allowed to view all patients

        """
        """
        This methode enable all authenticated users to see the patient list.
        The pre_enforce decorator gives access to the method by the SAPL-Server
        """
        queryset = self.get_queryset()
        return await queryset.auth_user_view_all_patients()

    @post_enforce
    async def find_patient_by_pk(self, patient_pk):
        """
        check if user is only allowed to see default patient ( pre_enforce map function arguments)
        check if user is allowed to see all values of the patient ( post_enforce map certain diagnose for assistant)
        """
        queryset = self.get_queryset()
        return await queryset.get_patient_by_pk(patient_pk)

    @pre_enforce
    async def delete_patient(self, patient_pk: int):
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.delete_patient(patient)

    @pre_enforce
    async def update_patient_data(self, patient_pk: int, attending_doctor: Optional[str], room_number: Optional[int]):
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.update_patient_general_data(patient, attending_doctor, room_number)

    @pre_enforce
    async def update_patient_diagnose(self, patient_pk: int, diagnose: Optional[str], icd11: Optional[str]):
        queryset = self.get_queryset()
        patient = await queryset.get_patient_by_pk(patient_pk)
        return await queryset.update_patient_diagnose(patient, diagnose, icd11)
