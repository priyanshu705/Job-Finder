"""
src/finder/core/explainable_matching.py
---------------------------------------
PHASE A: Explainable AI Matching

Score jobs with transparent, understandable breakdowns.

Formula:
  Final Score = 0.30(skill_match) 
              + 0.30(semantic_fit)
              + 0.20(goal_alignment)
              + 0.10(level_match)
              + 0.10(hiring_signals)
"""

import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)


@dataclass
class ScoreComponent:
    """Individual score component contribution."""
    label: str
    value: float  # 0-1 normalized
    explanation: str
    weight: float  # 0-1
    max_score: float = None  # Contribution to final score


class ExplainableJobMatcher:
    """
    Score jobs with transparent breakdown.
    
    Provides clear explanations for every point awarded.
    """
    
    def __init__(self, user_resume_text: str, user_goals: Dict = None):
        self.resume_text = (user_resume_text or "").lower()
        self.goals = user_goals or {}
        self.components = []
    
    def match(self, job_dict: Dict) -> Tuple[float, List[Dict]]:
        """
        Score job with explanation.
        
        Args:
            job_dict: Job with title, description, company, skills, etc.
            
        Returns:
            (final_score_0_100, list_of_components)
        """
        self.components = []
        
        job_title = (job_dict.get("title") or "").lower()
        job_desc = (job_dict.get("description") or "").lower()
        job_skills = (job_dict.get("skills") or "").lower()
        company = job_dict.get("company", "")
        
        # Extract resume skills
        resume_skills = self._extract_resume_skills()
        
        # 1. Skill Match (30% weight)
        skill_score = self._calculate_skill_match(resume_skills, job_skills)
        self.components.append(ScoreComponent(
            label="Skill Match",
            value=skill_score,
            explanation=self._skill_explanation(resume_skills, job_skills),
            weight=0.30
        ))
        
        # 2. Semantic Fit (30% weight)
        semantic_score = self._calculate_semantic_fit(job_desc)
        self.components.append(ScoreComponent(
            label="Semantic Fit",
            value=semantic_score,
            explanation=self._semantic_explanation(job_title),
            weight=0.30
        ))
        
        # 3. Goal Alignment (20% weight)
        goal_score = self._calculate_goal_alignment(job_title)
        self.components.append(ScoreComponent(
            label="Goal Alignment",
            value=goal_score,
            explanation=self._goal_explanation(job_title),
            weight=0.20
        ))
        
        # 4. Level Match (10% weight)
        level_score = self._calculate_level_match(job_title)
        self.components.append(ScoreComponent(
            label="Experience Level",
            value=level_score,
            explanation=self._level_explanation(job_title),
            weight=0.10
        ))
        
        # 5. Hiring Signals (10% weight)
        signal_score = self._calculate_hiring_signals(job_desc)
        self.components.append(ScoreComponent(
            label="Hiring Signals",
            value=signal_score,
            explanation=self._signal_explanation(job_desc),
            weight=0.10
        ))
        
        # Calculate weighted final score
        final_score = sum(c.value * c.weight for c in self.components)
        
        # Assign max_score to each component
        for c in self.components:
            c.max_score = c.value * c.weight
        
        return final_score * 100, [asdict(c) for c in self.components]
    
    # ─────────────────────────────────────────────────────────────────
    # SKILL MATCHING
    # ─────────────────────────────────────────────────────────────────
    
    def _extract_resume_skills(self) -> set:
        """Extract detected tech skills from resume."""
        skill_keywords = {
            "python": ["python", "django", "flask", "celery"],
            "javascript": ["javascript", "js", "node", "nodejs"],
            "react": ["react", "jsx", "redux"],
            "frontend": ["html", "css", "vue", "angular"],
            "backend": ["api", "rest", "graphql"],
            "sql": ["sql", "postgres", "mysql", "sqlite"],
            "database": ["database", "db", "sql"],
            "java": ["java", "spring", "maven"],
            "aws": ["aws", "ec2", "s3", "lambda"],
            "docker": ["docker", "container"],
            "git": ["git", "github", "gitlab"],
        }
        
        detected = set()
        for skill, keywords in skill_keywords.items():
            if any(kw in self.resume_text for kw in keywords):
                detected.add(skill)
        
        return detected
    
    def _calculate_skill_match(self, resume_skills: set, job_skills: str) -> float:
        """Calculate skill overlap ratio."""
        if not resume_skills:
            return 0.3  # Neutral if no skills detected
        
        job_skills_lower = job_skills.lower()
        matches = sum(1 for skill in resume_skills if skill in job_skills_lower)
        
        # Score: matches / (matches + 1) to avoid divide by zero
        return min(matches / (len(resume_skills) + 1), 1.0)
    
    def _skill_explanation(self, resume_skills: set, job_skills: str) -> str:
        """Explain skill match."""
        job_skills_lower = job_skills.lower()
        matched = [s for s in resume_skills if s in job_skills_lower]
        
        if not matched:
            return "Limited skill overlap with job requirements"
        
        matched_str = ", ".join(sorted(matched)[:3])
        return f"Your resume shows: {matched_str}"
    
    # ─────────────────────────────────────────────────────────────────
    # SEMANTIC FIT
    # ─────────────────────────────────────────────────────────────────
    
    def _calculate_semantic_fit(self, job_desc: str) -> float:
        """Measure how closely job description matches resume context."""
        if not job_desc:
            return 0.5
        
        # Simple TF-IDF style: intersection / union of words
        resume_words = set(self.resume_text.split())
        job_words = set(job_desc.split())
        
        if not job_words:
            return 0.5
        
        intersection = len(resume_words & job_words)
        union = len(resume_words | job_words)
        
        if union == 0:
            return 0.5
        
        return min(intersection / union, 1.0)
    
    def _semantic_explanation(self, job_title: str) -> str:
        """Explain semantic fit."""
        if "senior" in job_title.lower():
            return "Experience level aligns with job posting tone"
        if "intern" in job_title.lower():
            return "Entry-level role matches career stage"
        return "Job description aligns with your experience"
    
    # ─────────────────────────────────────────────────────────────────
    # GOAL ALIGNMENT
    # ─────────────────────────────────────────────────────────────────
    
    def _calculate_goal_alignment(self, job_title: str) -> float:
        """Check if job aligns with user's career goals."""
        target_role = (self.goals.get("target_role") or "").lower()
        
        if not target_role:
            return 0.7  # Neutral if no goal set
        
        if target_role in job_title:
            return 1.0  # Perfect match
        
        # Partial credit for similar roles
        role_families = {
            "frontend": ["frontend", "react", "vue", "angular", "ui"],
            "backend": ["backend", "api", "server", "django", "node"],
            "fullstack": ["fullstack", "full-stack", "full stack"],
            "devops": ["devops", "sre", "infrastructure"],
        }
        
        for family, keywords in role_families.items():
            if any(kw in target_role for kw in keywords):
                if any(kw in job_title for kw in keywords):
                    return 0.8  # Family match
        
        return 0.5  # Different role
    
    def _goal_explanation(self, job_title: str) -> str:
        """Explain goal alignment."""
        target_role = (self.goals.get("target_role") or "").lower()
        
        if not target_role:
            return "No target role set - aligns with general search"
        
        if target_role in job_title:
            return f"Matches your target: {self.goals.get('target_role')}"
        
        return "Complements your career goals"
    
    # ─────────────────────────────────────────────────────────────────
    # LEVEL MATCHING
    # ─────────────────────────────────────────────────────────────────
    
    def _calculate_level_match(self, job_title: str) -> float:
        """Check experience level fit."""
        user_years = self.goals.get("years_experience", 0)
        job_title_lower = job_title.lower()
        
        levels = {
            "intern": (0, 1),
            "junior": (1, 3),
            "mid": (3, 7),
            "senior": (7, 15),
            "lead": (10, 30),
        }
        
        # Detect job level from title
        job_level_range = None
        for level, (min_yrs, max_yrs) in levels.items():
            if level in job_title_lower:
                job_level_range = (min_yrs, max_yrs)
                break
        
        if not job_level_range:
            return 0.8  # Neutral if unclear
        
        min_yrs, max_yrs = job_level_range
        
        if min_yrs <= user_years <= max_yrs:
            return 1.0  # Perfect fit
        elif user_years < min_yrs:
            return 0.6  # Stretch role (good for growth)
        else:
            return 0.4  # Underleveled role
    
    def _level_explanation(self, job_title: str) -> str:
        """Explain level match."""
        years = self.goals.get("years_experience", 0)
        job_lower = job_title.lower()
        
        if "intern" in job_lower and years < 1:
            return "Internship - perfect for your stage"
        elif "junior" in job_lower and 1 <= years < 3:
            return "Junior level - great fit for your experience"
        elif "senior" in job_lower and years >= 7:
            return "Senior role - matches your seniority"
        elif "mid" in job_lower and 3 <= years < 7:
            return "Mid-level - perfect career progression"
        
        return "Experience level compatible"
    
    # ─────────────────────────────────────────────────────────────────
    # HIRING SIGNALS
    # ─────────────────────────────────────────────────────────────────
    
    def _calculate_hiring_signals(self, job_desc: str) -> float:
        """Detect positive hiring signals."""
        if not job_desc:
            return 0.5
        
        signals = {
            "visa": ["visa", "sponsorship", "h1b", "work authorization"],
            "remote": ["remote", "work from home", "distributed"],
            "equity": ["equity", "stock options", "partnership"],
            "startup": ["startup", "early-stage"],
            "diversity": ["diversity", "women", "underrepresented"],
        }
        
        signal_count = sum(
            1 for signal_type, keywords in signals.items()
            if any(kw in job_desc for kw in keywords)
        )
        
        return min(signal_count / len(signals), 1.0)
    
    def _signal_explanation(self, job_desc: str) -> str:
        """Explain hiring signals found."""
        signals = []
        
        if any(w in job_desc for w in ["visa", "sponsorship"]):
            signals.append("Offers visa sponsorship")
        if any(w in job_desc for w in ["remote", "work from home"]):
            signals.append("Remote position")
        if any(w in job_desc for w in ["equity", "stock"]):
            signals.append("Equity compensation")
        
        if signals:
            return " • ".join(signals)
        
        return "Standard hiring profile"
