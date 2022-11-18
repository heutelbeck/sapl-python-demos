from sapl_base.constraint_handling.constraint_handler_provider import FunctionArgumentsConstraintHandlerProvider


class MapPatientDetailsToDefault(FunctionArgumentsConstraintHandlerProvider):
    def handle(self, function_arguments: dict) -> dict:
        """
        Modify the pk of patient to the value=1, to return only one specific patient independent of the patient which
        was requested. Interns are allowed to see the page with patient details, but they should only see the details of
        the patient with the pk=1, which is a dummy patient for educational purpose.

        @param function_arguments: A dict containing the values as keywords, with which a function is called
        @return: Modified dict, where the pk which will be requested from the database has been changed to the value=1
        """
        function_arguments.update({'pk': 1})
        return function_arguments

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        'map_patient_details_to_default'

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        if constraint == 'map_patient_details_to_default':
            return True
        return False


class MapRoomNumberToDoctor(FunctionArgumentsConstraintHandlerProvider):
    def handle(self, function_arguments: dict) -> dict:
        """
        Patients, which are relocated to one of the first 10 rooms get julia assigned as their attending doctor.

        @param function_arguments: A dict containing the values as keywords, with which a function is called
        @return: Modified dict, where the value of the parameter 'attending_doctor' is set to julia.
        """
        if 'room_number' in function_arguments:
            if function_arguments.get('room_number') < 10:
                function_arguments.update({'attending_doctor': 'Julia'})
        return function_arguments

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        'map_room_to_doctor'

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        if constraint == 'map_room_to_doctor':
            return True
        return False
