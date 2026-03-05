# Advanced Guide: Building NLU Systems with LLMs, Tool Calling, and Structured Outputs

Author: Generated Guide

------------------------------------------------------------------------

# 1. Overview

Modern Natural Language Understanding (NLU) systems increasingly use
**LLMs as structured classifiers** rather than free‑form text
generators.

Instead of prompting the model to produce arbitrary text, we constrain
outputs using:

-   JSON schemas
-   Function / tool calling
-   Enumerated intents
-   Deterministic generation settings

This produces **predictable machine-readable outputs** that can safely
drive backend logic.

------------------------------------------------------------------------

# 2. Conceptual Architecture

A typical LLM-powered NLU pipeline:

    User message
         │
         ▼
    LLM classifier
     (temperature=0)
         │
         ▼
    Structured output (JSON)
         │
         ▼
    Business logic router
         │
         ├── booking service
         ├── FAQ retrieval
         ├── support escalation
         └── clarification question

------------------------------------------------------------------------

# 3. Tool Calling vs Structured Outputs vs Prompted JSON

There are three main ways to obtain structured outputs.

## 3.1 Tool / Function Calling

The model generates **arguments to a declared function**.

Example:

    tools=[{"type":"function","function":schema}]

Advantages

-   robust parsing
-   strong schema adherence
-   natural integration with backend actions

Best used when:

-   model output triggers application logic
-   you want the model to "choose an action"

------------------------------------------------------------------------

## 3.2 Structured Outputs (JSON Schema)

The model directly returns structured JSON following a schema.

Advantages

-   simpler when no tool execution is needed
-   lower complexity

Best used when:

-   the output is purely classification or extraction.

------------------------------------------------------------------------

## 3.3 Prompted JSON

Example:

    Return JSON with fields intent and location

Drawbacks

-   fragile formatting
-   hallucinated keys
-   inconsistent output

Avoid for production systems.

------------------------------------------------------------------------

# 4. Designing Robust Intent Classification

## 4.1 Enumerated intents

Always constrain intents with enums.

Example

    "intent": {
      "type": "string",
      "enum": [
        "book_tour",
        "ask_info",
        "change_booking",
        "cancel_booking",
        "complaint",
        "out_of_scope"
      ]
    }

Benefits

-   deterministic routing
-   no synonym drift
-   easy analytics

------------------------------------------------------------------------

# 5. Entity Extraction Strategy

Entities should be **separate fields**, not embedded in the intent.

Example structure

    intent
    location
    category
    date_text
    party_size

Example user input

    I want a food tour in Barcelona tomorrow for 3 people

Structured output

    intent = book_tour
    category = food
    location = Barcelona
    date_text = tomorrow
    party_size = 3

------------------------------------------------------------------------

# 6. Avoiding Hallucinated Fields

Always include

    additionalProperties: false

This prevents unexpected keys.

------------------------------------------------------------------------

# 7. Clarification Handling Pattern

Many requests lack enough information.

Example

User message

    I want to book a tour

Output

    intent = book_tour
    needs_clarification = true
    clarification_question = "Which city would you like the tour in?"

------------------------------------------------------------------------

# 8. Confidence-Based Routing

Confidence values allow fallback logic.

Example routing

  Confidence   Action
  ------------ -------------------
  \>0.8        automatic routing
  0.5--0.8     confirm intent
  \<0.5        ask clarification

Note: LLM confidence is heuristic.

------------------------------------------------------------------------

# 9. Production Guardrails

Important safeguards.

## 9.1 Temperature

    temperature = 0

Ensures deterministic classification.

------------------------------------------------------------------------

## 9.2 Schema strictness

Use

    strict: true

to enforce schema adherence.

------------------------------------------------------------------------

## 9.3 Limit output tokens

    max_tokens = 200

Prevents runaway responses.

------------------------------------------------------------------------

# 10. Parsing Tool Calls in Python

Example processing logic.

``` python

response = await client.chat.completions.create(...)

tool_call = response.choices[0].message.tool_calls[0]

arguments = json.loads(tool_call.arguments)

intent = arguments["intent"]

if intent == "book_tour":
    route_to_booking(arguments)
```

------------------------------------------------------------------------

# 11. Multi‑Model Production Pattern

Many production systems use **model cascades**.

    cheap classifier model
            │
            ▼
    high accuracy model fallback
            │
            ▼
    human escalation

Benefits

-   lower cost
-   higher reliability

------------------------------------------------------------------------

# 12. Logging and Analytics

Always log:

-   user message
-   model output
-   routing decision
-   downstream result

These logs enable:

-   prompt improvements
-   schema adjustments
-   intent taxonomy refinement

------------------------------------------------------------------------

# 13. Example Full Schema

    NLU_FUNCTION_SCHEMA = {
    "name": "classify_tourism_request",
    "description": "Classify tourism related requests",
    "strict": True,
    "parameters": {
    "type": "object",
    "additionalProperties": False,
    "properties": {

    "intent": {
    "type": "string",
    "enum": [
    "book_tour",
    "ask_info",
    "change_booking",
    "cancel_booking",
    "complaint",
    "out_of_scope"
    ]
    },

    "category": {
    "type": "string",
    "enum": [
    "city",
    "food",
    "museum",
    "nature",
    "adventure",
    "nightlife",
    "transport",
    "accommodation",
    "other",
    "unknown"
    ]
    },

    "location": {"type":"string"},

    "date_text": {"type":"string"},

    "party_size": {
    "type":"integer",
    "minimum":1
    },

    "language": {
    "type":"string",
    "enum":["es","en","fr","de","it","unknown"]
    },

    "confidence":{
    "type":"number",
    "minimum":0,
    "maximum":1
    },

    "needs_clarification":{
    "type":"boolean"
    },

    "clarification_question":{
    "type":"string"
    }

    },

    "required":[
    "intent",
    "language",
    "confidence",
    "needs_clarification"
    ]

    }
    }

------------------------------------------------------------------------

# 14. Example Model Output

Input

    Quiero reservar un tour gastronómico en Madrid para 4 personas mañana

Output

    {
    "intent":"book_tour",
    "category":"food",
    "location":"Madrid",
    "date_text":"mañana",
    "party_size":4,
    "language":"es",
    "confidence":0.93,
    "needs_clarification":false,
    "clarification_question":""
    }

------------------------------------------------------------------------

# 15. Key Takeaways

-   Treat LLMs as **structured classifiers**
-   Design schemas carefully
-   Always constrain intents with enums
-   Separate classification from entity extraction
-   Use clarification patterns
-   Implement guardrails and logging

A well-designed schema typically improves NLU reliability **more than
prompt tuning alone**.
