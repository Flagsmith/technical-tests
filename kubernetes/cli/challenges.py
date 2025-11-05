"""
Challenge discovery and management system.

Automatically discovers challenges from patch files in the challenges/ directory
and provides functionality to apply patches, manage deployments, and run health checks.
"""

import atexit
import json
import os
import shlex
import signal
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import requests
import yaml
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ConnectTimeout
from requests.exceptions import RequestException
from requests.exceptions import Timeout


class Challenge:
    """Represents a single challenge with metadata, helm values, and kubectl patches."""

    def __init__(
        self,
        filename: str,
        name: str,
        description: str,
        helm_values: dict[str, Any],
        kubectl_patches: list[dict[str, Any]],
        estimates: dict[str, str],
        challenge_dir: Path,
    ):
        self.filename = filename
        self.name = name
        self.description = description
        self.helm_values = helm_values
        self.kubectl_patches = kubectl_patches
        self.estimates = estimates
        self.challenge_dir = challenge_dir
        self._manual: str | None = None

    @property
    def manual(self) -> str:
        """Load and cache the manual for this challenge.

        Every challenge requires a corresponding .md manual file.
        The file path is constructed from the YAML filename.
        """
        if self._manual is not None:
            return self._manual

        manual_filename = self.filename.replace('.yaml', '.md')
        manual_path = self.challenge_dir / manual_filename

        self._manual = manual_path.read_text()
        return self._manual

    def __str__(self) -> str:
        return f"{self.name}"


