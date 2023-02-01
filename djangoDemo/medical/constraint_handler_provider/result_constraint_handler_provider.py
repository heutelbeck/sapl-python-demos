from typing import List

from medical.models import Patient
from sapl_base.authorization_subscription_factory import client_request
from sapl_base.constraint_handling.constraint_handler_provider import ResultConstraintHandlerProvider


class FilterPatientsRelatedToStaff(ResultConstraintHandlerProvider):

    def handle(self, result: List[Patient]) -> List[Patient]:
        """
        patients which are related to staff mustn't be returned and are filtered from the list of patients, before
        returning the list

        @param result: list of patients
        @return: Filtered list of patients
        """
        filtered_patients = []
        for patient in result:
            if not patient.is_related_to_staff:
                filtered_patients.append(patient)
        return filtered_patients

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        'filter_patients_related_to_staff'

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        if constraint == 'filter_patients_related_to_staff':
            return True
        return False


class BlackenDiagnose(ResultConstraintHandlerProvider):

    def handle(self, result: Patient)-> Patient:
        """
        Patients related to staff are only visible to the Head Nurse and the attending doctor, but the Head Nurse
        shouldn't be allowed to see the diagnosis of these patients
        @param result: A Patient object, which diagnosis_text shall be modified
        @return: Modified Patient object, with diagnosis_text changed to 'FORBIDDEN'
        """
        result.diagnosis_text = "FORBIDDEN"
        return result

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        "blacken_diagnose"

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        if constraint == "blacken_diagnose":
            return True
        return False


class DoctorCanSeeOnlyHisPatients(ResultConstraintHandlerProvider):
    def handle(self, result: List[Patient]) -> List[Patient]:
        """
        Doctors are only allowed to see their own patients.
        When the User requesting a list of all patients is of the group "Doctor", the list is filtered. Only those
        patients,which have the requesting User as their attending_doctor are returned.
        @param result: A list of all Patients
        @return: A filtered list of Patients
        """
        filtered_patients = []
        request = client_request.get('request')
        name = request.user.username

        for patient in result:
            if patient.attending_doctor == name:
                filtered_patients.append(patient)
        return filtered_patients

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        "doctor_can_only_see_his_patients"

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        if constraint == "doctor_can_only_see_his_patients":
            return True
        return False
