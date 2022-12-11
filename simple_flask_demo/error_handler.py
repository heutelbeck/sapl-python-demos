def permission_denied(e):
    return "SAPL: Permission denied"


def value_error(e):
    return "You requested something, which you had no permission for. \n" \
           "A Constrainthandler mapped the permission denied Decision into a ValueError Exception, " \
           "which was handled by this ErrorHandler"