class ChallengeManager:
    """Manages challenge discovery, deployment, and health checking."""

    def __init__(self, challenges_dir: str = "/app/challenges"):
        self.challenges_dir = Path(challenges_dir)
        self.challenges: list[Challenge] = []
        self.current_challenge: Challenge | None = None
        self.flagsmith_namespace = "flagsmith"
        self.helm_release_name = "flagsmith"
        # Generate unique container name using UUID hash
        unique_id = str(uuid.uuid4())[:12]
        self.candidate_container_name = f"k8s_challenger-candidate-env-{unique_id}"

        # Register cleanup on exit and signals
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_cleanup)
        signal.signal(signal.SIGTERM, self._signal_cleanup)

    def _run_command(self, cmd: str, check: bool = True, verbose: bool = False) -> subprocess.CompletedProcess:
        """
        Run shell command with consistent interface.

        Args:
            cmd: Command to run
            check: Whether to raise on non-zero exit
            verbose: Whether to show output in real-time

        Returns:
            CompletedProcess result
        """
        return subprocess.run(
            shlex.split(cmd),
            check=check,
            text=True,
            capture_output=not verbose,
        )

    def _signal_cleanup(self, signum, frame):
        """Handle cleanup on signal."""
        self._cleanup()

    def _cleanup(self):
        """Clean up project Docker resources."""
        self._run_command("docker-compose down --volumes --remove-orphans", check=False)
        # Also clean up any dynamically created candidate containers
        self._force_cleanup_containers()

    def _force_cleanup_containers(self):
        """Force cleanup of any remaining candidate containers."""
        try:
            # Find and remove any candidate containers (including uniquely named ones)
            cmd = 'docker ps -a --filter "name=k8s_challenger-candidate-env" --format "{{.ID}}"'
            result = self._run_command(cmd, check=False)
            if result.returncode == 0 and result.stdout.strip():
                container_ids = result.stdout.strip().split('\n')
                for container_id in container_ids:
                    if container_id.strip():
                        self._run_command(f"docker rm -f {container_id.strip()}", check=False)
        except Exception:
            # Don't fail cleanup due to container cleanup issues
            pass

    def discover_challenges(self) -> None:
        """Automatically discover challenges from patch files."""
        self.challenges = []

        if not self.challenges_dir.exists():
            return

        yaml_files = sorted(self.challenges_dir.glob("*.yaml"))

        for yaml_file in yaml_files:
            try:
                challenge = self._parse_challenge_file(yaml_file)
                if challenge:
                    self.challenges.append(challenge)
            except Exception:
                pass

    def _parse_challenge_file(self, filepath: Path) -> Challenge | None:
        """Parse a YAML challenge file and extract metadata.

        Challenge YAML files must include all required fields:
        name, description, helm_values, kubectl_patches, estimates.
        """
        try:
            data = yaml.safe_load(filepath.read_text())
        except (yaml.YAMLError, OSError):
            return None

        # Validate all required fields
        required_fields = ['name', 'description', 'helm_values', 'kubectl_patches', 'estimates']
        if not isinstance(data, dict) or not all(field in data for field in required_fields):
            return None

        return Challenge(
            filename=filepath.name,
            name=data['name'],
            description=data['description'],
            helm_values=data['helm_values'],
            kubectl_patches=data['kubectl_patches'],
            estimates=data['estimates'],
            challenge_dir=filepath.parent,
        )

    def list_challenges(self) -> list[Challenge]:
        """Return list of available challenges."""
        return self.challenges

    def get_challenge(self, index: int) -> Challenge | None:
        """Get challenge by index."""
        if 0 <= index < len(self.challenges):
            return self.challenges[index]
        return None

    def setup_challenge(self, challenge: Challenge) -> bool:
        """Set up a challenge by applying its patch to the Flagsmith deployment."""
        self.current_challenge = challenge

        try:
            # Cleanup before starting
            self._cleanup()

            # Wait for cleanup to complete
            time.sleep(2)

            # Create namespace
            self._run_command(f"kubectl create namespace {self.flagsmith_namespace}", check=False, verbose=True)

            # Clone Flagsmith charts if not exists
            if not Path("/tmp/flagsmith-charts").exists():
                self._run_command(
                    "git clone https://github.com/Flagsmith/flagsmith-charts.git /tmp/flagsmith-charts",
                    verbose=True,
                )

            # Prepare values file
            values_file = "/tmp/flagsmith-values.yaml"

            if challenge.helm_values:
                # Use custom values from challenge
                Path(values_file).write_text(yaml.dump(challenge.helm_values))
            else:
                # Use original values
                original_values = "/tmp/flagsmith-charts/charts/flagsmith/values.yaml"
                self._run_command(f"cp {original_values} {values_file}", check=True)

            # Add Flagsmith Helm repo
            self._run_command(
                "helm repo add flagsmith https://flagsmith.github.io/flagsmith-charts/",
                check=False,
                verbose=True,
            )
            # Add common dependency repos used by the chart
            self._run_command(
                "helm repo add bitnami https://charts.bitnami.com/bitnami",
                check=False,
                verbose=True,
            )
            self._run_command(
                "helm repo add influxdata https://helm.influxdata.com/",
                check=False,
                verbose=True,
            )
            self._run_command(
                "helm repo add kiwigrid https://kiwigrid.github.io/helm-charts/",
                check=False,
                verbose=True,
            )
            self._run_command("helm repo update", check=False, verbose=True)

            # Optionally build local chart dependencies (not required when using remote chart)
            self._run_command(
                "helm dependency build /tmp/flagsmith-charts/charts/flagsmith",
                check=False,
                verbose=True,
            )

            # Deploy using Helm (no --wait to allow broken deployments)
            helm_cmd = (
                f"helm upgrade --install {self.helm_release_name} flagsmith/flagsmith "
                f"-f {values_file} -n {self.flagsmith_namespace} --create-namespace"
            )

            self._run_command(helm_cmd, check=True, verbose=True)

            # Apply kubectl patches after successful helm deployment
            if challenge.kubectl_patches:
                self._apply_kubectl_patches(challenge.kubectl_patches)

            return True

        except Exception:
            return False

    def _apply_kubectl_patches(self, patches: list[dict[str, Any]]) -> None:
        """Apply kubectl patches after helm deployment."""
        for patch in patches:
            try:
                resource = patch.get('resource')
                name = patch.get('name')
                namespace = patch.get('namespace', self.flagsmith_namespace)
                patch_data = patch.get('patch', {})
                patch_type = patch.get('patch_type', 'merge')  # Default to merge

                if not resource or not name or not patch_data:
                    continue

                # Convert patch data to JSON
                patch_json = json.dumps(patch_data)

                kubectl_cmd = (
                    f"kubectl patch {resource} {name} -n {namespace} "
                    f"--type {patch_type} -p '{patch_json}'"
                )

                self._run_command(kubectl_cmd, check=True, verbose=True)

            except Exception as e:
                # Continue with other patches even if one fails
                print(f"Warning: Failed to apply patch to {resource}/{name}: {e}")
                continue

    def _cleanup_deployment(self) -> None:
        """Clean up existing Flagsmith deployment."""
        # Cleanup handles everything
        self._cleanup()



    def check_health(self) -> tuple[bool, str, int | None]:
        """
        Check if Flagsmith is healthy using kubectl port-forward.

        Returns:
            Tuple of (is_healthy, status_message, http_status_code)
        """
        try:
            # First check if API service exists
            result = self._run_command(
                f"kubectl get service {self.helm_release_name}-api -n {self.flagsmith_namespace}",
                check=False,
            )

            if result.returncode != 0:
                return False, "Service not deployed", None

            # Use kubectl port-forward to create a reliable connection
            local_port = 8080
            port_forward_cmd = f"kubectl port-forward svc/{self.helm_release_name}-api {local_port}:8000 -n {self.flagsmith_namespace}"

            # Start port-forward in background
            port_forward_proc = subprocess.Popen(
                shlex.split(port_forward_cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            try:
                # Give port-forward time to establish
                time.sleep(2)

                # Check if port-forward is still running
                if port_forward_proc.poll() is not None:
                    return False, "Port-forward failed", None

                # Make health check request to localhost
                health_url = f"http://localhost:{local_port}/health/liveness/"
                response = requests.get(health_url, timeout=5)

                is_healthy = response.status_code == 200

                if is_healthy:
                    return True, "Healthy", response.status_code
                elif response.status_code == 404:
                    return False, "Endpoint not found", response.status_code
                elif response.status_code == 500:
                    return False, "Server error", response.status_code
                elif response.status_code == 503:
                    return False, "Service unavailable", response.status_code
                else:
                    return False, f"HTTP {response.status_code}", response.status_code

            finally:
                # Always clean up port-forward process
                try:
                    port_forward_proc.terminate()
                    port_forward_proc.wait(timeout=5)
                except Exception:
                    try:
                        port_forward_proc.kill()
                    except Exception:
                        pass

        except ConnectTimeout:
            return False, "Connection timeout", None
        except RequestsConnectionError:
            return False, "Cannot connect to service", None
        except Timeout:
            return False, "Request timeout", None
        except RequestException:
            return False, "Network error", None
        except Exception:
            return False, "Health check failed", None

    def get_flagsmith_info(self) -> dict[str, Any]:
        """Get information about the current Flagsmith deployment."""
        try:
            # Get pods
            pods_result = self._run_command(f"kubectl get pods -n {self.flagsmith_namespace} -o json")

            info: dict[str, Any] = {
                "namespace": self.flagsmith_namespace,
                "release": self.helm_release_name,
                "pods": [],
                "services": [],
            }

            if pods_result.returncode == 0:
                pods_data: Any = json.loads(pods_result.stdout)
                if isinstance(pods_data, dict):
                    items: Any = pods_data.get("items", [])
                    if isinstance(items, list):
                        for pod in items:
                            info["pods"].append({
                                "name": pod["metadata"]["name"],
                                "status": pod["status"]["phase"],
                                "ready": self._is_pod_ready(pod),
                            })

            # Get services
            services_result = self._run_command(f"kubectl get services -n {self.flagsmith_namespace} -o json")

            if services_result.returncode == 0:
                services_data: Any = json.loads(services_result.stdout)
                if isinstance(services_data, dict):
                    items = services_data.get("items", [])
                    if isinstance(items, list):
                        for svc in items:
                            info["services"].append({
                                "name": svc["metadata"]["name"],
                                "type": svc["spec"]["type"],
                                "ports": svc["spec"]["ports"],
                            })

            return info

        except Exception as e:
            return {"error": str(e)}

    def _is_pod_ready(self, pod: dict[str, Any]) -> bool:
        """Check if a pod is ready."""
        conditions = pod.get("status", {}).get("conditions", [])
        for condition in conditions:
            if condition.get("type") == "Ready":
                return condition.get("status") == "True"
        return False

    def get_tmate_info(self) -> tuple[bool, str | None, str | None]:
        """
        Get tmate connection information from candidate environment.

        Returns:
            Tuple of (is_ready, ssh_url, web_url)
        """
        try:
            status_file = Path("/tmp/tmate-info/status")
            ssh_file = Path("/tmp/tmate-info/ssh")
            web_file = Path("/tmp/tmate-info/web")

            if not status_file.exists():
                return False, None, None

            status = status_file.read_text().strip()
            if status != "ready":
                return False, None, None

            ssh_url = ssh_file.read_text().strip() if ssh_file.exists() else None
            web_url = web_file.read_text().strip() if web_file.exists() else None

            return True, ssh_url, web_url

        except Exception:
            return False, None, None

    def start_candidate_environment(self) -> None:
        """Start a new candidate environment container for debugging."""
        # Cleanup first
        self._cleanup()
        time.sleep(2)

        # Get network name from existing k3s container
        k3s_inspect = self._run_command(
            'docker inspect k8s_challenger-k3s-1 --format "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}"',
            check=False,
        )
        network_id = k3s_inspect.stdout.strip() if k3s_inspect.returncode == 0 else "k8s_challenger_flagsmith-network"

        # Start fresh candidate environment container with auto-remove on stop
        docker_cmd = (
            f"docker run -d --name {self.candidate_container_name} --network {network_id} "
            f"--user root --rm -v k8s_challenger_k3s-server:/etc/rancher/k3s:ro "
            f"-v k8s_challenger_kubeconfig-data:/home/candidate/.kube-shared:ro "
            f"-v k8s_challenger_tmate-info:/tmp/tmate-info "
            f"--env KUBECONFIG=/home/candidate/.kube/config k8s_challenger-candidate-env"
        )

        self._run_command(docker_cmd, check=True)

    def stop_candidate_environment(self) -> None:
        """Stop and remove the candidate environment container for cleanup."""
        self._cleanup()

    def _cleanup_tmate_info(self) -> None:
        """Clean up tmate info files safely."""
        try:
            tmate_info_dir = Path("/tmp/tmate-info")
            if tmate_info_dir.exists():
                # Remove files individually instead of entire directory to avoid resource busy
                for file_path in tmate_info_dir.glob("*"):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass  # Ignore individual file removal errors
                # Try to remove directory, but don't fail if it's busy
                try:
                    tmate_info_dir.rmdir()
                except OSError:
                    pass  # Directory might still be in use by volume mount
        except Exception:
            pass  # Don't fail cleanup due to minor issues

    def cleanup(self) -> None:
        """Clean up current challenge deployment and candidate environment."""
        # Cleanup handles everything
        self._cleanup()
        self.current_challenge = None
