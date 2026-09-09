"""
CineMatch — Smart Movie Recommendation System
Glassmorphism UI | Mood-Based NLP | SQL Server | Netflix-style Preview Pages
Run: streamlit run app.py
"""

import streamlit as st
import random
import pyodbc
import os
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════
# DATA LAYER
# ═══════════════════════════════════════════════════════════════


DB_CONN_STR = (
    f"DRIVER={{SQL Server}};"
    f"SERVER={os.getenv('DB_SERVER', 'localhost')};"
    f"DATABASE=MovieDB;"
    f"Trusted_Connection=yes;"
)

@st.cache_resource
def get_connection():
    """Open and return a cached pyodbc connection."""
    # FIX 3 — autocommit=True prevents transaction lock issues
    return pyodbc.connect(DB_CONN_STR, autocommit=True)


# ── Data models ───────────────────────────────────────────────

@dataclass
class Movie:
    id: int
    title: str
    genre: list[str]
    language: str
    rating: float
    platform: str
    description: str
    poster_url: str
    year: int
    trailer_url: str = ""   # ✅ STEP 3 — stored from DB, defaults to empty string


@dataclass
class CastMember:
    actor_name: str
    actor_image: str


@dataclass
class MovieImage:
    image_url: str


# ── DDL for extended tables ───────────────────────────────────

CREATE_CAST_SQL = """
IF NOT EXISTS (
    SELECT * FROM sysobjects WHERE name='cast' AND xtype='U'
)
CREATE TABLE [cast] (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    movie_id    INT NOT NULL,
    actor_name  NVARCHAR(255) NOT NULL,
    actor_image NVARCHAR(500) NOT NULL DEFAULT '',
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);
"""

CREATE_IMAGES_SQL = """
IF NOT EXISTS (
    SELECT * FROM sysobjects WHERE name='movie_images' AND xtype='U'
)
CREATE TABLE movie_images (
    id        INT IDENTITY(1,1) PRIMARY KEY,
    movie_id  INT NOT NULL,
    image_url NVARCHAR(500) NOT NULL,
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);
"""


def ensure_extra_tables() -> None:
    """Create [cast] and movie_images tables if they don't exist yet."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(CREATE_CAST_SQL)
        cursor.execute(CREATE_IMAGES_SQL)
        conn.commit()
    except Exception as e:
        print(f"[warn] ensure_extra_tables: {e}")


# ── Query functions ───────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_movies_from_db() -> list[Movie]:
    """Fetch all movies from SQL Server. Cached for 30 minutes."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, genre, language, rating, "
            "platform, description, poster_url, year, trailer_url FROM movies"
        )
        movies: list[Movie] = []
        for row in cursor.fetchall():
            movies.append(Movie(
                id=row.id,
                title=row.title,
                genre=[g.strip() for g in row.genre.split(",")],
                language=row.language,
                rating=float(row.rating),
                platform=row.platform,
                description=row.description,
                poster_url=row.poster_url,
                year=int(row.year),
                trailer_url=row.trailer_url or "",   # ✅ STEP 5
            ))
        return movies
    except Exception as e:
        print(f"[error] get_movies_from_db: {e}")
        return []


