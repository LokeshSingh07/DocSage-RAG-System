"""Input and output guardrails for the RAG Project. 
    check_input(question)  -> cleaned question, or raises GuardrailError
    check_output(answer)   -> answer with secrets redacted
"""

import re
import unicodedata
import logging


log = logging.getLogger(__name__)

MAX_INPUT_CHARS = 2000
MAX_OUTPUT_CHARS = 8000
FALLBACK_ANSWER = "I could not produce a valid answer. Please try rephrasing your question."


class GuardrailError(ValueError):
    """Raised when an input is rejected. The message is safe to show to the user."""



# ---------------------------------------------------------------
# INPUT GUARDRAIL
# ---------------------------------------------------------------
_INJECTION_PATTERNS=[
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|prompts?|rules)",
    r"disregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)?\s*(instructions|prompts?|rules)",
    r"forget\s+(all\s+|everything\s+)?(your|the|previous)\s+(instructions|rules|prompt)",
    r"(reveal|show|print|repeat|leak)\s+(me\s+)?(your|the)\s+(system|hidden|initial)\s+(prompt|instructions|message)",
    r"what\s+(is|are)\s+your\s+(system\s+prompt|instructions)",
    r"you\s+are\s+now\s+(in\s+)?(developer|dan|jailbreak|god)\s*mode",
    r"\bjailbreak\b",
    r"\bdo\s+anything\s+now\b",
    r"<\s*/?\s*(system|assistant)\s*>",
]

# turns a pattern string into a reusable regex object
_INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.IGNORECASE)
 
# Control characters except newline and tab.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Invisible characters often used to hide text. U+200C and U+200D (ZWNJ/ZWJ) are deliberately kept because Hindi and other Indic scripts need them.
_INVISIBLE_RE = re.compile(r"[\u200b\u200e\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
 
 

def input_guardrail(question: str):
    """Validate and clean an input question. Return the cleaned text"""

    if not isinstance(question, str) or not question.strip():
        raise GuardrailError("Question cannot be empty")

    if len(question) > MAX_INPUT_CHARS:
        log.warning("input blocked: oversized (%d chars)", len(question))
        raise GuardrailError("Question too long")


    # 1. Sanitize the input question
    question = unicodedata.normalize("NFKC", question)
    question = _CONTROL_RE.sub("", question)
    question = _INVISIBLE_RE.sub("", question)
    question = re.sub(r"[ \t]+", " ", question).strip()

    if not question:
        raise GuardrailError("Question cannot be empty")


    if len(question) > MAX_INPUT_CHARS:
        log.warning("input blocked: oversized (%d chars)", len(question))
        raise GuardrailError("Question too long")

    # 2. Then check. Reject instead of deleting the phrase: deleting is bypassable ("ignore ignore previous instructions previous instructions") and silently changes what the user asked.
    if _INJECTION_RE.search(question):
        log.warning("Input Blocked: prompt-injection pattern")
        raise GuardrailError(
            "This request looks like an attempt to override the assistant's "
            "instructions, so it was blocked."
        )
    

    return question
    





# ---------------------------------------------------------------
# OUTPUT GUARDRAIL
# ---------------------------------------------------------------
_SENSITIVE_OUTPUT_PATTERNS=[
    # AWS access key IDs
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # AWS secret key when labelled
    (
        re.compile(
            r"(aws_secret_access_key\s*[:=]\s*)['\"]?[A-Za-z0-9/+=]{40}['\"]?",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    # PEM private keys
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # Database URLs containing a password: scheme://user:password@host
    (
        re.compile(r"\b([a-z][a-z0-9+.\-]*://[^\s:/@]+):[^\s@]+@", re.IGNORECASE),
        r"\1:[REDACTED]@",
    ),
    # Bearer tokens
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}", re.IGNORECASE), "Bearer [REDACTED]"),
    # Common API key prefixes (sk-..., pcsk_..., ghp_..., xox?-...)
    (
        re.compile(r"\b(sk-|pcsk_|ghp_|gho_|xox[abprs]-)[A-Za-z0-9_\-]{16,}"),
        "[REDACTED_API_KEY]",
    ),
    # Labelled secrets: api_key = "...", password: ..., token=...
    (
        re.compile(
            r"\b(api[_\-]?key|secret|password|passwd|token)(\s*[:=]\s*)['\"]?[^\s'\",;]{8,}['\"]?",
            re.IGNORECASE,
        ),
        r"\1\2[REDACTED]",
    ),
    # Google API keys
    (
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "[REDACTED_GOOGLE_API_KEY]",
    ),

    # JWT tokens (three Base64URL segments)
    (
        re.compile(
            r"\beyJ[A-Za-z0-9_-]*\."
            r"[A-Za-z0-9_-]+\."
            r"[A-Za-z0-9_-]+\b"
        ),
        "[REDACTED_JWT]",
    ),
]


def output_guardrail(answer: str):
    """Clean a model answer: redact secrets, cap length, avoid empty replies."""
    
    if not isinstance(answer, str) or not answer.strip():
        return FALLBACK_ANSWER

    answer = answer.strip()

    # Redact BEFORE truncating, so a secret is never cut in half and left visible.
    redactions = 0
    for pattern, replacement in _SENSITIVE_OUTPUT_PATTERNS:
        answer, count = pattern.subn(replacement, answer)
        redactions += count

    if redactions:
        log.warning("Redacted %d secrets in output", redactions)

        
    if len(answer) > MAX_OUTPUT_CHARS:
        answer = answer[:MAX_OUTPUT_CHARS].rstrip() + "\n\n[TRUNCATED]"

    return answer




# ---------------------------------------------------------------
# alias for input_guardrail and output_guardrail
# ---------------------------------------------------------------
check_input = input_guardrail
check_output = output_guardrail