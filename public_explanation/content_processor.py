"""
Content processing module using gitingest for repository analysis.
Handles repository content extraction with intelligent file filtering and prioritization.
"""

import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from gitingest import ingest
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import RepositoryInfo

console = Console()


class ContentProcessor:
    """Processes repository content using gitingest with intelligent filtering."""
    
    def __init__(self, max_file_size_mb: int = 1, max_total_size_mb: int = 50, verbose: bool = False):
        self.max_file_size_mb = max_file_size_mb
        self.max_total_size_mb = max_total_size_mb
        self.verbose = verbose
        
        # Convert MB to bytes for gitingest
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_total_size_bytes = max_total_size_mb * 1024 * 1024
    
    def _extract_question_keywords(self, question: str) -> List[str]:
        """Extract relevant keywords from the user's question for file filtering."""
        # Remove common question words and extract meaningful terms
        stop_words = {'how', 'what', 'where', 'when', 'why', 'does', 'do', 'can', 'is', 'are', 
                     'the', 'a', 'an', 'to', 'for', 'with', 'in', 'on', 'at', 'by', 'this', 'that'}
        
        # Extract words, convert to lowercase, remove stop words
        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Add common programming concepts that might be relevant
        tech_terms = ['api', 'rest', 'auth', 'test', 'config', 'setup', 'install', 'deploy', 
                     'docker', 'database', 'model', 'view', 'controller', 'route', 'middleware']
        
        for term in tech_terms:
            if term in question.lower():
                keywords.append(term)
        
        return list(set(keywords))  # Remove duplicates
    
    def _generate_include_patterns(self, question: str, repo_info: RepositoryInfo) -> Set[str]:
        """Generate minimal, focused include patterns based on question context."""
        patterns = set()
        
        # ALWAYS include core documentation (essential for any question)
        patterns.update({
            'README*', 'readme*', 
            'CONTRIBUTING*', 'LICENSE*'
        })
        
        # Add minimal language-specific patterns
        language = repo_info.language or 'unknown'
        if language.lower() == 'python':
            patterns.update({
                'pyproject.toml', 'setup.py', 'requirements*.txt',
                '__init__.py'  # Package entry points
            })
        
        # Question-driven patterns (keep very minimal)
        question_lower = question.lower()
        
        if any(term in question_lower for term in ['api', 'rest', 'endpoint']):
            # Only core API-related files
            patterns.update({
                '*api*.py', 'main.py', 'app.py',
                'docs/tutorial/*.md'  # Tutorial docs for learning
            })
        
        if any(term in question_lower for term in ['tutorial', 'example', 'getting started']):
            patterns.update({
                'examples/*', 'tutorial/*', 'docs/tutorial/*'
            })
        
        if any(term in question_lower for term in ['config', 'setup', 'install']):
            patterns.update({
                'setup.py', 'pyproject.toml', 'requirements*.txt',
                'Dockerfile', 'docker-compose.*'
            })
        
        return patterns
    
    def _generate_exclude_patterns(self) -> Set[str]:
        """Generate common exclude patterns to skip non-essential files."""
        return {
            # Dependencies and build artifacts
            'node_modules/*', 'dist/*', 'build/*', 'target/*', '__pycache__/*',
            '*.pyc', '*.pyo', '*.class', '*.jar', '*.war',
            
            # Version control and IDE
            '.git/*', '.svn/*', '.hg/*', '.vscode/*', '.idea/*',
            
            # Logs and temporary files
            '*.log', '*.tmp', '*.temp', 'tmp/*', 'temp/*',
            
            # Media and binary files
            '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.ico',
            '*.pdf', '*.zip', '*.tar.gz', '*.exe', '*.dll', '*.so',
            
            # Large data files
            '*.csv', '*.json', '*.xml', '*.sql', '*.db', '*.sqlite',
            
            # Test coverage and reports
            'coverage/*', '.coverage', '.nyc_output/*', 'htmlcov/*',
            
            # Package manager caches
            '.npm/*', '.yarn/*', '.pip/*', '.cache/*'
        }
    
    def _calculate_file_importance(self, filepath: str, question_keywords: List[str]) -> int:
        """Calculate importance score for a file based on type and question relevance."""
        score = 0
        filename = Path(filepath).name.lower()
        filepath_lower = filepath.lower()
        
        # High priority: README and main documentation
        if any(readme in filename for readme in ['readme', 'README']):
            score += 100
        elif filename in ['contributing.md', 'contributing.rst', 'license', 'license.md', 'license.txt']:
            score += 90
        elif any(doc in filepath_lower for doc in ['docs/', 'doc/', 'documentation/']):
            score += 80
        elif filename.endswith(('.md', '.rst', '.txt')) and 'doc' in filename:
            score += 75
        
        # Medium-high priority: Main source files and configs
        elif filename in ['main.py', 'app.py', 'server.py', 'index.js', 'app.js', 'main.js']:
            score += 70
        elif filename in ['package.json', 'pyproject.toml', 'setup.py', 'requirements.txt', 'cargo.toml']:
            score += 65
        elif filename.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs')) and not 'test' in filepath_lower:
            score += 60
        
        # Medium priority: Configuration files
        elif filename.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.conf')):
            score += 40
        elif filename in ['dockerfile', 'makefile', '.env.example']:
            score += 45
        
        # Lower priority: Tests and examples
        elif 'test' in filepath_lower or 'spec' in filepath_lower:
            score += 20
        elif 'example' in filepath_lower or 'demo' in filepath_lower:
            score += 25
        
        # Question relevance boost
        for keyword in question_keywords:
            if keyword in filepath_lower or keyword in filename:
                score += 30
        
        return score
    
    def _show_filtering_plan(self, repo_info: RepositoryInfo, question: str):
        """Show what filtering strategy will be used."""
        keywords = self._extract_question_keywords(question)
        include_patterns = self._generate_include_patterns(question, repo_info)
        exclude_patterns = self._generate_exclude_patterns()
        
        table = Table(title="Intelligent Filtering Plan")
        table.add_column("Strategy", style="cyan")
        table.add_column("Details", style="white")
        
        table.add_row("Question Keywords", ", ".join(keywords) if keywords else "None extracted")
        table.add_row("Language Focus", repo_info.language or "Generic")
        table.add_row("Include Patterns", f"{len(include_patterns)} patterns (docs, source, config)")
        table.add_row("Exclude Patterns", f"{len(exclude_patterns)} patterns (node_modules, build, etc.)")
        table.add_row("Max File Size", f"{self.max_file_size_mb}MB")
        table.add_row("Strategy", "README-first, docs-priority, question-relevant")
        
        console.print(table)
        
        if self.verbose:
            console.print(f"\n[blue]🔍 Include patterns:[/blue] {', '.join(sorted(include_patterns)[:10])}...")
            console.print(f"[blue]🚫 Exclude patterns:[/blue] {', '.join(sorted(exclude_patterns)[:10])}...")

    def process_repository(self, repo_info: RepositoryInfo, dry_run: bool = False, question: str = "") -> Optional[Dict]:
        """
        Process repository content using gitingest with intelligent filtering.
        
        Args:
            repo_info: Repository information
            dry_run: If True, show plan without processing
            question: User question for context-aware filtering
            
        Returns:
            Dict with 'summary', 'tree', 'content' keys, or None if dry_run
        """
        if self.verbose:
            console.print(f"[blue]📂 Processing repository: {repo_info.full_name}[/blue]")
        
        if dry_run:
            console.print("[yellow]🎭 Dry run: Would process repository with intelligent filtering[/yellow]")
            self._show_filtering_plan(repo_info, question)
            return None
        
        try:
            # Generate intelligent filtering patterns
            include_patterns = self._generate_include_patterns(question, repo_info)
            exclude_patterns = self._generate_exclude_patterns()
            
            if self.verbose:
                console.print(f"[blue]🎯 Using {len(include_patterns)} include patterns and {len(exclude_patterns)} exclude patterns[/blue]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Extracting repository content with intelligent filtering...", total=None)
                
                # Use gitingest with intelligent filtering
                summary, tree, content = ingest(
                    repo_info.github_url,
                    max_file_size=self.max_file_size_bytes,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    include_submodules=False  # Keep it simple
                )
                
                progress.update(task, description="Applying final content optimization...")
                
                # Apply final size filtering if needed (backup safety check)
                filtered_content = self._filter_content_by_size(content)
                
                progress.update(task, description="Content extraction complete!")
            
            # Display processing results
            self._display_processing_results(summary, tree, filtered_content, include_patterns, exclude_patterns)
            
            return {
                'summary': summary,
                'tree': tree, 
                'content': filtered_content,
                'original_size': len(content),
                'filtered_size': len(filtered_content),
                'filtering_applied': True
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
    

    
    def _display_processing_results(self, summary: str, tree: str, content: str, include_patterns: Set[str] = None, exclude_patterns: Set[str] = None):
        """Display the results of repository processing with filtering info."""
        content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        
        table = Table(title="Intelligent Repository Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Content Size", f"{content_size_mb:.2f} MB")
        table.add_row("Summary Length", f"{len(summary)} chars")
        table.add_row("Tree Length", f"{len(tree)} chars")
        table.add_row("Total Content", f"{len(content)} chars")
        
        if include_patterns:
            table.add_row("Include Patterns", f"{len(include_patterns)} patterns applied")
        if exclude_patterns:
            table.add_row("Exclude Patterns", f"{len(exclude_patterns)} patterns applied")
        
        console.print(table)
        
        if self.verbose:
            console.print("\n[blue]📋 Repository Summary (first 200 chars):[/blue]")
            console.print(summary[:200] + "..." if len(summary) > 200 else summary)
            
            if include_patterns:
                console.print(f"\n[green]🎯 Smart filtering applied:[/green] Prioritized docs, source, and question-relevant files")
    
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