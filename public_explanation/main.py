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
@click.version_option()
def cli(repository, question, model, max_file_size, max_total_size, verbose, dry_run):
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
            f"Dry run: {dry_run}",
            title="Configuration",
            border_style="blue"
        ))
    
    # TODO: Implement repository discovery and processing
    console.print("[yellow]🚧 Tool is under development - Phase 1 complete![/yellow]")
    console.print(f"[green]✅ Successfully parsed arguments:[/green]")
    console.print(f"  Repository: {repository}")
    console.print(f"  Question: {question}")
    
    if dry_run:
        console.print("[blue]ℹ️  This was a dry run - no API calls would be made[/blue]")


if __name__ == "__main__":
    cli() 