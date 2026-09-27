"""Tool schemas and dispatcher.

Seven tools, registered with Anthropic tool-use shape. The dispatcher returns
serialized JSON strings to be wrapped as `tool_result` content. Errors follow
the Playbook "Graceful Tool Failure" shape:

    {"is_error": true,
     "error_category": "transient"|"permanent",
     "is_retryable": bool,
     "message": "..."}

Errors are never raised to the loop.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claims_intake.session import ClaimSession


CLAIM_TYPES = ["property_damage", "theft", "liability", "auto"]
SEVERITIES = ["low", "medium", "high"]


# ----------------------------------------------------------------------------
# Schemas — passed verbatim to the Anthropic Messages API as the `tools` arg.
# ----------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lookup_policy",
        "description": (
            "Look up a policy record using the policy ID. Use this early "
            "in the claim process to verify the policy and retrieve its details "
            "before making a classification."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_id": {
                    "type": "string",
                    "description": "The policy ID to look up.",
                }
            },
            "required": ["policy_id"],
        },
    },
    {
        "name": "record_claim_fact",
        "description": (
            "Record a normalized fact about the claim, such as the incident "
            "date, location, or items lost. Use this when you have a factual "
            "piece of claim information that should be stored."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "The normalized name of the claim fact.",
                },
                "value": {
                    "type": "string",
                    "description": "The value of the claim fact.",
                },
            },
            "required": ["field", "value"],
        },
    },
    {
        "name": "classify_claim",
        "description": (
            "Commit to a claim type after gathering enough information. "
            "Use one of the allowed claim types and provide a confidence "
            "score and rationale explaining the classification."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_type": {
                    "type": "string",
                    "enum": CLAIM_TYPES,
                    "description": "The claim type.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence in the classification, from 0 to 1.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Reasoning supporting the selected claim type.",
                },
            },
            "required": [
                "claim_type",
                "confidence",
                "rationale",
            ],
        },
    },
    {
        "name": "assess_severity",
        "description": (
            "Commit to the severity of the claim after assessing the "
            "available facts. Use low, medium, or high and explain the reasoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": SEVERITIES,
                    "description": "The severity level of the claim.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Reasoning supporting the selected severity.",
                },
            },
            "required": ["severity", "rationale"],
        },
    },
]


# ----------------------------------------------------------------------------
# Errors — Graceful Tool Failure shape
# ----------------------------------------------------------------------------


def _err(category: str, retryable: bool, message: str) -> str:
    return json.dumps(
        {
            "is_error": True,
            "error_category": category,
            "is_retryable": retryable,
            "message": message,
        }
    )


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


# ----------------------------------------------------------------------------
# Tool implementations
# ----------------------------------------------------------------------------

def _t_lookup_policy(session: ClaimSession, inp: dict[str, Any]) -> str:
    policy_id = inp.get("policy_id")

    if not isinstance(policy_id, str):
        return _err(
            "permanent",
            False,
            "policy_id must be a string",
        )

    policy = session.policies.get(policy_id)

    if policy is None:
        return _err(
            "permanent",
            False,
            f"policy_id not found: {policy_id}",
        )

    return _ok(policy)


def _t_record_claim_fact(session: ClaimSession, inp: dict[str, Any]) -> str:
    field = inp.get("field")
    value = inp.get("value")

    if not isinstance(field, str):
        return _err(
            "permanent",
            False,
            "field must be a string",
        )

    if not isinstance(value, str):
        return _err(
            "permanent",
            False,
            "value must be a string",
        )

    session.case_facts[field] = value

    return _ok(
        {
            "recorded": True,
            "field": field,
            "case_facts_count": len(session.case_facts),
        }
    )


def _t_classify_claim(session: ClaimSession, inp: dict[str, Any]) -> str:
    claim_type = inp.get("claim_type")
    confidence = inp.get("confidence")
    rationale = inp.get("rationale")

    if claim_type not in CLAIM_TYPES:
        return _err(
            "permanent",
            False,
            f"invalid claim_type: {claim_type}",
        )

    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return _err(
            "permanent",
            False,
            "confidence must be a number",
        )

    if not 0 <= confidence <= 1:
        return _err(
            "permanent",
            False,
            "confidence must be between 0 and 1",
        )

    if not isinstance(rationale, str):
        return _err(
            "permanent",
            False,
            "rationale must be a string",
        )

    session.classification = {
        "claim_type": claim_type,
        "confidence": confidence,
        "rationale": rationale,
    }

    return _ok(
        {
            "recorded": True,
            "claim_type": claim_type,
            "confidence": confidence,
            "rationale": rationale,
        }
    )


def _t_assess_severity(session: ClaimSession, inp: dict[str, Any]) -> str:
    severity = inp.get("severity")
    rationale = inp.get("rationale")

    if severity not in SEVERITIES:
        return _err(
            "permanent",
            False,
            f"invalid severity: {severity}",
        )

    if not isinstance(rationale, str):
        return _err(
            "permanent",
            False,
            "rationale must be a string",
        )

    session.severity = {
        "severity": severity,
        "rationale": rationale,
    }

    return _ok(
        {
            "recorded": True,
            "severity": severity,
            "rationale": rationale,
        }
    )


# ----------------------------------------------------------------------------
# Exercise 3 tools — leave these as TODO for now
# ----------------------------------------------------------------------------


def _t_request_clarification(session: ClaimSession, inp: dict[str, Any]) -> str:
    # TODO: Implement in Exercise 3.
    return _err(
        "permanent",
        False,
        "TODO: _t_request_clarification not implemented yet",
    )


def _t_route_to_adjuster(session: ClaimSession, inp: dict[str, Any]) -> str:
    # TODO: Implement in Exercise 3.
    return _err(
        "permanent",
        False,
        "TODO: _t_route_to_adjuster not implemented yet",
    )


def _t_escalate_to_human(session: ClaimSession, inp: dict[str, Any]) -> str:
    # TODO: Implement in Exercise 3.
    return _err(
        "permanent",
        False,
        "TODO: _t_escalate_to_human not implemented yet",
    )


# ----------------------------------------------------------------------------
# Dispatcher
# ----------------------------------------------------------------------------


_DISPATCH = {
    "lookup_policy": _t_lookup_policy,
    "record_claim_fact": _t_record_claim_fact,
    "classify_claim": _t_classify_claim,
    "assess_severity": _t_assess_severity,
    "request_clarification": _t_request_clarification,
    "route_to_adjuster": _t_route_to_adjuster,
    "escalate_to_human": _t_escalate_to_human,
}


def make_executor(session: ClaimSession) -> Executor:
    """Return a ToolExecutor callable bound to this session."""

    def execute(name: str, tool_input: dict[str, Any]) -> str:
        handler = _DISPATCH.get(name)

        if handler is None:
            return _err(
                "permanent",
                False,
                f"unknown tool: {name}",
            )

        try:
            return handler(session, tool_input)

        except Exception as exc:
            # Defensive: anything raised inside a handler becomes a graceful
            # error, never crashes the loop.
            return _err(
                "transient",
                True,
                f"{type(exc).__name__}: {exc}",
            )

    return execute


# Type alias for clarity; the loop only sees a Callable.
Executor = Any


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )