# chat/views.py
from asgiref.sync import sync_to_async
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views import View
from medical.forms import UpdatePatientData, UpdatePatientDiagnose, NewPatientForm
from medical.models import Patient
from sapl_base.decorators import pre_enforce


async def index(request):
    """
    Entrypoint to site
    """

    user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
    if user_is_anonym:
        return render(request, "medical/home.html")
    return redirect("medical:patients")


@pre_enforce
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
    all_patients = await Patient.objects_patients.auth_user_view_all_patients()

    return render(request, "medical/patients/patient_list.html", {"patients": all_patients})


class PatientDetails(View):

    @pre_enforce
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
        if patient is None:
            return render(request, "medical/404.html")
        return render(request, "medical/patients/detailview.html",
                      {"patient": patient})

    @pre_enforce
    async def post(self, request, pk):
        await Patient.objects_patients.delete_patient(pk)
        return redirect("medical:patients")


class NewPatient(View):
    """
    create new patient

    :param request:
    :return:
    """

    @pre_enforce
    async def get(self, request):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = NewPatientForm()
        return render(request, "medical/patients/new_patient.html", {'form': form})

    @pre_enforce
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

    @pre_enforce
    async def get(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientDiagnose()
        patient = await Patient.objects_patients.find_patient_by_pk(pk)
        if patient is None:
            return render(request, "medical/404.html")
        return render(request, "medical/patients/update_diagnose.html", {'form': form, 'patient': patient})

    @pre_enforce
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

    @pre_enforce
    async def get(self, request, pk):
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientData()

        patient = await Patient.objects_patients.find_patient_by_pk(pk)
        if patient is None:
            return render(request, "medical/404.html")
        return render(request, "medical/patients/update_patient.html", {'form': form, 'patient': patient})

    @pre_enforce
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


def custom_error_403(request, exception):
    """
    This method render the view for the error 403

    :type request: WSGIRequest
    :param request: request for the view
    :type exception: Exception
    :param exception: Exception raise error 403
    """
    return render(request, "medical/403.html", {})


def custom_error_404(request, exception):
    """
    This method render the view for the error 404

    :type request: WSGIRequest
    :param request: request for the view
    """
    return render(request, "medical/404.html", {})
