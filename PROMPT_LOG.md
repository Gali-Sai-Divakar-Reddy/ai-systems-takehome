# Prompt Log

## Prompt 1

I reviewed the scaffold and identified that the primary reliability issue was the application returning raw model output without validating its structure or contents.

I used AI to discuss potential failure modes of LLM-based systems and confirm whether validation of model output was the highest-priority issue to address.

## Outcome

This reinforced my decision to focus first on schema validation and error handling before considering additional improvements.

## Prompt 2

I asked for examples of common techniques used when consuming LLM output in production systems, including:

- Schema validation
- Structured JSON responses
- Category constraints
- Error handling patterns

## Outcome

I used this information to compare different approaches and selected a Pydantic-based validation layer because it was simple, reliable, and appropriate for the scope of the assignment.

## Prompt 3

After implementing validation, I explored additional reliability improvements and asked about tradeoffs between:

- Returning raw errors
- Retrying invalid model responses
- Falling back to rule-based parsing

## Outcome

Based on that discussion, I added a single retry path with a corrective prompt because it directly addressed a failure mode mentioned in the assignment while keeping the implementation small.

## Prompt 4

I discussed how to document the solution and explain tradeoffs clearly.

## Outcome

I used that feedback to organize my submission notes around:

- The most important problem identified
- The changes implemented
- Known limitations
- Future improvements

The final design decisions, implementation, and testing were completed and verified manually.