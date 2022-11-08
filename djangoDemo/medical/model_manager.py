from typing import Optional

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


class PatientQuerySet(models.QuerySet):
    """
    This class provide the query sets for the methods of the Patient-Manager
    """

    async def authUser_view_all_patients(self):
        """
        This queryset filter a list of all the patients
        """
        return await sync_to_async(lambda:self.all())()

    async def delete_patient(self, patient_pk: int):
        patient = await self.aget(pk=patient_pk)
        return await sync_to_async(lambda: patient.delete())()

    async def update_patient_general_data(self, patient_pk: int, attending_doctor: Optional[str],room_number: Optional[int]
                                          ):
        patient = await self.aget(pk=patient_pk)
        if room_number:
            patient.roomNumber = room_number
        if attending_doctor:
            patient.attendingDoctor = attending_doctor
        return await sync_to_async(lambda: patient.save())()

    async def update_patient_diagnose(self, patient_pk: int, diagnose: Optional[str], icd11: Optional[str]):
        patient = await self.aget(pk=patient_pk)
        if diagnose:
            patient.diagnosisText = diagnose
        if icd11:
            patient.icd11Code = icd11
        return await sync_to_async(lambda: patient.save())()


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

    async def authUser_view_all_patients(self):
        """
        This methode enable all authenticated users to see the patient list.
        The pre_enforce decorator gives access to the method by the SAPL-Server
        """
        queryset = self.get_queryset()
        return await queryset.authUser_view_all_patients()

    async def find_patient_by_pk(self, patient_pk):
        queryset = self.get_queryset()
        try:
            return await queryset.aget(id=patient_pk)
        except ObjectDoesNotExist:
            return None

    async def delete_patient(self, patient_pk: int):
        queryset = self.get_queryset()
        return await queryset.delete_patient(patient_pk)

    async def update_patient_data(self, patient_pk: int, attenting_doctor: Optional[str], room_number: Optional[int]):
        queryset = self.get_queryset()
        return await queryset.update_patient_general_data(patient_pk, attenting_doctor, room_number)

    async def update_patient_diagnose(self, patient_pk: int, diagnose: Optional[str], icd11: Optional[str]):
        queryset = self.get_queryset()
        return await queryset.update_patient_diagnose(patient_pk, diagnose, icd11)

    # async def save(self, *args, **kwargs):
    #     """
    #     This methode save patients.
    #     The pre_enforce decorator gives access to the method by the SAPL-Server
    #     """
    #     super().save(*args, **kwargs)
