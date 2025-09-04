"""
Repository discovery and validation module.
Handles parsing various GitHub repository formats and validation.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

from rich.console import Console

from .models import RepositoryInfo
from .github_api import GitHubAPI

console = Console()


class RepositoryDiscovery:
    """Handles discovery and parsing of GitHub repositories."""
    
    # GitHub URL patterns
    GITHUB_URL_PATTERN = re.compile(
        r'https?://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)/?'
    )
    
    # Owner/repo pattern (e.g., "facebook/react")
    OWNER_REPO_PATTERN = re.compile(
        r'^([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)$'
    )
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.github_api = GitHubAPI(verbose=verbose)
    
    def parse_repository_input(self, repository_input: str, use_api: bool = True) -> RepositoryInfo:
        """
        Parse various repository input formats and return RepositoryInfo.
        
        Supports:
        - Full GitHub URLs: https://github.com/owner/repo
        - Owner/repo format: owner/repo
        - Search terms: "react router" (uses GitHub Search API if use_api=True)
        """
        repository_input = repository_input.strip()
        
        if self.verbose:
            console.print(f"[blue]🔍 Parsing repository input: {repository_input}[/blue]")
        
        # Try GitHub URL first
        url_match = self.GITHUB_URL_PATTERN.match(repository_input)
        if url_match:
            owner, repo = url_match.groups()
            if self.verbose:
                console.print(f"[green]✅ Detected GitHub URL format[/green]")
            
            repo_info = RepositoryInfo(
                owner=owner,
                name=repo,
                url=repository_input,
                source_type='url'
            )
            
            # Fetch additional metadata if using API
            if use_api:
                github_info = self.github_api.get_repository_info(owner, repo)
                if github_info:
                    repo_info.description = github_info.description
                    repo_info.stars = github_info.stars
                    repo_info.size_mb = github_info.size_mb
                    repo_info.language = github_info.language
            
            return repo_info
        
        # Try owner/repo format
        owner_repo_match = self.OWNER_REPO_PATTERN.match(repository_input)
        if owner_repo_match:
            owner, repo = owner_repo_match.groups()
            if self.verbose:
                console.print(f"[green]✅ Detected owner/repo format[/green]")
            
            repo_info = RepositoryInfo(
                owner=owner,
                name=repo,
                url=f"https://github.com/{owner}/{repo}",
                source_type='owner_repo'
            )
            
            # Fetch additional metadata if using API
            if use_api:
                github_info = self.github_api.get_repository_info(owner, repo)
                if github_info:
                    repo_info.description = github_info.description
                    repo_info.stars = github_info.stars
                    repo_info.size_mb = github_info.size_mb
                    repo_info.language = github_info.language
            
            return repo_info
        
        # If neither pattern matches, treat as search term
        if self.verbose:
            console.print(f"[yellow]🔍 Treating as search term[/yellow]")
        
        if use_api:
            return self._search_repositories(repository_input)
        else:
            # Fall back to mock for testing
            return self._mock_search_result(repository_input)
    
    def _search_repositories(self, search_term: str) -> RepositoryInfo:
        """
        Search GitHub repositories using the Search API.
        """
        if self.verbose:
            console.print(f"[blue]🔍 Searching GitHub for repositories matching: '{search_term}'[/blue]")
        
        # Search for repositories
        results = self.github_api.search_repositories(search_term, limit=10)
        
        if not results:
            console.print(f"[red]❌ No repositories found for: {search_term}[/red]")
            console.print("[blue]💡 Try using a more specific search term or owner/repo format[/blue]")
            raise ValueError(f"No repositories found for search term: {search_term}")
        
        # Let user select from results
        selected = self.github_api.select_repository_interactive(results)
        if not selected:
            raise ValueError("Repository selection cancelled")
        
        return RepositoryInfo(
            owner=selected.owner,
            name=selected.name,
            url=selected.url,
            source_type='search_term',
            description=selected.description,
            stars=selected.stars,
            size_mb=selected.size_mb,
            language=selected.language
        )
    
    def _mock_search_result(self, search_term: str) -> RepositoryInfo:
        """
        Mock search functionality for testing without API calls.
        This is kept for fallback and testing purposes.
        """
        # Create a mock result based on common search terms
        mock_results = {
            'react': ('facebook', 'react'),
            'react router': ('remix-run', 'react-router'),
            'vue': ('vuejs', 'vue'),
            'angular': ('angular', 'angular'),
            'express': ('expressjs', 'express'),
            'fastapi': ('tiangolo', 'fastapi'),
            'django': ('django', 'django'),
            'flask': ('pallets', 'flask'),
            'next': ('vercel', 'next.js'),
            'nuxt': ('nuxt', 'nuxt'),
        }
        
        # Try to find a mock match
        search_lower = search_term.lower()
        for term, (owner, repo) in mock_results.items():
            if term in search_lower:
                if self.verbose:
                    console.print(f"[blue]🎭 Using mock result for '{search_term}': {owner}/{repo}[/blue]")
                return RepositoryInfo(
                    owner=owner,
                    name=repo,
                    url=f"https://github.com/{owner}/{repo}",
                    source_type='search_term'
                )
        
        # If no mock found, create a generic mock
        if self.verbose:
            console.print(f"[yellow]🎭 No mock found, creating generic mock for '{search_term}'[/yellow]")
        
        # Use first word as both owner and repo for testing
        clean_term = re.sub(r'[^a-zA-Z0-9]', '', search_term.split()[0])
        return RepositoryInfo(
            owner='mock-owner',
            name=clean_term or 'mock-repo',
            url=f"https://github.com/mock-owner/{clean_term or 'mock-repo'}",
            source_type='search_term'
        )
    
    def validate_repository_format(self, repo_info: RepositoryInfo) -> Tuple[bool, Optional[str]]:
        """
        Validate that the repository information is properly formatted.
        Returns (is_valid, error_message).
        """
        # Check owner format
        if not re.match(r'^[a-zA-Z0-9._-]+$', repo_info.owner):
            return False, f"Invalid owner format: {repo_info.owner}"
        
        # Check repository name format
        if not re.match(r'^[a-zA-Z0-9._-]+$', repo_info.name):
            return False, f"Invalid repository name format: {repo_info.name}"
        
        # Check for common invalid patterns
        if repo_info.owner.lower() in ['', 'null', 'undefined']:
            return False, f"Invalid owner: {repo_info.owner}"
        
        if repo_info.name.lower() in ['', 'null', 'undefined']:
            return False, f"Invalid repository name: {repo_info.name}"
        
        return True, None
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize user input to prevent issues."""
        # Remove leading/trailing whitespace
        sanitized = input_str.strip()
        
        # Remove any potential shell injection characters for safety
        # (though we won't be executing shell commands with this input directly)
        dangerous_chars = ['`', '$', ';', '|', '&', '>', '<']
        for char in dangerous_chars:
            if char in sanitized:
                console.print(f"[yellow]⚠️  Removed potentially dangerous character: {char}[/yellow]")
                sanitized = sanitized.replace(char, '')
        
        return sanitized 