@st.cache_data(ttl=3600)
def get_cast_by_movie(movie_id: int) -> list[CastMember]:
    """Return cast members for a given movie_id. Cached for 1 hour."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT actor_name, actor_image FROM [cast] WHERE movie_id = ?",
            movie_id,
        )
        return [
            CastMember(actor_name=r.actor_name, actor_image=r.actor_image)
            for r in cursor.fetchall()
        ]
    except Exception as e:
        print(f"[warn] get_cast_by_movie(movie_id={movie_id}): {e}")
        return []


@st.cache_data(ttl=3600)
def get_images_by_movie(movie_id: int) -> list[MovieImage]:
    """Return gallery images for a given movie_id. Cached for 1 hour."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT image_url FROM movie_images WHERE movie_id = ?",
            movie_id,
        )
        return [MovieImage(image_url=r.image_url) for r in cursor.fetchall()]
    except Exception as e:
        print(f"[warn] get_images_by_movie(movie_id={movie_id}): {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════

MOOD_KEYWORD_MAP: dict[str, list[str]] = {
    "sad":        ["sad", "crying", "heartbroken", "depressed", "down", "unhappy", "upset", "lonely"],
    "happy":      ["happy", "joyful", "great", "wonderful", "amazing", "cheerful", "good"],
    "excited":    ["excited", "hyped", "thrilled", "pumped", "stoked", "wow"],
    "bored":      ["bored", "nothing", "dull", "sleepy", "tired", "blank"],
    "romantic":   ["love", "romantic", "crush", "date", "heart", "relationship"],
    "tense":      ["anxious", "nervous", "tense", "scared", "fear", "worried"],
    "motivated":  ["motivated", "inspired", "goal", "hustle", "grind", "push"],
    "curious":    ["curious", "wonder", "weird", "strange", "mystery", "explore"],
    "nostalgic":  ["nostalgic", "miss", "memory", "remember", "childhood", "old"],
    "mind-blown": ["mind", "complex", "deep", "layers", "twist", "philosophy"],
}

MOOD_TO_GENRE: dict[str, list[str]] = {
    "sad":        ["Comedy", "Drama", "Musical"],
    "happy":      ["Comedy", "Romance", "Adventure"],
    "excited":    ["Action", "Thriller", "Sci-Fi"],
    "bored":      ["Action", "Thriller", "Sci-Fi", "Horror"],
    "romantic":   ["Romance", "Drama", "Musical"],
    "tense":      ["Thriller", "Horror", "Drama"],
    "motivated":  ["Drama", "Sports", "Action"],
    "curious":    ["Sci-Fi", "Thriller", "Drama"],
    "nostalgic":  ["Drama", "Comedy", "Romance"],
    "mind-blown": ["Sci-Fi", "Thriller", "Drama"],
}

MOOD_DESC_KEYWORDS: dict[str, list[str]] = {
    "sad":        ["loss", "grief", "heartbreak", "tragedy", "alone", "death", "sorrow"],
    "happy":      ["friendship", "joy", "celebration", "fun", "laughter", "family", "wedding"],
    "excited":    ["battle", "war", "chase", "explosion", "hero", "mission", "fight"],
    "bored":      ["adventure", "quest", "mystery", "heist", "survival", "journey"],
    "romantic":   ["love", "romance", "couple", "kiss", "passion", "relationship", "heart"],
    "tense":      ["murder", "crime", "killer", "danger", "threat", "conspiracy", "dark"],
    "motivated":  ["success", "dream", "overcome", "rise", "ambition", "champion", "inspire"],
    "curious":    ["mystery", "secret", "discover", "unknown", "strange", "explore", "alien"],
    "nostalgic":  ["past", "memory", "childhood", "old", "reunion", "retro", "decade"],
    "mind-blown": ["twist", "illusion", "reality", "multiverse", "time", "dimension", "mind"],
}

INTEREST_KEYWORD_MAP: dict[str, str] = {
    "action": "Action", "comedy": "Comedy", "rom": "Romance",
    "love": "Romance", "thrill": "Thriller", "drama": "Drama",
    "horror": "Horror", "sci": "Sci-Fi", "sport": "Sports",
    "adventure": "Adventure", "musical": "Musical",
    "fantasy": "Fantasy", "history": "History", "anim": "Animation",
}


def detect_mood(text: str) -> list[str]:
    """Map free-text to one or more mood buckets. Falls back to ['happy']."""
    text_lower = text.lower()
    detected = [
        mood for mood, keywords in MOOD_KEYWORD_MAP.items()
        if any(kw in text_lower for kw in keywords)
    ]
    return detected or ["happy"]


def _parse_interest_genres(interest_text: str) -> list[str]:
    """Parse free-text interest into known genre strings."""
    lower = interest_text.lower()
    return [
        genre for kw, genre in INTEREST_KEYWORD_MAP.items()
        if kw in lower
    ]


def compute_score(movie: Movie, moods: list[str], interest_genres: list[str]) -> float:
    """
    Weighted scoring — normalised to 0-100:
      Mood → Genre match           = up to 60 pts  (primary signal)
      Mood keyword in description  = up to 20 pts  (context depth)
      Rating boost                 = up to 20 pts  (quality signal)
      Interest genre bonus         = up to +10 pts (light user hint)
      Baseline                     = 5 pts         (ensures all compete)
    """
    genre_score:  float = 5.0
    desc_score:   float = 0.0
    rating_score: float = 0.0

    # ── Mood → Genre (max 60 pts) ─────────────────────────────
    mood_genres: list[str] = []
    for m in moods:
        mood_genres.extend(MOOD_TO_GENRE.get(m, []))

    matched_genres: set[str] = set()
    for mg in mood_genres:
        if mg in movie.genre and mg not in matched_genres:
            genre_score += 20
            matched_genres.add(mg)
    genre_score = min(genre_score, 60)

    # ── Mood keywords in description (max 20 pts) ─────────────
    desc_lower = movie.description.lower()
    for m in moods:
        if any(kw in desc_lower for kw in MOOD_DESC_KEYWORDS.get(m, [])):
            desc_score += 10
    desc_score = min(desc_score, 20)

    # ── Rating boost (max 20 pts) ─────────────────────────────
    rating_score = (movie.rating / 10.0) * 20.0

    # ── Interest genre bonus (max 10 pts, non-dominant) ───────
    interest_bonus = min(
        sum(5 for ig in interest_genres if ig in movie.genre), 10
    )

    raw = genre_score + desc_score + rating_score + interest_bonus
    # Normalise: theoretical max raw ≈ 110 (60+20+20+10)
    normalised = min((raw / 110.0) * 100.0, 100.0)
    normalised += random.uniform(0, 0.3)   # reduced jitter for better consistency

    return round(min(normalised, 100.0), 1)


def recommend(
    mood_text: str,
    interest_text: str,
    language_filter: str,
    genre_filter: list[str],
    platform_filter: list[str],
    rating_min: float,
    year_range: tuple[int, int],
    all_movies: list[Movie],
    top_n: int = 12,
) -> list[tuple[Movie, float]]:
    """
    Apply hard filters then return top_n (movie, score) tuples ranked by score.
    Falls back to global top-rated movies when all filters yield zero results.
    """
    moods           = detect_mood(mood_text)
    interest_genres = _parse_interest_genres(interest_text)

    results: list[tuple[Movie, float]] = []
    for movie in all_movies:
        # Hard filters — applied before scoring
        if language_filter != "All" and movie.language != language_filter:
            continue
        # FIX 1 — case-insensitive platform comparison
        if platform_filter and movie.platform.lower() not in [p.lower() for p in platform_filter]:
            continue
        if movie.rating < rating_min:
            continue
        if not (year_range[0] <= movie.year <= year_range[1]):
            continue
        # Genre filter (no case change needed — genres are title-cased consistently)
        if genre_filter and not any(g in movie.genre for g in genre_filter):
            continue

        results.append((movie, compute_score(movie, moods, interest_genres)))

    results.sort(key=lambda x: x[1], reverse=True)

    # Fallback: when zero movies survive the filters
    if not results:
        fallback = sorted(all_movies, key=lambda m: m.rating, reverse=True)[:top_n]
        return [(m, compute_score(m, moods, interest_genres)) for m in fallback]

    return results[:top_n]


# ═══════════════════════════════════════════════════════════════
# CSS — Glassmorphism Theme
# ═══════════════════════════════════════════════════════════════

GLASS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Root design tokens ── */
:root {
    --bg1:          #0d0d1a;
    --bg2:          #12122a;
    --accent:       #e63d72;
    --accent2:      #7c5ce6;
    --gold:         #f5a623;
    --glass-bg:     rgba(255,255,255,0.05);
    --glass-border: rgba(255,255,255,0.10);
    --glass-shadow: 0 8px 32px rgba(0,0,0,0.45);
    --text:         #f0eaff;
    --muted:        rgba(240,234,255,0.55);
    --radius:       18px;
    --card-h:       520px;
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}
.stApp {
    background: linear-gradient(135deg, var(--bg1) 0%, var(--bg2) 50%, #1a0d2e 100%);
    min-height: 100vh;
}

/* ── Ambient background mesh ── */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 60% 40% at 20% 20%, rgba(124,92,230,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 50% 35% at 80% 70%, rgba(230,61,114,0.14) 0%, transparent 55%),
        radial-gradient(ellipse 40% 30% at 55% 45%, rgba(0,180,255,0.08) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 3rem 1rem 2rem;
    position: relative;
}
.hero h1 {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(2.4rem, 5vw, 4rem);
    background: linear-gradient(135deg, #ffffff 30%, var(--accent) 65%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
    margin: 0 0 0.5rem;
}
.hero p {
    color: var(--muted);
    font-size: 1.1rem;
    font-weight: 300;
    letter-spacing: 0.03em;
}

/* ── Glass panel ── */
.glass-panel {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: var(--radius);
    box-shadow: var(--glass-shadow);
    padding: 2rem;
    margin-bottom: 1.5rem;
}

/* ── Section label ── */
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.5rem;
}

/* ── Filter panel ── */
.filter-panel {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: var(--radius);
    box-shadow: var(--glass-shadow);
    padding: 1.5rem;
    margin: 1.5rem 0;
}
.filter-panel h3 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem;
    margin: 0 0 1rem;
    color: var(--text);
}

/* ── Movie card ── */
.movie-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: var(--radius);
    box-shadow: var(--glass-shadow);
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
    height: var(--card-h);
    position: relative;
    cursor: pointer;
}
.movie-card:hover {
    transform: translateY(-6px) scale(1.01);
    box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 0 1px var(--accent);
    border-color: rgba(230,61,114,0.45);
}
.movie-poster {
    width: 100%;
    height: 310px;
    object-fit: cover;
    display: block;
}
.movie-poster-fallback {
    width: 100%;
    height: 310px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3.5rem;
    background: linear-gradient(135deg, rgba(124,92,230,0.3), rgba(230,61,114,0.3));
}
.card-body { padding: 1rem; }
.card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    font-weight: 400;
    margin: 0 0 0.35rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.card-meta {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
}
.chip {
    font-size: 0.68rem;
    font-weight: 500;
    padding: 2px 9px;
    border-radius: 30px;
    letter-spacing: 0.04em;
    border: 1px solid;
}
.chip-genre { color:#a78bfa; border-color:rgba(167,139,250,0.35); background:rgba(167,139,250,0.10); }
.chip-lang  { color:#67e8f9; border-color:rgba(103,232,249,0.35); background:rgba(103,232,249,0.10); }
.chip-plat  { color:#fb923c; border-color:rgba(251,146,60,0.35);  background:rgba(251,146,60,0.10); }
.rating-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.82rem;
    color: var(--gold);
    font-weight: 600;
    margin-bottom: 0.45rem;
}
.card-desc {
    font-size: 0.78rem;
    color: var(--muted);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── IMPROVEMENT 2 — Mood match tag on card ── */
.mood-match-tag {
    font-size: 0.7rem;
    color: var(--accent);
    margin-top: 4px;
    font-weight: 500;
}

/* ── Score badge ── */
.score-badge {
    position: absolute;
    top: 12px; right: 12px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 50%;
    width: 46px; height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 700;
    color: #fff;
    box-shadow: 0 4px 14px rgba(230,61,114,0.5);
    z-index: 5;
}

/* ── CTA / action buttons ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.7rem 2.2rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    box-shadow: 0 4px 20px rgba(230,61,114,0.45) !important;
    transition: all 0.25s ease !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(230,61,114,0.6) !important;
}

/* ── Mood detection tags ── */
.mood-display { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
.mood-tag {
    font-size: 0.75rem;
    padding: 4px 12px;
    background: rgba(230,61,114,0.18);
    border: 1px solid rgba(230,61,114,0.4);
    border-radius: 20px;
    color: #fca5a5;
    font-weight: 500;
}

/* ── Decorative divider ── */
.fancy-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
    margin: 1.5rem 0;
}

/* ── Stats row ── */
.stats-row {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin: 0.5rem 0 1.5rem;
}
.stat-pill {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 40px;
    padding: 0.4rem 1.2rem;
    font-size: 0.8rem;
    color: var(--muted);
    backdrop-filter: blur(10px);
}
.stat-pill span { color: var(--text); font-weight: 600; }

/* ── Empty / fallback state ── */
.empty-state { text-align: center; padding: 4rem 2rem; color: var(--muted); }
.empty-state .icon  { font-size: 4rem; margin-bottom: 1rem; }
.empty-state h3     { font-family: 'DM Serif Display', serif; color: var(--text); margin-bottom: 0.5rem; }

/* ── Text area / input overrides ── */
.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: rgba(230,61,114,0.5) !important;
    box-shadow: 0 0 0 3px rgba(230,61,114,0.15) !important;
}

/* ══════════════════════════════════════════════
   PREVIEW PAGE — Netflix-style detail view
══════════════════════════════════════════════ */

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}
.preview-animate { animation: slideUp 0.4s ease forwards; }

.preview-hero {
    position: relative;
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7);
}
.preview-hero-img {
    width: 100%; height: 420px;
    object-fit: cover; display: block;
    filter: brightness(0.5);
}
.preview-hero-fallback {
    width: 100%; height: 420px;
    display: flex; align-items: center; justify-content: center;
    font-size: 6rem;
    background: linear-gradient(135deg, rgba(124,92,230,0.4), rgba(230,61,114,0.4));
}
.preview-hero-overlay {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 2.5rem 2rem 2rem;
    background: linear-gradient(to top, rgba(13,13,26,0.98) 0%, transparent 100%);
}
.preview-title {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(2rem, 4vw, 3.2rem);
    line-height: 1.1; margin: 0 0 0.5rem;
    background: linear-gradient(135deg, #ffffff, var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.preview-sub {
    color: var(--muted); font-size: 0.9rem;
    display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;
}

.preview-info-block {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(20px);
    border-radius: var(--radius);
    padding: 1.8rem;
    margin-bottom: 1.5rem;
}
.preview-section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem; margin: 0 0 1rem;
    color: var(--text);
    border-bottom: 1px solid var(--glass-border);
    padding-bottom: 0.5rem;
}
.preview-description { font-size: 1rem; line-height: 1.8; color: var(--muted); }
.preview-rating-big  { font-size: 2.8rem; font-weight: 700; color: var(--gold); line-height: 1; }
.preview-rating-sub  { font-size: 0.8rem; color: var(--muted); margin-top: 0.2rem; }

