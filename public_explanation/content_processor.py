"""
Content processing module using gitingest for repository analysis.
Handles repository content extraction with file size limits and filtering.
"""

import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gitingest import ingest
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import RepositoryInfo

console = Console()


class ContentProcessor:
    """Processes repository content using gitingest with size limits."""
    
    def __init__(self, max_file_size_mb: int = 1, max_total_size_mb: int = 50, verbose: bool = False):
        self.max_file_size_mb = max_file_size_mb
        self.max_total_size_mb = max_total_size_mb
        self.verbose = verbose
        
        # Convert MB to bytes for gitingest
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_total_size_bytes = max_total_size_mb * 1024 * 1024
    
    def process_repository(self, repo_info: RepositoryInfo, dry_run: bool = False) -> Optional[Dict]:
        """
        Process repository content using gitingest.
        
        Returns:
            Dict with 'summary', 'tree', 'content' keys, or None if dry_run
        """
        if self.verbose:
            console.print(f"[blue]📂 Processing repository: {repo_info.full_name}[/blue]")
        
        if dry_run:
            console.print("[yellow]🎭 Dry run: Would process repository content with gitingest[/yellow]")
            self._show_processing_plan(repo_info)
            return None
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Extracting repository content...", total=None)
                
                # Use gitingest to extract repository content
                # Note: gitingest doesn't directly support file size limits in its API
                # We'll implement filtering after extraction
                summary, tree, content = ingest(
                    repo_info.github_url,
                    # include_submodules=False,  # Keep it simple for now
                    # We'll add file filtering logic after getting the content
                )
                
                progress.update(task, description="Processing content...")
                
                # Filter content based on size limits
                filtered_content = self._filter_content_by_size(content)
                
                progress.update(task, description="Content extraction complete!")
            
            # Display processing results
            self._display_processing_results(summary, tree, filtered_content)
            
            return {
                'summary': summary,
                'tree': tree, 
                'content': filtered_content,
                'original_size': len(content),
                'filtered_size': len(filtered_content)
            }
            
        except Exception as e:
            console.print(f"[red]❌ Error processing repository: {str(e)}[/red]")
            if self.verbose:
                console.print_exception()
            return None
    
    def _filter_content_by_size(self, content: str) -> str:
        """
        Filter repository content based on size limits.
        This is a simple implementation - in practice, gitingest should handle this.
        """
        if len(content.encode('utf-8')) <= self.max_total_size_bytes:
            if self.verbose:
                console.print(f"[green]✅ Content size OK: {len(content.encode('utf-8'))} bytes[/green]")
            return content
        
        # If content is too large, truncate with a warning
        max_chars = int(self.max_total_size_bytes * 0.8)  # Rough estimate for UTF-8
        truncated = content[:max_chars]
        
        warning_msg = f"\n\n[CONTENT TRUNCATED - Original size exceeded {self.max_total_size_mb}MB limit]"
        
        if self.verbose:
            console.print(f"[yellow]⚠️  Content truncated from {len(content)} to {len(truncated)} chars[/yellow]")
        
        return truncated + warning_msg
    
    def _show_processing_plan(self, repo_info: RepositoryInfo):
        """Show what would be processed in dry run mode."""
        table = Table(title="Processing Plan")
        table.add_column("Step", style="cyan")
        table.add_column("Action", style="white")
        table.add_column("Limits", style="yellow")
        
        table.add_row(
            "1", 
            f"Extract content from {repo_info.github_url}",
            f"Max file: {self.max_file_size_mb}MB"
        )
        table.add_row(
            "2",
            "Filter files by size and relevance", 
            f"Max total: {self.max_total_size_mb}MB"
        )
        table.add_row(
            "3",
            "Generate repository tree and summary",
            "Token-optimized format"
        )
        
        console.print(table)
    
    def _display_processing_results(self, summary: str, tree: str, content: str):
        """Display the results of repository processing."""
        content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        
        table = Table(title="Repository Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Content Size", f"{content_size_mb:.2f} MB")
        table.add_row("Summary Length", f"{len(summary)} chars")
        table.add_row("Tree Length", f"{len(tree)} chars")
        table.add_row("Total Content", f"{len(content)} chars")
        
        console.print(table)
        
        if self.verbose:
            console.print("\n[blue]📋 Repository Summary (first 200 chars):[/blue]")
            console.print(summary[:200] + "..." if len(summary) > 200 else summary)
    
    def estimate_token_cost(self, content: str, question: str) -> Dict[str, int]:
        """
        Estimate token usage for the AI request.
        This is a rough estimation - actual usage may vary.
        """
        # Rough estimation: ~4 characters per token for English text
        chars_per_token = 4
        
        prompt_tokens = len(content + question) // chars_per_token
        # Estimated response tokens (usually much smaller than input)
        estimated_response_tokens = min(1000, prompt_tokens // 10)
        
        total_tokens = prompt_tokens + estimated_response_tokens
        
        # GPT-4o pricing (approximate, as of 2024)
        input_cost_per_1k = 0.005  # $5 per 1M tokens
        output_cost_per_1k = 0.015  # $15 per 1M tokens
        
        estimated_cost = (prompt_tokens * input_cost_per_1k / 1000) + (estimated_response_tokens * output_cost_per_1k / 1000)
        
        return {
            'prompt_tokens': prompt_tokens,
            'estimated_response_tokens': estimated_response_tokens,
            'total_tokens': total_tokens,
            'estimated_cost_usd': estimated_cost
        } 