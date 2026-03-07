"""
Data Explorer Insights — generates structured, educational insight text
for each environmental factor + view combination.

Uses Gemini API (google.genai) when available, otherwise falls back to local templates.
Automatically tries multiple model names until one succeeds.

Output format (3 parts):
  1. Observation  — main pattern visible in the data
  2. Comparison   — country value vs global stats
  3. Environmental Meaning — why the trend matters
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

# Environmental context per factor key
_ENV_CONTEXT = {
    "co2_per_capita": (
        "CO₂ emissions directly drive global warming. Higher per‑capita values indicate "
        "fossil‑fuel dependence, while declines suggest energy transition progress."
    ),
    "renewable_percentage": (
        "Higher renewable energy share reduces greenhouse gas emissions and fossil‑fuel "
        "dependency. Rapid growth signals strong clean‑energy policy."
    ),
    "forest_area_percentage": (
        "Forests act as carbon sinks, absorbing ~2.6 billion tonnes of CO₂ annually. "
        "Declining forest cover accelerates climate change and biodiversity loss."
    ),
    "pm25": (
        "PM2.5 particles penetrate deep into lungs and blood. WHO guideline is 5 µg/m³. "
        "Values above 35 µg/m³ are considered hazardous to health."
    ),
}


def generate_data_insight(factor: dict, view_type: str, data_summary: dict) -> str:
    """
    Generate a structured educational insight about an environmental metric.

    Returns:
        str: A 3–5 sentence insight with Observation, Comparison, and
             Environmental Meaning sections, formatted with bold labels.
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

    view_labels = {"map": "world choropleth map", "line": "time-series line chart", "bar": "bar chart"}
    view_label = view_labels.get(view_type, "visualization")

    prompt = f"""You are an environmental data educator. Write a concise, structured insight (3–5 sentences total) for a {view_label} showing {factor['label']} ({factor['unit']}).

DATA PROVIDED (use ONLY these numbers — do NOT invent values):
{_format_summary(data_summary)}

STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS:
**Observation:** [1 sentence describing the main visible pattern — trend direction, stability, notable spikes or dips]
**Comparison:** [1 sentence comparing the selected country or region with the global average, highest, and/or lowest values from the data]
**Environmental Meaning:** [1–2 sentences explaining why this pattern matters for the environment, climate, or human health]

RULES:
- Use ONLY the statistics listed above — never hallucinate or invent numbers
- Be specific; reference exact values and country names from the data
- Use 1 relevant emoji at the very start of your response
- Do NOT add any prefix like "Here is..." — start directly with the emoji
- Keep total length under 60 words"""

    last_err = None
    for model_name in _MODEL_PRIORITY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = response.text.strip()
            # Clean markdown artifacts
            text = text.replace("***", "**").replace("* ", "")
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            logger.info("Gemini educational insight generated (%s) for %s/%s", model_name, factor["key"], view_type)
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
    """Generate a template-based 3-part insight when API is unavailable."""
    emoji = factor.get("emoji", "📊")
    label = factor.get("label", "Metric")
    unit = factor.get("unit", "")
    key = factor.get("key", "")

    avg = data_summary.get("avg")
    max_val = data_summary.get("max_val")
    min_val = data_summary.get("min_val")
    max_country = data_summary.get("max_country", "N/A")
    min_country = data_summary.get("min_country", "N/A")
    env_context = _ENV_CONTEXT.get(key, f"Changes in {label.lower()} have significant environmental implications.")

    if view_type == "map":
        if max_val is not None and min_val is not None:
            observation = (
                f"Across {data_summary.get('count', 0)} countries, {label.lower()} "
                f"shows wide variation from {min_val:.1f} to {max_val:.1f} {unit}."
            )
            comparison = (
                f"The global average is {avg:.1f} {unit}, with {max_country} at the "
                f"top ({max_val:.1f}) and {min_country} at the bottom ({min_val:.1f})."
            )
        else:
            observation = f"Viewing {label.lower()} data across {data_summary.get('count', 0)} countries."
            comparison = "Insufficient data for comparison."

    elif view_type == "line":
        country = data_summary.get("country", "Selected country")
        trend = data_summary.get("trend", "stable")
        year_from = data_summary.get("year_from", "")
        year_to = data_summary.get("year_to", "")
        first_val = data_summary.get("first_val")
        last_val = data_summary.get("last_val")

        trend_word = {"increasing": "upward", "decreasing": "downward"}.get(trend, "stable")
        observation = (
            f"{country}'s {label.lower()} shows a {trend_word} trend "
            f"from {year_from} to {year_to}"
        )
        if first_val is not None and last_val is not None:
            observation += f", moving from {first_val:.1f} to {last_val:.1f} {unit}."
        else:
            observation += "."

        if avg is not None:
            comparison = (
                f"The global average is {avg:.1f} {unit} "
                f"(highest: {max_country} at {max_val:.1f}, "
                f"lowest: {min_country} at {min_val:.1f})."
            )
        else:
            comparison = "Global comparison data unavailable."

    elif view_type == "bar":
        mode = data_summary.get("mode", "top10")
        if mode == "top10" and max_country:
            observation = (
                f"{max_country} leads with {max_val:.1f} {unit}, "
                f"standing out among the top emitters."
            )
        elif mode == "bot10" and min_country:
            observation = (
                f"{min_country} has the lowest {label.lower()} "
                f"at {min_val:.1f} {unit}."
            )
        else:
            observation = f"Comparing {label.lower()} across {data_summary.get('count', 0)} countries."

        comparison = f"The global average is {avg:.1f} {unit}." if avg else ""

    else:
        observation = f"Exploring {label.lower()} data across the globe."
        comparison = ""

    meaning = f"**Environmental Meaning:** {env_context}"
    parts = [f"{emoji} **Observation:** {observation}"]
    if comparison:
        parts.append(f"**Comparison:** {comparison}")
    parts.append(meaning)

    return " ".join(parts)
