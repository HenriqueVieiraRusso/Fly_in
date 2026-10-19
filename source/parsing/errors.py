
class ParseError(Exception):
    """Exception raised for errors encountered during parsing.

    Attributes:
        line_number (int): The line number where the parsing error occurred.
        message (str): The explanation of the error.
    """
    def __init__(self, line_number: int, message: str) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")
