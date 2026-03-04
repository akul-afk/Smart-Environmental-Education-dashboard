"""
Data Explorer Insights — generates short, data-driven insight sentences
for each environmental factor + view combination.

Uses Gemini API (google.genai) when available, otherwise falls back to local templates.
Automatically tries multiple model names until one succeeds.
"""

import os
from dotenv import load_dotenv
from app_logger import logger

# Load .env once
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# Models to try in priority order (most capable → lightest)
_MODEL_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


def generate_data_insight(factor: dict, view_type: str, data_summary: dict) -> str:
    """
    Generate a short insight about an environmental metric.

    Args:
        factor: dict with keys 'key', 'label', 'emoji', 'unit', 'color'
        view_type: 'map' | 'line' | 'bar'
        data_summary: dict with contextual stats

    Returns:
        str: A 1–2 sentence insight with emoji.
    """
    if _GEMINI_KEY:
        try:
            return _gemini_insight(factor, view_type, data_summary)
        except Exception as e:
            logger.error("Gemini data insight failed: %s", e)

    return _local_insight(factor, view_type, data_summary)


# ── Gemini-powered insight ──────────────────────────────────

def _gemini_insight(factor: dict, view_type: str, data_summary: dict) -> str:
    from google import genai

    client = genai.Client(api_key=_GEMINI_KEY)

    view_labels = {"map": "world map", "line": "time-series chart", "bar": "bar chart"}
    view_label = view_labels.get(view_type, "visualization")

    prompt = f"""You are an environmental data analyst. Write exactly ONE short, insightful sentence (max 25 words) about these {factor['label']} statistics shown on a {view_label}. Use 1 emoji at the start.

Data:
{_format_summary(data_summary)}

Factor: {factor['label']} ({factor['unit']})

Rules:
- Be specific with numbers
- Highlight a surprising pattern, comparison, or trend
- No generic statements like "this data shows..."
- Just the one sentence, no prefix or label"""

    # Try each model until one works
    last_err = None
    for model_name in _MODEL_PRIORITY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = response.text.strip()
            text = text.replace("**", "").replace("*", "")
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            logger.info("Gemini data insight generated (%s) for %s/%s", model_name, factor["key"], view_type)
            return text
        except Exception as e:
            last_err = e
            logger.warning("Model %s failed: %s", model_name, str(e)[:120])
            continue

    raise last_err or RuntimeError("All Gemini models failed")


def _format_summary(data_summary: dict) -> str:
    """Format data_summary dict into readable bullet points for the prompt."""
    lines = []
    for k, v in data_summary.items():
        label = k.replace("_", " ").title()
        lines.append(f"- {label}: {v}")
    return "\n".join(lines)


# ── Local template fallback ─────────────────────────────────

def _local_insight(factor: dict, view_type: str, data_summary: dict) -> str:
    """Generate a template-based insight when API is unavailable."""
    emoji = factor.get("emoji", "📊")
    label = factor.get("label", "Metric")
    unit = factor.get("unit", "")

    avg = data_summary.get("avg")
    max_val = data_summary.get("max_val")
    min_val = data_summary.get("min_val")
    max_country = data_summary.get("max_country", "N/A")
    min_country = data_summary.get("min_country", "N/A")
    count = data_summary.get("count", 0)
    year = data_summary.get("year", "")

    if view_type == "map":
        if max_val is not None and min_val is not None:
            spread = max_val - min_val
            return (
                f"{emoji} Across {count} countries, {label.lower()} ranges "
                f"from {min_val:.1f} to {max_val:.1f} {unit} — "
                f"a {spread:.1f} {unit} gap between {min_country} and {max_country}."
            )
        return f"{emoji} Viewing {label.lower()} data across {count} countries ({year})."

    elif view_type == "line":
        country = data_summary.get("country", "Selected country")
        trend = data_summary.get("trend", "stable")
        year_from = data_summary.get("year_from", "")
        year_to = data_summary.get("year_to", "")
        data_points = data_summary.get("data_points", 0)

        if trend == "increasing":
            return f"📈 {country}'s {label.lower()} has been rising from {year_from} to {year_to} ({data_points} data points)."
        elif trend == "decreasing":
            return f"📉 {country}'s {label.lower()} has been declining from {year_from} to {year_to} — a positive sign for sustainability."
        else:
            return f"{emoji} {country}'s {label.lower()} has remained relatively stable over {year_from}–{year_to}."

    elif view_type == "bar":
        mode = data_summary.get("mode", "top10")
        if mode == "top10" and max_country:
            return (
                f"{emoji} {max_country} leads with {max_val:.1f} {unit} — "
                f"the global average is {avg:.1f} {unit}."
            )
        elif mode == "bot10" and min_country:
            return (
                f"{emoji} {min_country} has the lowest {label.lower()} "
                f"at {min_val:.1f} {unit}, well below the {avg:.1f} {unit} average."
            )
        return f"{emoji} Comparing {label.lower()} across {count} countries."

    return f"{emoji} Exploring {label.lower()} data across the globe."
