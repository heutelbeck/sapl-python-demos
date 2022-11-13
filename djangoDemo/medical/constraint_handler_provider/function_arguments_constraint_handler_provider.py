from sapl_base.constraint_handling.constraint_handler_provider import FunctionArgumentsConstraintHandlerProvider


class MapPatientDetailsToDefault(FunctionArgumentsConstraintHandlerProvider):
    def handle(self, function_arguments: dict) -> dict:
        function_arguments.update({'pk': 1})
        return function_arguments

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        if constraint == 'map_patient_details_to_default':
            return True
        return False


class MapRoomNumberToDoctor(FunctionArgumentsConstraintHandlerProvider):
    def handle(self, function_arguments: dict) -> dict:

        if 'room_number' in function_arguments:
            if function_arguments.get('room_number') < 10:
                function_arguments.update({'attending_doctor': 'Julia'})
        return function_arguments

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        if constraint == 'map_room_to_doctor':
            return True
        return False
