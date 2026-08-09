"""
Free local relevance scorer — no API, no cost.

Builds a weighted keyword profile from the user's uploaded CV, then scores each
job by how much of that profile appears in the job title + description.
"""

import re
from collections import Counter
from typing import List, Dict

# Broad multi-domain vocabulary. Only terms actually found in the CV are used,
# so the scorer adapts to whoever uploads.
VOCABULARY = {
    # ── Roles / seniority
    "role": [
        "project manager", "program manager", "product manager", "delivery manager",
        "engineering manager", "team lead", "technical lead", "scrum master",
        "software engineer", "data scientist", "data engineer", "data analyst",
        "machine learning engineer", "ml engineer", "ai engineer", "nlp engineer",
        "computer vision engineer", "devops engineer", "cloud engineer", "sre",
        "business analyst", "qa engineer", "test engineer", "solutions architect",
        "researcher", "research scientist", "lecturer", "professor", "consultant",
        "designer", "ux designer", "accountant", "marketing manager", "sales manager",
        "hr manager", "recruiter", "operations manager", "financial analyst",
    ],
    # ── AI / ML / Data
    "ai": [
        "machine learning", "deep learning", "artificial intelligence", "neural network",
        "computer vision", "object detection", "segmentation", "nlp",
        "natural language processing", "llm", "large language model", "generative ai",
        "conversational ai", "chatbot", "voice bot", "speech recognition", "asr", "nlu",
        "tts", "text to speech", "transformer", "rag", "fine-tuning", "prompt engineering",
        "yolo", "cnn", "rnn", "reinforcement learning", "mlops", "model deployment",
    ],
    # ── Tech stack
    "tech": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "scala",
        "php", "ruby", "swift", "kotlin", "r", "matlab", "sql", "nosql",
        "pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "pandas", "numpy",
        "spark", "hadoop", "airflow", "kafka", "databricks", "snowflake",
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring",
        "docker", "kubernetes", "terraform", "jenkins", "ci/cd", "git",
        "aws", "azure", "gcp", "google cloud", "cuda", "gpu", "linux",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "power bi", "tableau", "excel", "sap", "salesforce",
    ],
    # ── Management / process
    "process": [
        "agile", "scrum", "kanban", "waterfall", "jira", "confluence", "sprint",
        "backlog", "roadmap", "stakeholder", "kpi", "okr", "budget", "risk management",
        "cross-functional", "requirements", "uat", "sdlc", "prince2", "pmp",
        "vendor management", "resource planning", "change management",
    ],
    # ── Domain / soft
    "domain": [
        "healthcare", "fintech", "banking", "insurance", "e-commerce", "retail",
        "telecom", "automotive", "manufacturing", "logistics", "education",
        "oil and gas", "energy", "cybersecurity", "saas", "enterprise",
        "leadership", "mentoring", "curriculum", "teaching", "research", "publication",
    ],
}

# Base weight per category — roles matter most, domain least.
CATEGORY_WEIGHT = {
    "role": 10,
    "ai": 7,
    "tech": 6,
    "process": 5,
    "domain": 3,
}

ALL_TERMS = {term: cat for cat, terms in VOCABULARY.items() for term in terms}


def _compile(term: str) -> "re.Pattern":
    """
    Word-boundary matcher. Without this, short terms like "r", "go" or "ai"
    match inside unrelated words and inflate every score.
    """
    escaped = re.escape(term)
    left = r"(?<![A-Za-z0-9])"
    # Terms ending in a symbol (c++, node.js, ci/cd) can't use a trailing \b
    right = r"(?![A-Za-z0-9])" if term[-1].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


TERM_RE = {term: _compile(term) for term in ALL_TERMS}


def build_profile(cv_text: str) -> Dict[str, int]:
    """
    Returns {term: weight} for terms present in the CV.
    Weight = category base × frequency boost.
    """
    text = cv_text or ""
    if not text:
        return {}

    profile: Dict[str, int] = {}
    for term, cat in ALL_TERMS.items():
        count = len(TERM_RE[term].findall(text))
        if count == 0:
            continue
        base = CATEGORY_WEIGHT[cat]
        # Terms mentioned repeatedly are more central to this person
        boost = 1.0 + min(count - 1, 4) * 0.15
        profile[term] = round(base * boost)

    return profile


def _max_possible(profile: Dict[str, int]) -> int:
    """Normalizer: sum of the 12 strongest profile terms."""
    if not profile:
        return 1
    top = sorted(profile.values(), reverse=True)[:12]
    return max(sum(top), 1)


def score_job(job: Dict, profile: Dict[str, int], ceiling: int) -> Dict:
    title = job.get("title") or ""
    text = " ".join([title, job.get("description") or "", job.get("company") or ""])

    total = 0
    hits: List[str] = []

    for term, weight in profile.items():
        pattern = TERM_RE[term]
        if pattern.search(text):
            # Title matches count double
            multiplier = 2 if pattern.search(title) else 1
            total += weight * multiplier
            hits.append(term)

    score = min(int((total / ceiling) * 100), 100)

    if score >= 70:
        level = "Excellent"
    elif score >= 45:
        level = "Good"
    elif score >= 20:
        level = "Fair"
    else:
        level = "Poor"

    top_hits = sorted(hits, key=lambda t: profile[t], reverse=True)[:4]

    return {
        **job,
        "score": score,
        "match_level": level,
        "key_matches": [h.title() if len(h) > 3 else h.upper() for h in top_hits],
        "gaps": [],
        "summary": "",
        "scored": True,
    }


def score_jobs(jobs: List[Dict], cv_text: str = "") -> List[Dict]:
    profile = build_profile(cv_text)
    if not profile:
        # No CV uploaded — return unscored
        return [{**j, "score": 0, "match_level": "Unscored",
                 "key_matches": [], "gaps": [], "summary": "", "scored": False}
                for j in jobs]

    ceiling = _max_possible(profile)
    return [score_job(j, profile, ceiling) for j in jobs]
