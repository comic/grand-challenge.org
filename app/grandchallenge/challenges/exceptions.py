class InsufficientBudgetError(Exception):
    def __init__(self, *, reason: str):
        self.reason = reason
        super().__init__(reason)
