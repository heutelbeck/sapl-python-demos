from django.contrib.auth.models import User
from django.db import models
from django.forms import model_to_dict

from medical.model_manager import PatientManager



class Patient(models.Model):
    """
    Model for the Patientrecord
    """
    name = models.CharField(max_length=200)
    icd11_code = models.CharField(max_length=64, blank=True, default='')
    diagnosis_text = models.TextField(max_length=4096)
    attending_doctor = models.CharField(max_length=64,blank=True,default='')
    room_number = models.IntegerField()
    is_related_to_staff = models.BooleanField(default=False)

    objects_patients = PatientManager()

    def __str__(self):
        """String for representing the Patient-Model object."""
        return model_to_dict(self)
