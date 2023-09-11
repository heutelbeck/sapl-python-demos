import sys

import django
from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medical'

    def ready(self):
        """
        The method ready configure if the application or DB first time runs.
        It initializes the DB and add the demoData and register the constraintService
        """

        if "runserver" not in sys.argv:
            return True
        # import here to avoid AppRegistryNotReady exception
        from medical.demo_data import initialize_database
        initialize_database()
        import medical.constraint_handler_provider

