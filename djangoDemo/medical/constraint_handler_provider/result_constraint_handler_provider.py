from typing import Any

from sapl_base.authorization_subscription_factory import client_request
from sapl_base.constraint_handling.constraint_handler_provider import ResultConstraintHandlerProvider




class FilterPatientsRelatedToStaff(ResultConstraintHandlerProvider):

    def handle(self, result: list) -> list:
        filtered_patients = []
        for patient in result:
            if not patient.is_related_to_staff:
                filtered_patients.append(patient)
        return filtered_patients

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        if constraint == 'filter_patients_related_to_staff':
            return True
        return False


class BlackenDiagnose(ResultConstraintHandlerProvider):

    def handle(self, result):
        result.diagnosis_text = "FORBIDDEN"
        return result

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        if constraint == "blacken_diagnose":
            return True
        return False


class DoctorCanSeeOnlyHisPatients(ResultConstraintHandlerProvider):
    def handle(self, result: Any) -> Any:
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
        if constraint == "doctor_can_only_see_his_patients":
            return True
        return False
