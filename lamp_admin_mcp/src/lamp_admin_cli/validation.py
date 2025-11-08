from pathlib import Path
from typing import Literal
import json

import logging

VALID_FILE_NAME = {
    "test-form": "test_form.json",
    "signature": "signature.json",
    "report": "report.pdf",
}


class ValidationError(Exception):
    pass


def validate_json(json_file: Path):
    with open(json_file, 'r') as f:
        try:
            json.load(f)
        except ValueError:
            return False
    return True



def files_validate_and_convert_path(**kwargs):
    #console = Console()
    test_form = kwargs.get('test_form')
    signature = kwargs.get('signature')
    report = kwargs.get('report')
    if any([test_form, signature, report]):
        logging.info("Validate Files")
    if test_form:
        logging.info("Validate test-form")
        if not validate_json(test_form):
            raise ValidationError("invalid json")
        test_form = Path(test_form)
    if signature:
        logging.info("Validate signautre")
        if not validate_json(signature):
            raise ValidationError("invalid json")
        signature = Path(signature)
    if report:
        logging.info("Validate report")
        report = Path(report)
    return {"test-form": test_form, "signature": signature, "report": report,}
    