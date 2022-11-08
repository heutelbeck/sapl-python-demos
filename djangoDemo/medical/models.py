from django.contrib.auth.models import User
from django.db import models
from django.db.models import SET_NULL

from medical.model_manager import PatientManager


# Create your models here.
class Patient(models.Model):
    """
    Model for the Patientrecord
    """
    name = models.CharField(max_length=200)
    icd11Code = models.CharField(max_length=64, blank=True, default='')
    diagnosisText = models.TextField(max_length=4096)
    attendingDoctor = models.CharField(max_length=64,blank=True,default='')

    roomNumber = models.CharField(max_length=64)
    is_related_to_staff = models.BooleanField(default=False)

    objects_patients = PatientManager()

    def __str__(self):
        """String for representing the Patient-Model object."""
        return "{} withs pk-Number {}".format(
            self.name, self.pk
        )

    # def save(self, *args, **kwargs):
    #     """Save new or changed Patients"""
    #     super().save(*args, **kwargs)
    #
    # def delete(self, using=None, keep_parents=False):
    #     """Delete Patients"""
    #     super().delete()
