#!/usr/bin/env python3
"""
Flagsmith Infrastructure Challenger - Main CLI Application
Production-grade Kubernetes troubleshooting scenarios
"""

import argparse
import atexit
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from cli.challenges import Challenge
from cli.challenges import ChallengeManager

console = Console()


def handle_error(error: Exception) -> None:
    """Display error with confirmation message."""
    console.print()
    error_panel = Panel(
        f"[red bold]Error:[/red bold] {error!s}\n\n"
        f"[dim]Type: {type(error).__name__}[/dim]",
        title="❌ System Error",
        border_style="red",
        padding=(1, 2),
    )
    console.print(error_panel)
    console.print()
    console.print("[yellow]Press Enter to exit...[/yellow]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def get_safe_width(console: Console) -> int:
    """Get safe panel width that prevents border wrapping."""
    return console.size.width - 2


def create_panel(content: str, title: str = "", style: str = "blue", title_align: str = "left") -> Panel:
    """Create a consistent panel with standard styling."""
    return Panel(
        content,
        title=title,
        title_align=title_align,
        border_style=style,
        padding=(0, 1),
        width=get_safe_width(console),
    )


def create_tip_panel(message: str) -> Panel:
    """Create a tip panel with consistent yellow styling."""
    return Panel(
        f"[yellow]💡 Tip:[/yellow] {message}",
        border_style="yellow",
        padding=(0, 1),
        width=get_safe_width(console),
    )


class InterviewSession:
    """Manages interview session lifecycle and health monitoring."""

    def __init__(self, challenge_manager: ChallengeManager):
        self.challenge_manager = challenge_manager
        self.start_time: datetime | None = None
        self.current_challenge: Challenge | None = None
        self.session_active = False

    def start_session(self, challenge: Challenge) -> bool:
        """Start interview session with selected challenge."""
        self.current_challenge = challenge
        self.start_time = datetime.now()
        self.session_active = True

        # Display challenge info in panel
        panel_text = Text()
        panel_text.append(challenge.name, style="bold")
        panel_text.append("\n")
        panel_text.append(challenge.description)

        bronze_min = challenge.estimates["Lv1"]
        silver_min = challenge.estimates["Lv2"]
        gold_min = challenge.estimates["Lv3"]
        panel_text.append("\n")
        panel_text.append("Time Estimates: ", style="cyan")
        panel_text.append("🥉", style="dim")
        panel_text.append(str(bronze_min), style="red")
        panel_text.append("/", style="dim")
        panel_text.append(str(silver_min), style="white")
        panel_text.append("/", style="dim")
        panel_text.append("🥇", style="dim")
        panel_text.append(str(gold_min), style="yellow")
        panel_text.append("min", style="dim")

        challenge_panel = Panel(
            panel_text,
            title="Challenge",
            title_align="left",
            border_style="cyan",
            padding=(0, 1),
            width=get_safe_width(console),
        )
        console.print()
        console.print(challenge_panel)
        console.print()

        # Show reference to manual
        _ = challenge.manual  # Ensure manual exists, will raise if missing
        manual_filename = Path(challenge.filename).stem
        manual_reference = Panel(
            f"📖 Reviewer manual: [blue underline]challenges/{manual_filename}.md[/blue underline]",
            title_align="left",
            border_style="blue",
            padding=(0, 1),
            width=get_safe_width(console),
        )
        console.print(manual_reference)
        console.print()

        # Deploy challenge
        console.print("📦 [bold]Step 1:[/bold] Deploying challenge environment")
        self.challenge_manager.setup_challenge(challenge)

        # Start candidate environment
        console.print("🔗 [bold]Step 2:[/bold] Starting candidate session")
        self.challenge_manager.start_candidate_environment()

        if not self._setup_candidate_connection():
            console.print("[red]Connection setup failed[/red]")
            return False

        # Begin monitoring
        console.print("🏥 [bold]Step 3:[/bold] Monitoring active")
        self._start_health_monitoring()

        return True

    def _setup_candidate_connection(self) -> bool:
        """Setup and display candidate connection information."""
        max_retries = 2

        for retry in range(max_retries + 1):
            if retry > 0:
                console.print(f"Retry {retry}/{max_retries}")
                self.challenge_manager.start_candidate_environment()
                time.sleep(3)

            console.print("Initializing session...")

            for attempt in range(10):  # 10 second timeout
                is_ready, ssh_url, web_url = self.challenge_manager.get_tmate_info()

                if is_ready and ssh_url:
                    # Connection info panel
                    connection_info = f"[bold]SSH:[/bold] [cyan]{ssh_url}[/cyan]"
                    if web_url:
                        connection_info += f"\n[bold]Web:[/bold] [cyan]{web_url}[/cyan]"

                    instructions = (
                        "📋 [bold]Candidate instructions:[/bold]\n"
                        "  1. Connect using SSH command above\n"
                        "  2. Explore cluster with kubectl\n"
                        "  3. Debug and fix the deployment\n"
                        "  4. Verify health endpoint returns HTTP 200"
                    )

                    panel_content = f"{connection_info}\n\n{instructions}"
                    panel = create_panel(panel_content, "Session Ready", "blue")
                    console.print(panel)
                    return True

                # Check for session failure
                if self._check_session_failure():
                    break

                if attempt % 3 == 0 and attempt > 0:
                    console.print(f"Still initializing... ({attempt}s)")

                time.sleep(1)

            if retry < max_retries:
                console.print("[yellow]Session failed, retrying...[/yellow]")
            else:
                console.print("[red]Session initialization failed[/red]")

        return False

    def _check_session_failure(self) -> bool:
        """Check if session initialization failed."""
        status_file = Path("/tmp/tmate-info/status")
        if status_file.exists():
            status = status_file.read_text().strip()
            if status in ["failed", "timeout"]:
                console.print(f"[red]Session {status}[/red]")
                return True
        return False

    def _start_health_monitoring(self):
        """Start manual health monitoring with space bar."""
        console.print("Session active. [bold]Press ENTER to check health[/bold] (Ctrl+C to exit)")

        try:
            while self.session_active:
                user_input = input()
                if user_input.strip() == "":  # Enter pressed
                    console.print("[dim]Probing health endpoint...[/dim]")
                    self._check_health()
                else:
                    console.print("[yellow]Press ENTER to check health (Ctrl+C to exit)[/yellow]")
        except KeyboardInterrupt:
            pass

    def _check_health(self):
        """Perform health check and display result."""
        elapsed = self._format_elapsed_time()
        is_healthy, status_msg, _ = self.challenge_manager.check_health()
        console.print(f"{elapsed} | {status_msg.strip()}")

        if is_healthy:
            success_panel = Panel(
                "[green]Challenge completed successfully!\n"
                "Health endpoint is responding correctly.\n\n"
                "[yellow]Press Ctrl+C to exit[/yellow]",
                title="Success",
                title_align="center",
                border_style="green",
                padding=(0, 1),
                width=get_safe_width(console),
            )
            console.print(success_panel)
        else:
            console.print("[bold]Press ENTER to check again[/bold] (Ctrl+C to exit)")

    def _format_elapsed_time(self) -> str:
        """Format session elapsed time."""
        assert self.start_time is not None, "start_time must be set when session is active"
        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}".strip()

    def stop_session(self):
        """Clean up session and exit."""
        if not self.session_active:
            return

        console.print("\nEnding session...")
        self.session_active = False

        # Clean up resources
        self.challenge_manager.cleanup()

        elapsed = self._format_elapsed_time()
        console.print(f"Session duration: [bold]{elapsed}[/bold]")
        console.print("Environment cleaned up")

        self.current_challenge = None
        self.start_time = None


