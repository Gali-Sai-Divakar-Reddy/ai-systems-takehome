## Manual Testing

I manually tested the API using the following scenarios.

### 1. Valid Receipt

Request:

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_text": "Uber Eats $34.20\nAWS invoice $412.00\nOffice Depot $28.50\nDelta Airlines $890.00"
  }'
```

Response:

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

---

### 2. Unknown Vendor

Request:

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_text": "Random Vendor $50.00"
  }'
```


Response:

```json
{
  "items": [
    {
      "item": "Random Vendor",
      "amount": 50.0,
      "category": "other"
    }
  ]
}
```

---

### 3. Empty Receipt

Request:

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_text": ""
  }'
```

Response:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": [
        "body",
        "receipt_text"
      ],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {
        "min_length": 1
      }
    }
  ]
}
```

---

### 4. Invalid Receipt Content

Request:

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_text": "asdfasdfasdf"
  }'
```

Response:

{"items" : []}                                                                                                

Observation:

The application did not crash. The upstream model/API failure was caught and converted into a structured HTTP 502 response containing a request identifier for troubleshooting.
---

### 5. Model Failure Scenario

During development I simulated malformed model responses to verify the retry and validation path.

Example simulated response:

```text
This is not valid JSON
```

Observed behavior:

1. Initial parsing failed.
2. The application sent a corrective prompt to the model.
3. The corrected response was validated against the schema.
4. If validation still failed, the API returned a structured error response instead of returning invalid data.
