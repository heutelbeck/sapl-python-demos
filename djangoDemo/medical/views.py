# chat/views.py
from asgiref.sync import sync_to_async
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views import View
from sapl_base.decorators import pre_enforce

from medical.forms import UpdatePatientData, UpdatePatientDiagnose, NewPatientForm
from medical.models import Patient


async def index(request):
    """
    Entrypoint to site
    """
    user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
    if user_is_anonym:
        return render(request, "medical/home.html")
    return redirect("medical:patients")


# def room(request, room_name):
#
#     return render(request, "chat/room.html", {"room_name": room_name})

# absichern mit login required


async def patients(request):
    """
    This method render the view for the patient-list
    @pre_enforce for check the permission of the user

    :type request: WSGIRequest
    :param request: request for the view
    """
    user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
    if user_is_anonym:
        return redirect('medical:index')
    all_patients = await Patient.objects_patients.authUser_view_all_patients()
    patient_list = list()
    async for pat in all_patients:
        patient_list.append(pat)
    return render(request, "medical/patients/patient_list.html", {"patients": patient_list})


# preenforce

class PatientDetails(View):

    async def get(self, request, pk):
        """
            This method render the view for an patient-record
            @pre_enforce for check the permission of the user

            :type request: WSGIRequest
            :param request: request for the view

            :type pk: int
            :param request: Pk(Id) of the Patient
            """
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        patient = await Patient.objects_patients.find_patient_by_pk(pk)
        return render(request, "medical/patients/detailview.html",
                      {"patient": patient})

    async def post(self, request, pk):
        await Patient.objects_patients.delete_patient(pk)
        return redirect("medical:patients")


# preenforce
class NewPatient(View):
    """
    create new patient

    :param request:
    :return:
    """

    async def get(self, request):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = NewPatientForm()
        return render(request, "medical/patients/new_patient.html", {'form': form})

    async def post(self, request):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = NewPatientForm(request.POST)

        if form.is_valid():
            patient = Patient(**form.cleaned_data)
            await sync_to_async(lambda: patient.save())()
            return redirect('medical:patient', patient.pk)

        messages.error(self.request, 'Form is invalid')
        return HttpResponseRedirect(self.request.path_info)


class PatientMedicalData(View):

    # preenforce
    async def get(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientDiagnose()
        patient_object = await Patient.objects_patients.find_patient_by_pk(pk)
        return render(request, "medical/patients/update_diagnose.html", {'form': form, 'patient': patient_object})

    # postenforce
    async def post(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientDiagnose(request.POST)

        if form.is_valid():
            await Patient.objects_patients.update_patient_diagnose(pk, **form.cleaned_data)
            return redirect('medical:patient', pk)

        messages.error(self.request, 'Form is invalid')
        return HttpResponseRedirect(self.request.path_info)


class PatientData(View):

    # preenforce
    async def get(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientData()

        patient_object = await Patient.objects_patients.find_patient_by_pk(pk)
        return render(request, "medical/patients/update_patient.html", {'form': form, 'patient': patient_object})

    # postenforce
    async def post(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')

        form = UpdatePatientData(request.POST)
        if form.is_valid():
            await Patient.objects_patients.update_patient_data(pk, **form.cleaned_data)
            return redirect('medical:patient', pk)

        messages.error(self.request, 'Form is invalid')
        return HttpResponseRedirect(self.request.path_info)


async def custom_error_403(request, exception):
    """
    This method render the view for the error 403

    :type request: WSGIRequest
    :param request: request for the view
    :type exception: Exception
    :param exception: Exception raise error 403
    """
    return render(request, "medical/403.html", {})


async def custom_error_404(request, exception):
    """
    This method render the view for the error 404

    :type request: WSGIRequest
    :param request: request for the view
    """
    return render(request, "medical/404.html", {})