.cast-grid {
    display: flex;
    gap: 1.2rem;
    flex-wrap: wrap;
}
.cast-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1rem;
    text-align: center;
    width: 140px;
    transition: transform 0.25s ease, border-color 0.25s ease;
    backdrop-filter: blur(10px);
}
.cast-card:hover {
    transform: translateY(-6px) scale(1.03);
    border-color: rgba(230,61,114,0.5);
}
.cast-img {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    object-fit: cover;
    display: block;
    margin: 0 auto 0.6rem;
    border: 2px solid var(--glass-border);
    transition: transform 0.3s ease;
}
.cast-card:hover .cast-img {
    transform: scale(1.08);
}
.cast-img-fallback {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.8rem;
    background: linear-gradient(135deg, rgba(124,92,230,0.3), rgba(230,61,114,0.3));
    margin: 0 auto 0.6rem;
    border: 2px solid var(--glass-border);
}
.cast-name {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text);
    line-height: 1.3;
}

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
}
.gallery-img {
    width: 100%; height: 160px; object-fit: cover;
    border-radius: 12px; display: block;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    border: 1px solid var(--glass-border);
}
.gallery-img:hover { transform: scale(1.03); box-shadow: 0 8px 24px rgba(0,0,0,0.5); }

.stream-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px; padding: 0.5rem 1.2rem;
    font-size: 0.85rem; font-weight: 600; color: #fff; letter-spacing: 0.03em;
}
</style>
"""


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS — FILTERS
# ═══════════════════════════════════════════════════════════════

def render_inline_filters(all_movies: list[Movie]) -> tuple[str, list[str], list[str], float, tuple[int, int]]:
    """
    Render inline filter panel and return filter values.
    Returns: (language, genres, platforms, rating_min, year_range)
    """
    st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
    st.markdown('<h3 style="margin-top:0;">🎛️ Filters</h3>', unsafe_allow_html=True)

    f1, f2, f3, f4, f5 = st.columns(5, gap="small")

    with f1:
        language_filter = st.selectbox(
            "🌐 Language",
            ["All", "Telugu", "English", "Hindi", "Tamil", "Korean", "Malayalam"],
            index=0,
            label_visibility="collapsed",
        )

    with f2:
        genre_filter = st.multiselect(
            "🎭 Genres",
            ["Action", "Comedy", "Romance", "Thriller", "Drama",
             "Horror", "Sci-Fi", "Sports", "Adventure", "Musical",
             "Fantasy", "History", "Biography", "Music", "Animation"],
            label_visibility="collapsed",
        )

    with f3:
        all_platforms = (
            sorted({m.platform for m in all_movies})
            if all_movies
            else ["Netflix", "Prime Video", "Hotstar", "Zee5"]
        )
        platform_filter = st.multiselect(
            "📺 Platform",
            all_platforms,
            label_visibility="collapsed",
        )

    with f4:
        rating_min = st.slider(
            "⭐ Rating",
            0.0, 10.0, 0.0, 0.5,
            label_visibility="collapsed",
        )

    with f5:
        all_years = [m.year for m in all_movies] if all_movies else [2000, 2025]
        min_yr, max_yr = min(all_years), max(all_years)
        year_range = st.slider(
            "📅 Year",
            min_value=min_yr, max_value=max_yr,
            value=(min_yr, max_yr),
            label_visibility="collapsed",
        )

    st.markdown('</div>', unsafe_allow_html=True)

    return language_filter, genre_filter, platform_filter, rating_min, year_range


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS — MAIN PAGE
# ═══════════════════════════════════════════════════════════════

def render_hero() -> None:
    st.markdown("""
    <div class="hero">
        <h1>🎬 CineMatch</h1>
        <p>Tell us your mood — we'll find your perfect watch tonight.</p>
    </div>
    """, unsafe_allow_html=True)


def render_movie_card(movie: Movie, score: float) -> str:
    """Return the HTML string for a single glassmorphism movie card."""
    genres_html = "".join(
        f'<span class="chip chip-genre">{g}</span>' for g in movie.genre[:2]
    )
    stars = "★" * int(round(movie.rating / 2))
    return f"""
    <div class="movie-card">
        <div class="score-badge">{score:.0f}</div>
        <img class="movie-poster"
             src="{movie.poster_url}"
             onerror="this.style.display='none';this.nextSibling.style.display='flex';"
             alt="{movie.title}" />
        <div class="movie-poster-fallback" style="display:none;">🎞️</div>
        <div class="card-body">
            <div class="card-title" title="{movie.title}">
                {movie.title}
                <small style="color:var(--muted);font-size:0.75rem;">({movie.year})</small>
            </div>
            <div class="card-meta">
                {genres_html}
                <span class="chip chip-lang">{movie.language}</span>
                <span class="chip chip-plat">{movie.platform}</span>
            </div>
            <div class="rating-row">
                <span>{stars}</span>
                <span>{movie.rating}/10</span>
            </div>
            <div class="card-desc">{movie.description}</div>
            <!-- IMPROVEMENT 2 — Mood match label -->
            <div class="mood-match-tag">🔥 Matches your mood</div>
        </div>
    </div>
    """


def render_results_grid(results: list[tuple[Movie, float]], sort_by: str = "Best Match") -> None:
    """Render the recommendation grid with stats and clickable View Details buttons."""
    if not results:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🎭</div>
            <h3>No matches found</h3>
            <p>Try adjusting your mood, interests, or filters.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # OPTIONAL — Sorting
    if sort_by == "Rating":
        results = sorted(results, key=lambda x: x[0].rating, reverse=True)

    avg_score = sum(s for _, s in results) / len(results)
    platforms = {m.platform for m, _ in results}
    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-pill"><span>{len(results)}</span> movies found</div>
        <div class="stat-pill">Avg match <span>{avg_score:.0f}%</span></div>
        <div class="stat-pill"><span>{len(platforms)}</span> platforms</div>
    </div>
    """, unsafe_allow_html=True)

    cols_per_row = 3
    for row_start in range(0, len(results), cols_per_row):
        batch = results[row_start: row_start + cols_per_row]
        cols  = st.columns(cols_per_row)
        for col, (movie, score) in zip(cols, batch):
            with col:
                st.markdown(render_movie_card(movie, score), unsafe_allow_html=True)
                if st.button("▶  View Details", key=f"view_{movie.id}"):
                    st.session_state["selected_movie"] = movie
                    st.session_state["page"] = "preview"
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS — PREVIEW PAGE
# ═══════════════════════════════════════════════════════════════

