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
    Maps to the endpoint "/" and renders a page with information about this Demo and a Button,
    where a User can log in. When a User is already logged in, he is redirected to the patients page.
    """
    user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
    if user_is_anonym:
        return render(request, "medical/home.html")
    return redirect("medical:patients")


@pre_enforce
async def patients(request):
    """
    This function renders the view for the patient-list and maps to the endpoint "patients/"
    This Page is pre_enforced with SAPL and can only be accessed with a GET request from an authenticated User.
    Other request methods are denied

    The Policy which can apply for this Page is
    "Staff can see Patientlist" in the file views.sapl in the policies folder

    :param request: request for the view
    """
    user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
    if user_is_anonym:
        return redirect('medical:index')
    all_patients = await Patient.objects_patients.auth_user_view_all_patients()

    return render(request, "medical/patients/patient_list.html", {"patients": all_patients})


class PatientDetails(View):
    """
    Class based View to handle GET and POST Request for the URL "patients/<int:pk>/" which shows details of a patient.

    GET and POST requests are separately pre_enforced with SAPL.
    """

    @pre_enforce
    async def get(self, request, pk: int):
        """
        This method renders the view for a patient-record and is called by GET requests to the URL "patients/<int:pk>/"

        This Method is pre_enforced with SAPL and the Policies which can apply for this request are
        "Staff can see Patientlist" in the file views.sapl in the policies folder

        :param request: request for the view
        :param pk: id of the patient, which data shall be retrieved from the database.
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
        """
        POST Request to this endpoint will attempt to delete the patient with the given id from the database.

        Only a User of the Group "Doctor" is allowed to send a POST request to this endpoint.
        The Policy which can apply for this request is "only Doctor can delete patients"
        in the file views.sapl in the policies folder

        @param request: Request which was made to the Server
        @param pk: id of the patient
        @return: redirects the client to the patients page
        """
        await Patient.objects_patients.delete_patient(pk)
        return redirect("medical:patients")


class NewPatient(View):
    """
    Class based View to add a new patient to the database

    GET and POST requests are both pre_enforced with SAPL
    """

    @pre_enforce
    async def get(self, request):
        """
        Function is called when a GET request is sent to the endpoint "new_patient/" it renders a view of a form which
        adds a new patient.

        This page can only be seen by Users of the Group "Nurse". The policy which is applied for requests to this endpoint is
        "Nurse and interns are allowed to see the view to add new Patients" in the file views.sapl in the policies folder

        @param request: Request which was made to the Server
        """
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = NewPatientForm()
        return render(request, "medical/patients/new_patient.html", {'form': form})

    @pre_enforce
    async def post(self, request):
        """
        Function is called, when a POST request is sent to the endpoint "new_patient/". It attempts to add a
        new patient to the database with the arguments provided

        Patients can only be added by Nurses. The Policy which is applied for POST requests to this endpoint is
        "Only Nurse can add new patients" in the file views.sapl in the policies folder.
        Although Interns are allowed to see the Page, they are not allowed to add
        new patients.

        @param request: Request which was made to the Server

        """
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
    """
    Class based View to see and modify the medical data of a patient

    GET and POST requests are both pre_enforced with SAPL
    """

    @pre_enforce
    async def get(self, request, pk):
        """
        This method is called when a GET request is made to the endpoint "patients/<int:pk>/update_diagnose/"
        A page is rendered, which shows the medical data of the patient with the given pk.

        Only Users of the group "Doctor" are allowed to make a request to this endpoint. The policy which is applied to
        GET requests to this endpoint is policy "Only Doctor can update patients diagnose"
        @param request: Request, which was made to the Server
        @param pk: id of the patient, whose medical data will be displayed
        """
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
        """
        This method is called when a POST request is made to the endpoint "patients/<int:pk>/update_diagnose/"
        The medical data of the patient with the given pk will be updated with the arguments of the POST request.

        Only Users of the group "Doctor" are allowed to make a request to this endpoint. The policy which is applied to
        POST requests to this endpoint is policy "Only Doctor can update patients diagnose"
        @param request: Request, which was made to the Server
        @param pk: id of the patient, whose medical data will be displayed
        """
        user_is_anonym = await sync_to_async(lambda: request.user.is_anonymous)()
        if user_is_anonym:
            return redirect('medical:index')
        form = UpdatePatientDiagnose(request.POST)

        if form.is_valid():
            await Patient.objects_patients.update_patient_medical_data(pk, **form.cleaned_data)
            return redirect('medical:patient', pk)

        messages.error(self.request, 'Form is invalid')
        return HttpResponseRedirect(self.request.path_info)


class PatientData(View):
    """
    Class based View to see and modify the medical data of a patient

    GET and POST requests are both pre_enforced with SAPL
    """

    @pre_enforce
    async def get(self, request, pk):
        """
        This method is called when a GET request is made to the endpoint "patients/<int:pk>/update_patient_data/"
        A page is rendered, which shows the general data of the patient with the given pk.

        Only Users of the group "Nurse" are allowed to make a request to this endpoint. The policy which is applied to
        GET requests to this endpoint is policy "Only Nurse can update patients general data"
        @param request: Request, which was made to the Server
        @param pk: id of the patient, whose general data will be displayed
        """
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
        """
        This method is called when a POST request is made to the endpoint "patients/<int:pk>/update_patient_data/"
        The general data of the patient with the given pk will be updated with the arguments of the POST request.

        Only Users of the group "Nurse" are allowed to make a request to this endpoint. The policy which is applied to
        POST requests to this endpoint is policy "Only Nurse can update patients general data"
        @param request: Request, which was made to the Server
        @param pk: id of the patient, whose general data will be displayed
        """
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

    :param request: request for the view
    :param exception: Exception raise error 403
    """
    return render(request, "medical/403.html", {})


def custom_error_404(request, exception):
    """
    This method render the view for the error 404

    :param request: request for the view
    """
    return render(request, "medical/404.html", {})
