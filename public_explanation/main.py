#!/usr/bin/env python3
"""
Main CLI entry point for public-explanation tool.
"""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .repository import RepositoryDiscovery
from .content_processor import ContentProcessor
from .ai_processor import AIProcessor

# Load environment variables from .env file
load_dotenv()

console = Console()


@click.command()
@click.argument('repository', required=True)
@click.argument('question', required=True) 
@click.option('--model', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
@click.option('--max-file-size', default=1, type=int, help='Maximum file size in MB to include (default: 1)')
@click.option('--max-total-size', default=50, type=int, help='Maximum total repository size in MB (default: 50)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be processed without making API calls')
@click.option('--force', is_flag=True, help='Skip cost confirmation prompts')
@click.option('--no-api', is_flag=True, help='Disable GitHub API calls (use mock search only)')
@click.version_option()
def cli(repository, question, model, max_file_size, max_total_size, verbose, dry_run, force, no_api):
    """
    AI-powered GitHub repository explanation tool.
    
    REPOSITORY: GitHub repository (URL, owner/repo, or search term)
    QUESTION: Natural language question about the repository
    
    Examples:
      public-explanation "facebook/react" "how does the virtual DOM work?"
      public-explanation "react router" "how do I set up nested routes?"
      public-explanation "https://github.com/microsoft/vscode" "extension architecture"
    """
    
    # Check for required environment variables
    if not dry_run and not os.getenv('OPENAI_API_KEY'):
        console.print(Panel(
            "[red]ERROR: OPENAI_API_KEY environment variable not found![/red]\n\n"
            "Please create a .env file with your OpenAI API key:\n"
            "[yellow]OPENAI_API_KEY=your_key_here[/yellow]\n\n"
            "Or set it as an environment variable.",
            title="Configuration Error",
            border_style="red"
        ))
        sys.exit(1)
    
    if verbose:
        console.print(Panel(
            f"Repository: {repository}\n"
            f"Question: {question}\n"
            f"Model: {model}\n"
            f"Max file size: {max_file_size}MB\n"
            f"Max total size: {max_total_size}MB\n"
            f"Dry run: {dry_run}\n"
            f"Force: {force}\n"
            f"API disabled: {no_api}",
            title="Configuration",
            border_style="blue"
        ))
    
    # Initialize components
    repo_discovery = RepositoryDiscovery(verbose=verbose)
    content_processor = ContentProcessor(
        max_file_size_mb=max_file_size,
        max_total_size_mb=max_total_size,
        verbose=verbose
    )
    # Don't check dependencies in dry-run mode for development testing
    ai_processor = AIProcessor(model=model, verbose=verbose, check_deps=not dry_run)
    
    try:
        # Sanitize inputs
        clean_repository = repo_discovery.sanitize_input(repository)
        clean_question = repo_discovery.sanitize_input(question)
        
        if verbose and (clean_repository != repository or clean_question != question):
            console.print("[yellow]🧹 Input sanitized for safety[/yellow]")
        
        # Parse repository input (with or without API)
        use_api = not no_api
        repo_info = repo_discovery.parse_repository_input(clean_repository, use_api=use_api)
        
        # Validate repository format
        is_valid, error_msg = repo_discovery.validate_repository_format(repo_info)
        if not is_valid:
            console.print(Panel(
                f"[red]Repository validation failed:[/red] {error_msg}",
                title="Invalid Repository",
                border_style="red"
            ))
            sys.exit(1)
        
        # Display discovered repository info (enhanced with metadata)
        info_text = f"[green]Repository Found:[/green] {repo_info.full_name}\n"
        info_text += f"[blue]URL:[/blue] {repo_info.github_url}\n"
        info_text += f"[blue]Source Type:[/blue] {repo_info.source_type}\n"
        
        if repo_info.description:
            info_text += f"[blue]Description:[/blue] {repo_info.description}\n"
        if repo_info.stars is not None:
            info_text += f"[blue]Stars:[/blue] {repo_info.stars:,}\n"
        if repo_info.size_mb is not None:
            info_text += f"[blue]Size:[/blue] {repo_info.size_mb:.1f}MB\n"
        if repo_info.language:
            info_text += f"[blue]Language:[/blue] {repo_info.language}\n"
        
        info_text += f"[blue]Question:[/blue] {clean_question}"
        
        console.print(Panel(
            info_text,
            title="Repository Discovery",
            border_style="green"
        ))
        
        if repo_info.source_type == 'search_term':
            if no_api:
                console.print("[yellow]ℹ️  Search term with API disabled - using mock result[/yellow]")
            else:
                console.print("[green]ℹ️  Search term processed with GitHub API[/green]")
        
        # Warn about large repositories before processing
        if repo_info.size_mb and repo_info.size_mb > 100 and not force:
            console.print(Panel(
                f"[yellow]⚠️  LARGE REPOSITORY WARNING ⚠️[/yellow]\n\n"
                f"Repository size: [red]{repo_info.size_mb:.1f}MB[/red]\n\n"
                f"This is a large repository that may:\n"
                f"• Take a long time to process\n"
                f"• Exceed token limits and be expensive\n"
                f"• Hit API rate limits\n\n"
                f"💡 Consider using --max-total-size to limit content",
                title="Size Warning",
                border_style="yellow"
            ))
            
            if not Confirm.ask("Do you want to proceed with this large repository?"):
                console.print("[yellow]❌ Processing cancelled by user[/yellow]")
                console.print("[blue]💡 Try: --max-total-size 10 to limit content size[/blue]")
                sys.exit(0)
        
        # Process repository content
        content_result = content_processor.process_repository(repo_info, dry_run=dry_run)
        
        if content_result and not dry_run:
            # Estimate token costs
            token_info = content_processor.estimate_token_cost(
                content_result['content'], 
                clean_question
            )
            
            # Cost safety check
            cost_threshold = 0.05  # 5 cents
            estimated_cost = token_info['estimated_cost_usd']
            
            console.print(Panel(
                f"[blue]Estimated Tokens:[/blue] {token_info['total_tokens']:,}\n"
                f"[blue]Estimated Cost:[/blue] ${estimated_cost:.4f}\n"
                f"[blue]Content Size:[/blue] {content_result['filtered_size']} chars",
                title="Token Estimation",
                border_style="cyan"
            ))
            
            # Check if cost exceeds threshold
            if estimated_cost > cost_threshold and not force:
                console.print(Panel(
                    f"[yellow]⚠️  HIGH COST WARNING ⚠️[/yellow]\n\n"
                    f"Estimated cost: [red]${estimated_cost:.4f}[/red] (>{cost_threshold*100:.0f}¢)\n"
                    f"Tokens: {token_info['total_tokens']:,}\n\n"
                    f"This repository is large and will be expensive to process.\n"
                    f"Consider using --max-total-size to reduce content size.\n\n"
                    f"💡 Tip: Try a smaller repository first or use --dry-run",
                    title="Cost Confirmation Required",
                    border_style="red"
                ))
                
                if not Confirm.ask("Do you want to proceed with this expensive request?"):
                    console.print("[yellow]❌ Request cancelled by user[/yellow]")
                    console.print("[blue]💡 Try using smaller size limits: --max-total-size 5[/blue]")
                    sys.exit(0)
                else:
                    console.print("[green]✅ User confirmed - proceeding with request[/green]")
            elif estimated_cost <= cost_threshold:
                console.print("[green]✅ Cost is reasonable - ready to proceed![/green]")
            
            # Process with AI and render result
            success = ai_processor.process_repository_question(
                repo_info, clean_question, content_result, dry_run=dry_run
            )
            
            if success:
                console.print(Panel(
                    f"[green]🎉 Successfully generated explanation![/green]\n"
                    f"Repository: {repo_info.full_name}\n"
                    f"Cost: ${estimated_cost:.4f}",
                    title="Task Complete",
                    border_style="green"
                ))
            else:
                console.print("[red]❌ Failed to generate explanation[/red]")
                sys.exit(1)
        
        elif dry_run:
            # Show complete dry-run pipeline
            console.print(Panel(
                "[blue]✅ Complete pipeline test successful![/blue]\n\n"
                "Would execute:\n"
                "1. ✅ Repository discovery\n"
                "2. ✅ Content extraction with gitingest\n" 
                "3. ✅ Token cost estimation\n"
                "4. ✅ AI processing with mods\n"
                "5. ✅ Beautiful rendering with glow",
                title="Dry Run Complete",
                border_style="blue"
            ))
        
        if dry_run:
            console.print("[blue]ℹ️  This was a dry run - no repository processing or API calls made[/blue]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]❌ Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(Panel(
            f"[red]Unexpected error:[/red] {str(e)}",
            title="Error",
            border_style="red"
        ))
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    cli() 