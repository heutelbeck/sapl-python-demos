import sys

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medical'

    def ready(self):
        """
        The method ready configure if the application or DB first time runs.
        It initialize the DB and add the demoData and register the constraintService
        """

        if "runserver" not in sys.argv:
            return True
        # import here to avoid AppRegistryNotReady exception
        from medical.demo_data import initialize_database

        initialize_database()

        from sapl_base.constraint_handling.constraint_handler_service import constraint_handler_service
        from medical.constraint_handler_provider.function_arguments_constraint_handler_provider import \
            MapRoomNumberToDoctor, MapPatientDetailsToDefault
        from medical.constraint_handler_provider.result_constraint_handler_provider import BlackenDiagnose, \
            FilterPatientsRelatedToStaff, DoctorCanSeeOnlyHisPatients

        constraint_handler_service.result_handler.append(BlackenDiagnose())
        constraint_handler_service.result_handler.append(FilterPatientsRelatedToStaff())
        constraint_handler_service.result_handler.append(DoctorCanSeeOnlyHisPatients())
        constraint_handler_service.function_arguments_mapper.append(MapRoomNumberToDoctor())
        constraint_handler_service.function_arguments_mapper.append(MapPatientDetailsToDefault())

