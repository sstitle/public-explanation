"""
Shared data models for the public-explanation tool.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RepositoryInfo:
    """Information about a GitHub repository."""
    owner: str
    name: str
    url: str
    source_type: str  # 'url', 'owner_repo', 'search_term'
    description: Optional[str] = None
    stars: Optional[int] = None
    size_mb: Optional[float] = None
    language: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Return the full repository name in owner/repo format."""
        return f"{self.owner}/{self.name}"
    
    @property
    def github_url(self) -> str:
        """Return the full GitHub URL."""
        return f"https://github.com/{self.owner}/{self.name}"


@dataclass
class GitHubRepoResult:
    """GitHub repository search result."""
    owner: str
    name: str
    description: Optional[str]
    stars: int
    size_kb: int
    language: Optional[str]
    updated_at: str
    url: str
    
    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"
    
    @property
    def size_mb(self) -> float:
        return self.size_kb / 1024 