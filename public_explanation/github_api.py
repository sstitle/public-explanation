"""
GitHub API integration for repository search and metadata.
Handles GitHub Search API with rate limiting and authentication.
"""

import os
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import IntPrompt

from .models import RepositoryInfo, GitHubRepoResult

console = Console()


class GitHubAPI:
    """GitHub API client with rate limiting and search capabilities."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None, verbose: bool = False):
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.verbose = verbose
        self.session = requests.Session()
        
        if self.token:
            self.session.headers.update({'Authorization': f'token {self.token}'})
            if verbose:
                console.print("[green]🔑 Using GitHub token for higher rate limits[/green]")
        else:
            if verbose:
                console.print("[yellow]⚠️  No GitHub token - using unauthenticated requests (lower rate limits)[/yellow]")
    
    def search_repositories(self, query: str, limit: int = 5) -> List[GitHubRepoResult]:
        """
        Search GitHub repositories using the Search API.
        
        Args:
            query: Search query (e.g., "react router")
            limit: Maximum number of results to return
            
        Returns:
            List of GitHubRepoResult objects
        """
        if self.verbose:
            console.print(f"[blue]🔍 Searching GitHub for: '{query}'[/blue]")
        
        try:
            # Check rate limits before making request
            self._check_rate_limits()
            
            # Construct search query
            search_url = f"{self.BASE_URL}/search/repositories"
            params = {
                'q': query,
                'sort': 'stars',  # Sort by popularity
                'order': 'desc',
                'per_page': limit
            }
            
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if self.verbose:
                total_count = data.get('total_count', 0)
                console.print(f"[green]✅ Found {total_count} repositories[/green]")
            
            # Parse results
            results = []
            for item in data.get('items', []):
                result = GitHubRepoResult(
                    owner=item['owner']['login'],
                    name=item['name'],
                    description=item.get('description'),
                    stars=item['stargazers_count'],
                    size_kb=item['size'],
                    language=item.get('language'),
                    updated_at=item['updated_at'],
                    url=item['html_url']
                )
                results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ GitHub API error: {str(e)}[/red]")
            return []
        except Exception as e:
            console.print(f"[red]❌ Unexpected error during search: {str(e)}[/red]")
            return []
    
    def get_repository_info(self, owner: str, repo: str) -> Optional[GitHubRepoResult]:
        """
        Get detailed information about a specific repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            GitHubRepoResult or None if not found
        """
        if self.verbose:
            console.print(f"[blue]📋 Fetching info for {owner}/{repo}[/blue]")
        
        try:
            self._check_rate_limits()
            
            url = f"{self.BASE_URL}/repos/{owner}/{repo}"
            response = self.session.get(url)
            
            if response.status_code == 404:
                console.print(f"[red]❌ Repository {owner}/{repo} not found[/red]")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return GitHubRepoResult(
                owner=data['owner']['login'],
                name=data['name'],
                description=data.get('description'),
                stars=data['stargazers_count'],
                size_kb=data['size'],
                language=data.get('language'),
                updated_at=data['updated_at'],
                url=data['html_url']
            )
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Error fetching repository info: {str(e)}[/red]")
            return None
    
    def _check_rate_limits(self):
        """Check GitHub API rate limits and warn if low."""
        try:
            response = self.session.get(f"{self.BASE_URL}/rate_limit")
            if response.status_code == 200:
                data = response.json()
                search_limit = data['resources']['search']
                remaining = search_limit['remaining']
                reset_time = datetime.fromtimestamp(search_limit['reset'])
                
                if remaining < 5:
                    console.print(Panel(
                        f"[yellow]⚠️  GitHub API rate limit warning[/yellow]\n"
                        f"Remaining requests: {remaining}\n"
                        f"Reset time: {reset_time.strftime('%H:%M:%S')}\n\n"
                        f"Consider adding a GITHUB_TOKEN to your .env file for higher limits.",
                        title="Rate Limit Warning",
                        border_style="yellow"
                    ))
                
                if self.verbose:
                    console.print(f"[blue]📊 GitHub API: {remaining} requests remaining[/blue]")
                    
        except Exception:
            # Don't fail if rate limit check fails
            pass
    
    def select_repository_interactive(self, results: List[GitHubRepoResult]) -> Optional[GitHubRepoResult]:
        """
        Present repository search results for user selection.
        
        Args:
            results: List of search results
            
        Returns:
            Selected GitHubRepoResult or None if cancelled
        """
        if not results:
            console.print("[red]❌ No repositories found[/red]")
            return None
        
        if len(results) == 1:
            repo = results[0]
            console.print(f"[green]✅ Found single match: {repo.full_name}[/green]")
            return repo
        
        # Display results in a table
        table = Table(title="Repository Search Results")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Repository", style="green")
        table.add_column("Description", style="white", max_width=50)
        table.add_column("Stars", style="yellow", justify="right")
        table.add_column("Size", style="blue", justify="right")
        table.add_column("Language", style="magenta")
        
        for i, repo in enumerate(results, 1):
            table.add_row(
                str(i),
                repo.full_name,
                repo.description[:47] + "..." if repo.description and len(repo.description) > 50 else repo.description or "No description",
                f"{repo.stars:,}",
                f"{repo.size_mb:.1f}MB",
                repo.language or "Unknown"
            )
        
        console.print(table)
        
        # Get user selection
        try:
            choice = IntPrompt.ask(
                "Select a repository",
                choices=[str(i) for i in range(1, len(results) + 1)],
                default=1
            )
            return results[choice - 1]
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]❌ Selection cancelled[/yellow]")
            return None 