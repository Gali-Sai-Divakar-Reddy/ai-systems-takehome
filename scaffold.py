import json
import logging
import os
import re
import uuid
from enum import Enum
from typing import List

import anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Receipt Parser")


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class Category(str, Enum):
    meals = "meals"
    travel = "travel"
    software = "software"
    office_supplies = "office_supplies"
    other = "other"


class ReceiptRequest(BaseModel):
    receipt_text: str = Field(..., min_length=1)


class LineItem(BaseModel):
    item: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    category: Category


class ReceiptResponse(BaseModel):
    items: List[LineItem]


SYSTEM_PROMPT = """
You are a receipt parser.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations.

The JSON must match this schema exactly:

{
  "items": [
    {
      "item": "string",
      "amount": 12.34,
      "category": "meals | travel | software | office_supplies | other"
    }
  ]
}

Rules:
- Extract each receipt line item separately.
- Amount must be a number, not a string.
- Do not include dollar signs in amount.
- Category must be one of: meals, travel, software, office_supplies, other.
- If the category is unclear, use "other".
"""


REPAIR_PROMPT = """
The previous response could not be parsed or validated.

Return ONLY corrected valid JSON matching this schema:

{
  "items": [
    {
      "item": "string",
      "amount": 12.34,
      "category": "meals | travel | software | office_supplies | other"
    }
  ]
}

Do not include markdown or explanation.
"""


def call_model(receipt_text: str, request_id: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": receipt_text,
            }
        ],
    )

    if not message.content:
        raise ValueError("Model returned empty content")

    raw_text = message.content[0].text
    logger.info("request_id=%s raw_model_response=%s", request_id, raw_text)
    return raw_text


def repair_model_response(
    receipt_text: str,
    bad_response: str,
    validation_error: str,
    request_id: str,
) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        system=REPAIR_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Original receipt:\n{receipt_text}\n\n"
                    f"Invalid model response:\n{bad_response}\n\n"
                    f"Validation/parsing error:\n{validation_error}"
                ),
            }
        ],
    )

    if not message.content:
        raise ValueError("Repair attempt returned empty content")

    repaired_text = message.content[0].text
    logger.info("request_id=%s repaired_model_response=%s", request_id, repaired_text)
    return repaired_text


def extract_json(raw_text: str) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response")

        return json.loads(match.group(0))


def parse_and_validate(raw_text: str) -> ReceiptResponse:
    parsed_json = extract_json(raw_text)
    return ReceiptResponse.model_validate(parsed_json)


@app.post("/parse", response_model=ReceiptResponse)
def parse_receipt(request: ReceiptRequest):
    request_id = str(uuid.uuid4())

    logger.info(
        "request_id=%s receipt_length=%s",
        request_id,
        len(request.receipt_text),
    )

    try:
        raw_response = call_model(request.receipt_text, request_id)

        try:
            parsed_response = parse_and_validate(raw_response)
            logger.info("request_id=%s parsed_items=%s", request_id, parsed_response)
            return parsed_response

        except (ValidationError, ValueError, json.JSONDecodeError) as first_error:
            logger.warning(
                "request_id=%s initial_parse_failed=%s",
                request_id,
                str(first_error),
            )

            repaired_response = repair_model_response(
                receipt_text=request.receipt_text,
                bad_response=raw_response,
                validation_error=str(first_error),
                request_id=request_id,
            )

            try:
                parsed_repaired_response = parse_and_validate(repaired_response)
                logger.info(
                    "request_id=%s repaired_parse_success=%s",
                    request_id,
                    parsed_repaired_response,
                )
                return parsed_repaired_response

            except (ValidationError, ValueError, json.JSONDecodeError) as second_error:
                logger.exception(
                    "request_id=%s repaired_parse_failed=%s",
                    request_id,
                    str(second_error),
                )
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Model response could not be parsed into the expected receipt schema.",
                        "request_id": request_id,
                    },
                )

    except anthropic.APIError as error:
        logger.exception("request_id=%s anthropic_api_error=%s", request_id, str(error))
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI provider request failed.",
                "request_id": request_id,
            },
        )

    except HTTPException:
        raise

    except Exception as error:
        logger.exception("request_id=%s unexpected_error=%s", request_id, str(error))
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unexpected server error.",
                "request_id": request_id,
            },
        )
