# chat/urls.py
from django.urls import path

from . import views
from .views import PatientMedicalData, PatientData, NewPatient, PatientDetails

app_name = 'medical'

urlpatterns = [
    path("", views.index, name="index"),
    # path("rooms/<str:room_name>/", views.room, name="room"),
    path("patients/", views.patients, name="patients"),
    path("new_patient/", NewPatient.as_view(), name="new_patient"),
    path("patients/<int:pk>/", PatientDetails.as_view(), name="patient"),
    path("patients/<int:pk>/update_diagnose/", PatientMedicalData.as_view(), name="update_patient_diagnose"),
    path("patients/<int:pk>/update_patient_data/", PatientData.as_view(), name="update_patient")
]
