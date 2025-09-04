"""
AI processing module using mods for OpenAI integration and glow for output.
Handles prompt engineering, mods subprocess calls, and markdown rendering.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import RepositoryInfo

console = Console()


class AIProcessor:
    """Handles AI processing using mods and output rendering with glow."""
    
    def __init__(self, model: str = "gpt-4o", verbose: bool = False, check_deps: bool = True):
        self.model = model
        self.verbose = verbose
        self.mods_available = False
        self.glow_available = False
        
        if check_deps:
            self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required external tools are available."""
        missing_tools = []
        
        # Check for mods
        try:
            result = subprocess.run(['mods', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.mods_available = True
                if self.verbose:
                    console.print("[green]✅ mods CLI tool found[/green]")
            else:
                missing_tools.append('mods')
        except (subprocess.SubprocessError, FileNotFoundError):
            missing_tools.append('mods')
        
        # Check for glow
        try:
            result = subprocess.run(['glow', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.glow_available = True
                if self.verbose:
                    console.print("[green]✅ glow CLI tool found[/green]")
            else:
                missing_tools.append('glow')
        except (subprocess.SubprocessError, FileNotFoundError):
            missing_tools.append('glow')
        
        if missing_tools:
            console.print(Panel(
                f"[yellow]⚠️  Missing tools for full functionality: {', '.join(missing_tools)}[/yellow]\n\n"
                f"For complete experience, please install:\n"
                f"• mods: https://github.com/charmbracelet/mods\n"
                f"• glow: https://github.com/charmbracelet/glow\n\n"
                f"The tool will work in development mode without these tools.\n"
                f"Use --dry-run to test the complete pipeline.",
                title="Optional Dependencies Missing",
                border_style="yellow"
            ))
        else:
            if self.verbose:
                console.print("[green]✅ All required tools (mods, glow) are available[/green]")
    
    def create_explanation_prompt(self, repo_info: RepositoryInfo, question: str, 
                                content: str, tree: str, summary: str) -> str:
        """
        Create a well-structured prompt for repository explanation.
        
        Args:
            repo_info: Repository information
            question: User's question
            content: Repository content from gitingest
            tree: Repository file tree
            summary: Repository summary
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert software engineer helping someone understand a GitHub repository.

REPOSITORY INFORMATION:
- Name: {repo_info.full_name}
- URL: {repo_info.github_url}
- Description: {repo_info.description or 'No description available'}
- Primary Language: {repo_info.language or 'Unknown'}
- Stars: {repo_info.stars or 'Unknown'}

USER QUESTION: {question}

REPOSITORY STRUCTURE:
{tree}

REPOSITORY SUMMARY:
{summary}

REPOSITORY CONTENT:
{content}

INSTRUCTIONS:
1. Answer the user's question about this repository in detail
2. Use specific examples from the actual code when relevant
3. Explain concepts clearly for someone trying to understand or use this repository
4. If the question is about usage, provide practical examples
5. If the question is about architecture, explain the design patterns and structure
6. Format your response in clear, well-structured Markdown
7. Use code blocks with appropriate syntax highlighting when showing examples
8. Be thorough but concise - focus on what's most relevant to the question

Please provide a comprehensive explanation that directly addresses: "{question}"
"""
        
        if self.verbose:
            prompt_size = len(prompt.encode('utf-8'))
            console.print(f"[blue]📝 Generated prompt: {prompt_size} bytes[/blue]")
        
        return prompt
    
    def process_with_mods(self, prompt: str, dry_run: bool = False) -> Optional[str]:
        """
        Send prompt to OpenAI via mods and get response.
        
        Args:
            prompt: The formatted prompt to send
            dry_run: If True, don't make actual API call
            
        Returns:
            AI response string or None if dry_run/unavailable
        """
        if dry_run:
            console.print("[yellow]🎭 Dry run: Would send prompt to mods/OpenAI[/yellow]")
            console.print(f"[blue]Prompt size: {len(prompt)} chars[/blue]")
            return "# Mock AI Response\n\nThis is a mock response for dry-run mode.\n\nThe actual response would contain a detailed explanation of the repository based on the user's question."
        
        if not self.mods_available:
            console.print(Panel(
                "[red]❌ mods CLI tool not available[/red]\n\n"
                "Cannot process AI request without mods.\n"
                "Please install mods: https://github.com/charmbracelet/mods\n\n"
                "Or use --dry-run to test the pipeline without AI calls.",
                title="Missing mods",
                border_style="red"
            ))
            return None
        
        # Check if OpenAI API key is available
        if not os.getenv('OPENAI_API_KEY'):
            console.print(Panel(
                "[red]❌ OPENAI_API_KEY not found[/red]\n\n"
                "Mods requires an OpenAI API key to function.\n"
                "Please set OPENAI_API_KEY in your .env file or environment.",
                title="Missing OpenAI API Key",
                border_style="red"
            ))
            return None
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Sending request to OpenAI via mods...", total=None)
                
                # Use stdin instead of file to avoid path interpretation issues
                cmd = [
                    'mods',
                    '-a', 'openai',  # Explicitly specify OpenAI API
                    '-m', self.model,  # Use -m for model
                    '-f'  # Use -f for format (markdown)
                ]
                
                if self.verbose:
                    console.print(f"[blue]🤖 Running: {' '.join(cmd)}[/blue]")
                    console.print(f"[blue]📝 Prompt size: {len(prompt)} chars[/blue]")
                
                progress.update(task, description="Processing with AI...")
                
                # Pass the prompt via stdin instead of file
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                    env={**os.environ, 'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')}
                )
                
                if result.returncode != 0:
                    console.print(f"[red]❌ Mods error (exit {result.returncode}):[/red]")
                    console.print(f"[red]stderr: {result.stderr}[/red]")
                    if result.stdout:
                        console.print(f"[yellow]stdout: {result.stdout}[/yellow]")
                    return None
                
                progress.update(task, description="AI processing complete!")
                
                response = result.stdout.strip()
                if self.verbose:
                    response_size = len(response)
                    console.print(f"[green]✅ Received response: {response_size} chars[/green]")
                
                if not response:
                    console.print("[red]❌ Received empty response from mods[/red]")
                    return None
                
                return response
        
        except subprocess.TimeoutExpired:
            console.print("[red]❌ AI request timed out after 2 minutes[/red]")
            return None
        except Exception as e:
            console.print(f"[red]❌ Error calling mods: {str(e)}[/red]")
            if self.verbose:
                console.print_exception()
            return None
    
    def render_with_glow(self, markdown_content: str, dry_run: bool = False) -> bool:
        """
        Render markdown content using glow.
        
        Args:
            markdown_content: The markdown content to render
            dry_run: If True, don't actually render
            
        Returns:
            True if successful, False otherwise
        """
        if dry_run:
            console.print("[yellow]🎭 Dry run: Would render markdown with glow[/yellow]")
            console.print(f"[blue]Markdown size: {len(markdown_content)} chars[/blue]")
            return True
        
        if not self.glow_available:
            console.print(Panel(
                "[yellow]⚠️  glow CLI tool not available[/yellow]\n\n"
                "Displaying markdown directly in terminal.\n"
                "For beautiful rendering, install glow: https://github.com/charmbracelet/glow",
                title="Fallback Display",
                border_style="yellow"
            ))
            # Fallback: display markdown directly
            console.print("\n" + "="*80)
            console.print(markdown_content)
            console.print("="*80 + "\n")
            return True
        
        try:
            # Create temporary file for the markdown
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(markdown_content)
                md_file = f.name
            
            try:
                # Call glow to render the markdown
                cmd = ['glow', md_file]
                
                if self.verbose:
                    console.print(f"[blue]🌟 Rendering with glow: {md_file}[/blue]")
                
                # Use subprocess.run without capture_output so glow can display directly
                result = subprocess.run(cmd, timeout=30)
                
                return result.returncode == 0
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(md_file)
                except OSError:
                    pass
        
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Glow rendering timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error rendering with glow: {str(e)}[/red]")
            if self.verbose:
                console.print_exception()
            return False
    
    def process_repository_question(self, repo_info: RepositoryInfo, question: str,
                                  content_data: Dict, dry_run: bool = False) -> bool:
        """
        Complete AI processing pipeline: create prompt, call mods, render with glow.
        
        Args:
            repo_info: Repository information
            question: User's question
            content_data: Repository content from gitingest
            dry_run: If True, simulate the process without API calls
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the explanation prompt
            prompt = self.create_explanation_prompt(
                repo_info, question, 
                content_data['content'], 
                content_data['tree'], 
                content_data['summary']
            )
            
            # Process with mods (OpenAI)
            ai_response = self.process_with_mods(prompt, dry_run=dry_run)
            
            if ai_response:
                console.print(Panel(
                    "[green]✅ AI explanation generated successfully![/green]",
                    title="AI Processing Complete",
                    border_style="green"
                ))
                
                # Render with glow
                success = self.render_with_glow(ai_response, dry_run=dry_run)
                
                if success:
                    console.print(Panel(
                        "[green]🌟 Explanation rendered successfully![/green]\n"
                        f"Repository: {repo_info.full_name}\n"
                        f"Question: {question}",
                        title="Task Complete",
                        border_style="green"
                    ))
                    return True
                else:
                    console.print("[red]❌ Failed to render explanation[/red]")
                    return False
            
            elif dry_run:
                console.print(Panel(
                    "[blue]✅ Dry run complete - full pipeline tested![/blue]\n"
                    "Would have:\n"
                    "1. ✅ Created explanation prompt\n" 
                    "2. ✅ Sent to OpenAI via mods\n"
                    "3. ✅ Rendered response with glow",
                    title="Dry Run Summary",
                    border_style="blue"
                ))
                return True
            else:
                console.print("[red]❌ Failed to get AI response[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error in AI processing pipeline: {str(e)}[/red]")
            if self.verbose:
                console.print_exception()
            return False 