class CONSTANTS:
    """Constants cannot be changed at runtime"""

    TOKEN_KEY_LENGTH = 8

    def __setattr__(self, *args, **kwargs):
        raise Exception(
            """
            Constant values must NEVER be changed at runtime, as they are
            integral to the structure of database tables
            """
        )


CONSTANTS = CONSTANTS()
