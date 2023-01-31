from sapl_base.constraint_handling.constraint_handler_service import constraint_handler_service

from . import function_arguments_constraint_handler_provider as functions
from . import result_constraint_handler_provider as results
from . import error_constraint_handler_provider as errors
from . import on_decision_constraint_handler_provider as on_decisions

constraint_handler_service.register_result_constraint_handler_provider(
    [results.FilterPatientsRelatedToStaff(), results.BlackenDiagnose(), results.DoctorCanSeeOnlyHisPatients()])

constraint_handler_service.register_function_arguments_constraint_handler_provider(
    [functions.MapPatientDetailsToDefault(), functions.MapRoomNumberToDoctor()])

constraint_handler_service.register_error_constraint_handler_provider(
    [errors.LogErrorConstraintHandler()])
