# Submission Notes

## Demo Video

[Watch the working output demo video](https://www.youtube.com/watch?v=tvme5A2-sBM)

## Most Important Problem Identified

The most important issue in the original implementation was that it trusted the language model output directly.

The original endpoint sent receipt text to the model and returned the raw model response as a string. That is unreliable because an LLM can return malformed JSON, extra explanation text, missing fields, invalid category names, or otherwise unexpected output. In those cases, the application could either return garbage to the caller or fail unexpectedly.

I focused on treating the model response as untrusted input and validating it before returning it from the API.

## What I Built

I kept the FastAPI structure because the scaffold was already small and appropriate for this task.

I added:

- A structured response schema using Pydantic.
- A category enum limiting values to: meals, travel, software, office_supplies, and other.
- A stricter prompt asking the model to return only JSON in the expected schema.
- JSON parsing before returning the response.
- Pydantic validation of the parsed model output.
- Explicit error handling for malformed model output.
- Explicit handling for Anthropic API errors.
- A single retry path with a corrective prompt if the first response cannot be parsed or validated.
- Logging with a request ID so parsing failures can be traced.

## What I Deliberately Left Out

I did not add authentication, database storage, background jobs, Docker, deployment scripts, or a frontend. Those would not directly address the main reliability issue in the scaffold.

I also did not try to build a full production-grade receipt parser. The goal was to make a narrow, working improvement within the time limit by focusing on validating model output and handling failure cases clearly.

## Where the Solution Would Still Break

The solution can still fail if the model returns invalid output twice, even after the repair prompt. In that case, the API returns a structured 422 error instead of returning bad data.

It may also produce incorrect but valid categories. For example, if the model classifies an ambiguous vendor as "other" when it should be "software", the schema validation would still pass because the output is structurally valid.

The parser may also struggle with unusual receipt formats, multiple currencies, taxes, subtotals, discounts, or receipts where the item name and amount are not clearly separated.

## What I Would Fix Next With More Time

With more time, I would add:

- Unit tests for valid responses, malformed JSON, invalid categories, and retry behavior.
- More robust receipt parsing rules for subtotals, taxes, and discounts.
- Structured logging with redaction so sensitive receipt data is not logged directly.
- Metrics for model failure rate, retry rate, and validation failure rate.
- Request-level tracing for easier debugging.
- Anthropic tool use or another model-native structured output approach to reduce JSON parsing failures.
- A deterministic fallback parser for simple receipt lines.

# Setup and Running the Application

## Prerequisites

- Python 3.11+
- Anthropic API key

## Environment Setup

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=<your_api_key>
```

## Running the Application

Start the FastAPI server:

```bash
python -m uvicorn scaffold:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

## Example Request

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_text": "Uber Eats       $34.20\nAWS invoice     $412.00\nOffice Depot    $28.50\nDelta Airlines  $890.00"
  }'
```

## Example Response

```json
{
  "items": [
    {
      "item": "Uber Eats",
      "amount": 34.2,
      "category": "meals"
    },
    {
      "item": "AWS invoice",
      "amount": 412.0,
      "category": "software"
    },
    {
      "item": "Office Depot",
      "amount": 28.5,
      "category": "office_supplies"
    },
    {
      "item": "Delta Airlines",
      "amount": 890.0,
      "category": "travel"
    }
  ]
}
```