def render_cast_section(movie: Movie) -> None:
    """Render the cast grid."""
    cast = get_cast_by_movie(movie.id)
    st.markdown('<div class="preview-info-block">', unsafe_allow_html=True)
    st.markdown('<div class="preview-section-title">🎭 Cast</div>', unsafe_allow_html=True)

    if not cast:
        st.markdown(
            '<p style="color:var(--muted);font-size:0.85rem;">'
            'Cast information coming soon. Add rows to the '
            '<code>[cast]</code> table in SQL Server.</p>',
            unsafe_allow_html=True,
        )
    else:
        cards_html = ""
        for member in cast:
            if member.actor_image:
                img_tag = (
                    f'<img class="cast-img" src="{member.actor_image}" '
                    f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\';" '
                    f'alt="{member.actor_name}" />'
                    f'<div class="cast-img-fallback" style="display:none;">🎬</div>'
                )
            else:
                img_tag = '<div class="cast-img-fallback">🎬</div>'
            cards_html += (
                f'<div class="cast-card">'
                f'{img_tag}'
                f'<div class="cast-name">{member.actor_name}</div>'
                f'</div>'
            )
        st.markdown(f'<div class="cast-grid">{cards_html}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_gallery_section(movie: Movie) -> None:
    """Render the image gallery."""
    images = get_images_by_movie(movie.id)
    st.markdown('<div class="preview-info-block">', unsafe_allow_html=True)
    st.markdown('<div class="preview-section-title">🖼️ Image Gallery</div>', unsafe_allow_html=True)

    if not images:
        st.markdown(
            '<p style="color:var(--muted);font-size:0.85rem;">'
            'Gallery images coming soon. Add rows to the '
            '<code>movie_images</code> table in SQL Server.</p>',
            unsafe_allow_html=True,
        )
    else:
        imgs_html = "".join(
            f'<img class="gallery-img" src="{img.image_url}" alt="Scene" />'
            for img in images
        )
        st.markdown(f'<div class="gallery-grid">{imgs_html}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_preview_page(movie: Movie) -> None:
    """Full Netflix-style detail page rendered when a movie card is clicked."""
    st.markdown('<div class="preview-animate">', unsafe_allow_html=True)

    if st.button("← Back to Results", key="back_btn"):
        st.session_state["page"] = "main"
        st.session_state.pop("selected_movie", None)
        st.rerun()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    genres_chips = "".join(
        f'<span class="chip chip-genre" style="font-size:0.8rem;">{g}</span> '
        for g in movie.genre
    )
    stars_big = (
        "★" * int(round(movie.rating / 2))
        + "☆" * (5 - int(round(movie.rating / 2)))
    )

    st.markdown(f"""
    <div class="preview-hero">
        <img class="preview-hero-img"
             src="{movie.poster_url}"
             onerror="this.style.display='none';this.nextSibling.style.display='flex';"
             alt="{movie.title}" />
        <div class="preview-hero-fallback" style="display:none;">🎞️</div>
        <div class="preview-hero-overlay">
            <div class="preview-title">{movie.title}</div>
            <div class="preview-sub">
                <span>{movie.year}</span>
                <span>·</span>
                <span>{movie.language}</span>
                <span>·</span>
                <span style="color:var(--gold);">{stars_big}</span>
                <span style="color:var(--gold);font-weight:700;">{movie.rating}/10</span>
                <span>·</span>
                <span class="stream-badge">▶ {movie.platform}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown(f"""
        <div class="preview-info-block">
            <div class="preview-section-title">📖 Synopsis</div>
            <div class="preview-description">{movie.description}</div>
        </div>
        """, unsafe_allow_html=True)

        render_cast_section(movie)
        render_gallery_section(movie)

    with right:
        st.markdown(f"""
        <div class="preview-info-block">
            <div class="preview-section-title">⭐ Rating</div>
            <div class="preview-rating-big">{movie.rating}</div>
            <div class="preview-rating-sub">out of 10</div>
            <div style="margin-top:0.8rem;color:var(--gold);font-size:1.3rem;">{stars_big}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="preview-info-block">
            <div class="preview-section-title">🗂️ Details</div>
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <tr>
                    <td style="color:var(--muted);padding:0.35rem 0;width:40%;">Language</td>
                    <td style="font-weight:500;">{movie.language}</td>
                </tr>
                <tr>
                    <td style="color:var(--muted);padding:0.35rem 0;">Year</td>
                    <td style="font-weight:500;">{movie.year}</td>
                </tr>
                <tr>
                    <td style="color:var(--muted);padding:0.35rem 0;">Platform</td>
                    <td><span class="chip chip-plat" style="font-size:0.78rem;">{movie.platform}</span></td>
                </tr>
                <tr>
                    <td style="color:var(--muted);padding:0.35rem 0;vertical-align:top;">Genres</td>
                    <td style="padding-top:0.35rem;">{genres_chips}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="preview-info-block" style="text-align:center;">
            <div style="font-size:0.75rem;color:var(--muted);margin-bottom:0.8rem;
                        letter-spacing:0.08em;text-transform:uppercase;">
                Available on
            </div>
            <div class="stream-badge"
                 style="justify-content:center;width:100%;font-size:1rem;padding:0.8rem;">
                ▶ &nbsp; Watch on {movie.platform}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # STEP 6 — Use stored trailer URL if available, else fallback
        if movie.trailer_url:
            st.video(movie.trailer_url)
        else:
            st.warning("Trailer not available")

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="CineMatch – Smart Movie Recommender",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(GLASS_CSS, unsafe_allow_html=True)

    # ── Session state defaults ──────────────────────────────────
    if "page" not in st.session_state:
        st.session_state["page"] = "main"
    if "has_results" not in st.session_state:
        st.session_state["has_results"] = False

    # ── Load movie catalogue once per session ───────────────────
    if "all_movies" not in st.session_state:
        try:
            st.session_state["all_movies"] = get_movies_from_db()
            ensure_extra_tables()
        except Exception as e:
            st.session_state["all_movies"] = []
            st.error(
                f"🔴 Database Connection Failed\n\n"
                f"Error: {str(e)}\n\n"
                f"**Troubleshooting:**\n"
                f"- Check DB_SERVER environment variable is set\n"
                f"- Verify SQL Server is running\n"
                f"- Ensure `MovieDB` database exists\n"
                f"- Try refreshing the page",
                icon="❌"
            )

    all_movies: list[Movie] = st.session_state["all_movies"]

    # ══════════════════════════════════════════════
    # PAGE ROUTER
    # ══════════════════════════════════════════════
    if st.session_state["page"] == "preview" and st.session_state.get("selected_movie"):
        render_preview_page(st.session_state["selected_movie"])
        return

    # ══════════════════════════════════════════════
    # MAIN PAGE
    # ══════════════════════════════════════════════
    render_hero()

    # ── Inline filters (replaces sidebar) ──────────────────────
    language_filter, genre_filter, platform_filter, rating_min, year_range = (
        render_inline_filters(all_movies)
    )

    # ── Input panel ────────────────────────────────────────────

    if "combined_input" not in st.session_state:
        st.session_state["combined_input"] = ""

    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)

    st.markdown(
        '<div class="section-label">🧠 Describe your mood & what you want to watch</div>',
        unsafe_allow_html=True,
    )

    suggestions = [
        "feeling sad, want emotional movie",
        "bored, need action thriller",
        "happy mood, comedy movies",
        "romantic vibe, love stories",
        "mind blowing sci-fi",
    ]

    if not st.session_state["combined_input"]:
        st.markdown("### 💡 Try this:")
        cols = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            if cols[i].button(sug, key=f"sug_{i}"):
                st.session_state["combined_input"] = sug
                st.rerun()

    user_input = st.text_area(
        label="combined_input",
        value=st.session_state["combined_input"],
        placeholder='e.g. "feeling bored, want sci-fi action or something funny..."',
        height=130,
        label_visibility="collapsed",
    )

    st.session_state["combined_input"] = user_input

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Connect input to both mood + interest pipelines ────────
    mood_text     = user_input
    interest_text = user_input

    # ── Live mood detection tags ────────────────────────────────
    if mood_text.strip():
        detected  = detect_mood(mood_text)
        tags_html = "".join(f'<span class="mood-tag">✨ {m}</span>' for m in detected)
        st.markdown(f'<div class="mood-display">{tags_html}</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Sort + CTA row ──────────────────────────────────────────
    btn_col, sort_col, _ = st.columns([1, 1, 2])
    with btn_col:
        go = st.button("🎬  Get Recommendations (⏎)", key="go_btn", use_container_width=True)
    with sort_col:
        # OPTIONAL — Sort selector
        sort_by = st.selectbox(
            "Sort by",
            ["Best Match", "Rating"],
            label_visibility="collapsed",
        )

    # ── Results section ─────────────────────────────────────────
    if go or st.session_state.get("has_results"):
        if go:
            # IMPROVEMENT 1 — Block empty submissions
            if not mood_text.strip():
                st.warning("⚠️ Please describe your mood first")
                return
            st.session_state["has_results"] = True

        mood      = mood_text
        inter     = interest_text
        lang      = language_filter
        genres    = genre_filter
        platforms = platform_filter
        r_min     = rating_min
        y_range   = year_range

        with st.spinner("Finding your perfect movies…"):
            results = recommend(
                mood, inter, lang, genres, platforms,
                r_min, y_range, all_movies,
            )

        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

        # Active-filter summary line
        notes: list[str] = []
        if lang != "All":  notes.append(f'<b style="color:var(--text)">{lang}</b>')
        if genres:         notes.append(f'genres: <b style="color:var(--text)">{", ".join(genres)}</b>')
        if platforms:      notes.append(f'platform: <b style="color:var(--text)">{", ".join(platforms)}</b>')
        if r_min > 0:      notes.append(f'rating ≥ <b style="color:var(--text)">{r_min}</b>')

        note_str = " · ".join(notes)
        st.markdown(
            f'<p style="color:var(--muted);font-size:0.88rem;margin-bottom:1rem;">'
            f'Showing top <b style="color:var(--text)">{len(results)}</b> recommendations'
            + (f" · {note_str}" if note_str else "")
            + "</p>",
            unsafe_allow_html=True,
        )
        render_results_grid(results, sort_by=sort_by)

        # Footer tips
        st.markdown("""
        <div style="margin-top:3rem; padding-top:2rem; border-top:1px solid var(--glass-border); 
                    text-align:center; font-size:0.75rem; color:var(--muted);">
            💡 <b>Tip:</b> Click any movie card for full details, cast, and gallery. Adjust filters for different results.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state" style="padding:3rem 0 2rem;">
            <div class="icon">🍿</div>
            <h3>What are you watching tonight?</h3>
            <p>Describe your mood above and hit <b>Get Recommendations</b>. Try:</p>
            <p style="font-size: 0.9rem; margin-top: 1rem; color: rgba(240,234,255,0.7);">
                "sad but want something uplifting" · "bored, gimme action" · "romantic mood" · "sci-fi thriller"
            </p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()