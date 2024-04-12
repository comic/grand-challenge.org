def format_validation_error_message(error):
    if hasattr(error, "message"):
        return error.message
    elif hasattr(error, "messages"):
        return ", ".join(error.messages)
    else:
        return str(error)