class InterviewCLI:
    """Main CLI application."""

    def __init__(self):
        self.challenge_manager = ChallengeManager()
        self.session = InterviewSession(self.challenge_manager)

        # Setup cleanup handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        atexit.register(self._cleanup)

    def _handle_exit(self, signum, frame):
        """Handle exit signals gracefully."""
        if self.session.session_active:
            self.session.stop_session()

        console.print("\n👋 [bold]Goodbye[/bold]")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Perform final cleanup."""
        try:
            self.challenge_manager._force_cleanup_containers()
        except Exception:
            pass

    def run(self):
        """Run the CLI application."""
        self._show_banner()

        # Load challenges
        self.challenge_manager.discover_challenges()

        if not self.challenge_manager.challenges:
            console.print("[red]No challenges found[/red]")
            return

        # Select challenge
        if not (challenge := self._select_challenge()):
            return

        self._run_challenge(challenge)

    def run_specific_challenge(self, challenge_id: str) -> None:
        """Run a specific challenge by its filename (e.g., 'database-typo')."""
        self._show_banner()

        # Load challenges
        self.challenge_manager.discover_challenges()

        if not self.challenge_manager.challenges:
            console.print("[red]No challenges found[/red]")
            console.print("Add .yaml files to the challenges/ directory")
            return

        # Find challenge by filename prefix
        if not (challenge := self._find_challenge(challenge_id)):
            console.print(f"[red]Challenge '{challenge_id}' not found[/red]")
            self._list_available_challenges()
            return

        console.print(f"[bold]Running challenge:[/bold] {challenge.name}")
        console.print()

        self._run_challenge(challenge)

    def _find_challenge(self, challenge_id: str) -> Challenge | None:
        """Find challenge by matching its filename."""
        for challenge in self.challenge_manager.challenges:
            if Path(challenge.filename).stem == challenge_id:
                return challenge
        return None

    def _list_available_challenges(self):
        """List available challenges for error messages."""
        console.print("\n[bold]Available challenges:[/bold]")
        for challenge in self.challenge_manager.challenges:
            console.print(f"  {Path(challenge.filename).stem}: {challenge.name}")
        console.print()

    def _show_banner(self):
        """Display application banner."""
        banner_content = Text()
        banner_content.append("Flagsmith Infrastructure Challenger", style="bold blue")
        banner_content.append("\n")
        banner_content.append("Production-grade Kubernetes troubleshooting scenarios", style="dim")

        banner = Panel(
            banner_content,
            border_style="blue",
            padding=(0, 1),
            width=get_safe_width(console),
        )
        console.print()
        console.print(banner)
        console.print()

    def _select_challenge(self) -> Challenge | None:
        """Display challenges and get user selection."""
        console.print(f"[bold]Available challenges[/bold] ({len(self.challenge_manager.challenges)} found)")
        console.print()

        # List challenges
        from textwrap import fill

        for i, challenge in enumerate(self.challenge_manager.challenges, 1):
            # Challenge title
            title = Text()
            title.append(f"  {i}. ", style="bold")
            title.append(challenge.name, style="cyan")
            # Show time estimates
            bronze_min = challenge.estimates["Lv1"]
            silver_min = challenge.estimates["Lv2"]
            gold_min = challenge.estimates["Lv3"]
            title.append(" (", style="dim")
            title.append(str(bronze_min), style="red")
            title.append("/", style="dim")
            title.append(str(silver_min), style="white")
            title.append("/", style="dim")
            title.append(str(gold_min), style="yellow")
            title.append("min)", style="dim")
            console.print(title)

            # Description with proper wrapping
            wrapped_desc = fill(
                challenge.description,
                width=70,
                initial_indent="     ",
                subsequent_indent="     ",
            )
            console.print(wrapped_desc, style="dim")
            console.print()

        # Exit tip
        tip = create_tip_panel("Press [bold]Ctrl+C[/bold] anytime to exit")
        console.print(tip)
        console.print()

        # Get selection
        while True:
            try:
                choice = Prompt.ask("Select challenge number")
            except (EOFError, KeyboardInterrupt):
                return None

            if not choice.isdigit():
                console.print("[red]Enter a number[/red]")
                continue

            num = int(choice)
            if not (1 <= num <= len(self.challenge_manager.challenges)):
                console.print(f"[red]Enter 1-{len(self.challenge_manager.challenges)}[/red]")
                continue

            return self.challenge_manager.get_challenge(num - 1)



    def _run_challenge(self, challenge: Challenge) -> None:
        """Execute selected challenge."""
        # Run session
        if self.session.start_session(challenge):
            # Wait for completion or interruption
            while self.session.session_active:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    break


def setup_kubeconfig() -> None:
    """Simple kubeconfig setup - k3s is already healthy via docker-compose."""
    import shutil

    kube_dir = Path("/root/.kube")
    kube_dir.mkdir(exist_ok=True, parents=True)

    # K3s writes to this location via K3S_KUBECONFIG_OUTPUT
    source = Path("/root/.kube/kubeconfig.yaml")  # from kubeconfig-data volume
    target = Path("/root/.kube/config")

    if not source.exists():
        # Fallback to direct k3s location
        source = Path("/etc/rancher/k3s/k3s.yaml")

    if not source.exists():
        raise FileNotFoundError("Kubeconfig not found in expected locations")

    shutil.copy2(source, target)

    # Fix server URL for container networking
    content = target.read_text()
    content = content.replace('127.0.0.1:6443', 'k3s-server:6443')
    content = content.replace('localhost:6443', 'k3s-server:6443')
    target.write_text(content)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Flagsmith Infrastructure Challenger')
    parser.add_argument(
        '--challenges-dir',
        default='/app/challenges',
        help='Challenges directory path',
    )
    parser.add_argument(
        '--challenge',
        help='Run specific challenge by name (e.g., "database-typo")',
    )

    args = parser.parse_args()

    # Setup kubeconfig (k3s is already healthy via docker-compose)
    try:
        setup_kubeconfig()
    except Exception as e:
        console.print(f"[red]Failed to setup kubeconfig: {e}[/red]")
        sys.exit(1)

    # Run application with top-level exception handler
    try:
        cli = InterviewCLI()
        cli.challenge_manager.challenges_dir = Path(args.challenges_dir)

        if args.challenge:
            cli.run_specific_challenge(args.challenge)
        else:
            cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        handle_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
