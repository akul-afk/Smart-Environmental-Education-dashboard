"""
Lesson Manager — Transactional ingestion of structured lesson content.
Validates biome existence, prevents duplicates, and logs all operations.
"""

import json
from app_logger import logger


def ingest_lessons(conn, payload: dict) -> dict:
    """
    Ingest a single biome payload with lessons into the database.

    Args:
        conn: psycopg2 connection
        payload: dict with "biome_slug" and "lessons" list

    Returns:
        dict with summary: lessons_inserted, lessons_skipped,
        quiz_questions_inserted, key_terms_inserted, errors
    """
    summary = {
        "biome_slug": payload.get("biome_slug"),
        "lessons_inserted": 0,
        "lessons_skipped": 0,
        "quiz_questions_inserted": 0,
        "key_terms_inserted": 0,
        "errors": [],
    }

    biome_slug = payload.get("biome_slug")
    lessons = payload.get("lessons", [])

    if not biome_slug:
        summary["errors"].append("Missing biome_slug in payload")
        logger.error("Ingestion aborted: missing biome_slug")
        return summary

    cur = conn.cursor()

    try:
        # Step 1: Verify biome exists
        cur.execute("SELECT id FROM biomes WHERE slug = %s", (biome_slug,))
        row = cur.fetchone()
        if row is None:
            msg = f"Biome '{biome_slug}' not found in database"
            summary["errors"].append(msg)
            logger.error("Ingestion aborted: %s", msg)
            cur.close()
            return summary

        biome_id = row[0]
        logger.info("Ingesting lessons for biome '%s' (id=%d)", biome_slug, biome_id)

        for lesson_data in lessons:
            lesson_slug = lesson_data.get("lesson_slug")
            title = lesson_data.get("title", "Untitled")

            if not lesson_slug:
                summary["errors"].append(f"Lesson missing lesson_slug: {title}")
                continue

            # Step 2: Check for duplicate lesson
            cur.execute("SELECT id FROM lessons WHERE lesson_slug = %s", (lesson_slug,))
            if cur.fetchone() is not None:
                summary["lessons_skipped"] += 1
                logger.info("Lesson already exists, skipping: %s", lesson_slug)
                continue

            # Step 3: Build content_json (full lesson payload)
            content_json = json.dumps({
                "learning_objectives": lesson_data.get("learning_objectives", []),
                "sections": lesson_data.get("sections", []),
                "real_world_example": lesson_data.get("real_world_example", ""),
            })

            # Compute XP reward from difficulty
            difficulty = lesson_data.get("difficulty", "beginner").lower()
            xp_map = {"beginner": 50, "intermediate": 75, "advanced": 100}
            xp_reward = xp_map.get(difficulty, 50)

            cur.execute("""
                INSERT INTO lessons (biome_id, lesson_slug, title, difficulty,
                                     estimated_minutes, xp_reward, content_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                biome_id, lesson_slug, title,
                difficulty,
                lesson_data.get("estimated_minutes", 10),
                xp_reward,
                content_json,
            ))
            lesson_id = cur.fetchone()[0]
            summary["lessons_inserted"] += 1
            logger.info("Inserted lesson: %s (id=%d)", lesson_slug, lesson_id)

            # Step 4: Insert quiz questions
            for q in lesson_data.get("quiz", []):
                question_text = q.get("question", "")
                if not question_text:
                    continue

                # Prevent duplicate questions for same lesson
                cur.execute("""
                    SELECT id FROM quiz_questions
                    WHERE lesson_id = %s AND question_text = %s
                """, (lesson_id, question_text))
                if cur.fetchone() is not None:
                    continue

                cur.execute("""
                    INSERT INTO quiz_questions (lesson_id, question_text,
                                                options_json, correct_index, explanation)
                    VALUES (%s, %s, %s, %s, %s);
                """, (
                    lesson_id, question_text,
                    json.dumps(q.get("options", [])),
                    q.get("correct_index", 0),
                    q.get("explanation", ""),
                ))
                summary["quiz_questions_inserted"] += 1

            # Step 5: Insert key terms
            for term in lesson_data.get("key_terms", []):
                cur.execute("""
                    SELECT id FROM key_terms
                    WHERE lesson_id = %s AND term = %s
                """, (lesson_id, term))
                if cur.fetchone() is not None:
                    continue

                cur.execute("""
                    INSERT INTO key_terms (lesson_id, term)
                    VALUES (%s, %s);
                """, (lesson_id, term))
                summary["key_terms_inserted"] += 1

        # Step 6: Commit transaction
        conn.commit()
        logger.info(
            "Ingestion complete for '%s': %d inserted, %d skipped, %d quiz Qs, %d terms",
            biome_slug, summary["lessons_inserted"], summary["lessons_skipped"],
            summary["quiz_questions_inserted"], summary["key_terms_inserted"],
        )

    except Exception as e:
        conn.rollback()
        msg = f"Ingestion failed for '{biome_slug}': {e}"
        summary["errors"].append(msg)
        logger.error(msg)

    finally:
        cur.close()

    return summary


def ingest_all_payloads(conn, payloads: list) -> list:
    """
    Ingest multiple biome payloads.

    Args:
        conn: psycopg2 connection
        payloads: list of dicts, each with "biome_slug" and "lessons"

    Returns:
        list of summary dicts
    """
    results = []
    for payload in payloads:
        result = ingest_lessons(conn, payload)
        results.append(result)
    return results
