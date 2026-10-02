"""Central Gemini integration with JSON parsing and model failover."""
import json
import logging
import os
import re
import time

import requests

from utils.error_handler import ApiError


DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODELS = (
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
)
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS_PER_MODEL = 2
# Full career plans take longer than short AI responses. Allow a slow primary
# model time to finish while preserving the configured model failover chain.
REQUEST_BUDGET_SECONDS = 110
REQUEST_TIMEOUT_SECONDS = 30
logger = logging.getLogger(__name__)


def _configured_models():
    primary = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "").split(",")
    if not any(value.strip() for value in fallbacks):
        fallbacks = DEFAULT_FALLBACK_MODELS

    models = []
    for model in (primary, *fallbacks):
        model = model.strip()
        if model and model not in models:
            models.append(model)
    return models


def _parse_json_response(response):
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def generate(task, payload):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ApiError(
            "AI guidance is not configured on this server. Add a Gemini API key to enable it.",
            503,
            "ai_not_configured",
        )

    prompt = (
        "Return only valid JSON, with concise, useful, truthful career guidance. "
        "Never invent verified URLs. Task: "
        + task
        + "\nContext: "
        + json.dumps(payload, ensure_ascii=False)[:18000]
    )
    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.35},
    }
    failures = []
    deadline = time.monotonic() + REQUEST_BUDGET_SECONDS

    for model in _configured_models():
        if time.monotonic() >= deadline:
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        model_failed_over = False

        for attempt in range(MAX_ATTEMPTS_PER_MODEL):
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                failures.append(("timeout", None))
                model_failed_over = True
                break
            try:
                response = requests.post(
                    url,
                    params={"key": key},
                    json=request_body,
                    timeout=min(REQUEST_TIMEOUT_SECONDS, remaining - 1),
                )

                if response.status_code in (401, 403):
                    raise ApiError(
                        "AI service authentication failed. Please check the server configuration.",
                        502,
                        "ai_auth_failed",
                    )

                if response.status_code == 404:
                    failures.append(("status", 404))
                    logger.warning("Gemini model %s returned HTTP 404; moving to fallback model", model)
                    model_failed_over = True
                    break

                if response.status_code in RETRYABLE_STATUSES:
                    failures.append(("status", response.status_code))
                    provider_status = ""
                    provider_message = ""
                    try:
                        provider_error = response.json().get("error", {})
                        provider_status = str(provider_error.get("status", ""))
                        provider_message = str(provider_error.get("message", ""))
                    except (ValueError, AttributeError):
                        pass
                    provider_message = provider_message.replace(key, "[REDACTED]")[:240]
                    logger.warning(
                        "Gemini model %s returned HTTP %d (%s): %s; applying retry/failover",
                        model,
                        response.status_code,
                        provider_status or "provider status unavailable",
                        provider_message or "provider message unavailable",
                    )
                    if attempt + 1 < MAX_ATTEMPTS_PER_MODEL:
                        time.sleep(min(0.7 * (2**attempt), max(0, deadline - time.monotonic())))
                        continue
                    model_failed_over = True
                    break

                response.raise_for_status()
                try:
                    return _parse_json_response(response)
                except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
                    failures.append(("invalid_response", None))
                    model_failed_over = True
                    break

            except ApiError:
                raise
            except requests.RequestException as exc:
                failures.append(("timeout" if isinstance(exc, requests.Timeout) else "network", None))
                logger.warning("Gemini model %s request failed (%s); applying retry/failover", model, type(exc).__name__)
                if attempt + 1 < MAX_ATTEMPTS_PER_MODEL:
                    time.sleep(min(0.7 * (2**attempt), max(0, deadline - time.monotonic())))
                    continue
                model_failed_over = True
                break

        if not model_failed_over:
            break

    statuses = [status for kind, status in failures if kind == "status"]
    if 429 in statuses:
        raise ApiError(
            "Gemini models are currently rate-limited. Please wait and try again.",
            503,
            "ai_rate_limited",
        )
    if any(status in {500, 502, 503, 504} for status in statuses):
        raise ApiError(
            "Gemini is temporarily unavailable across the configured models. Please try again shortly.",
            503,
            "ai_unavailable",
        )
    if statuses and all(status == 404 for status in statuses):
        raise ApiError(
            "None of the configured Gemini models is available to this API project.",
            503,
            "ai_model_unavailable",
        )
    if failures and all(kind == "timeout" for kind, _ in failures):
        raise ApiError("AI analysis timed out across the configured models. Please try again.", 504, "ai_timeout")
    if failures and all(kind in {"timeout", "network"} for kind, _ in failures):
        raise ApiError("Gemini could not be reached. Please try again shortly.", 503, "ai_unavailable")
    raise ApiError("Gemini did not return usable JSON from the configured models. Please try again.", 502, "ai_invalid_response")
