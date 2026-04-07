"""
Netlify deployment script for dashboard auto-update pipeline
Deploys the output/ folder to Netlify using the Netlify API
"""

import os
import logging
import json
from pathlib import Path
from typing import Optional
import subprocess
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NetlifyDeployer:
    """Handles deployment to Netlify"""

    def __init__(self):
        self.auth_token = os.environ.get("NETLIFY_AUTH_TOKEN")
        self.site_id = os.environ.get("NETLIFY_SITE_ID")
        self.api_base = "https://api.netlify.com/api/v1"
        self.output_dir = "output"

        if not self.auth_token:
            raise ValueError("NETLIFY_AUTH_TOKEN environment variable not set")
        if not self.site_id:
            raise ValueError("NETLIFY_SITE_ID environment variable not set")

    def _get_headers(self) -> dict:
        """Get authorization headers for Netlify API"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def deploy_using_cli(self) -> Optional[str]:
        """Deploy using netlify-cli (preferred method)"""
        try:
            logger.info("Deploying using netlify-cli...")

            # Check if netlify-cli is installed
            subprocess.run(["netlify", "--version"], check=True, capture_output=True)

            # Deploy using CLI
            result = subprocess.run(
                [
                    "netlify",
                    "deploy",
                    "--site",
                    self.site_id,
                    "--auth",
                    self.auth_token,
                    "--prod",
                    "--dir",
                    self.output_dir,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Netlify CLI output:\n{result.stdout}")

            # Extract the deploy URL from the output
            for line in result.stdout.split("\n"):
                if "https://" in line and "netlify" in line:
                    url = line.strip()
                    if url.startswith("https://"):
                        return url

            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"netlify-cli deployment failed: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.warning("netlify-cli not found, will attempt API deployment")
            return None

    def deploy_using_api(self) -> Optional[str]:
        """Deploy using Netlify API (direct method)"""
        try:
            logger.info("Deploying using Netlify API...")

            if not os.path.exists(self.output_dir):
                raise FileNotFoundError(f"Output directory not found: {self.output_dir}")

            # Create a zip file of the output directory
            zip_path = self._create_deployment_zip()

            # Upload to Netlify
            deploy_url = self._upload_to_netlify(zip_path)

            # Clean up zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)

            return deploy_url

        except Exception as e:
            logger.error(f"API deployment failed: {e}")
            return None

    def _create_deployment_zip(self) -> str:
        """Create a zip file of the output directory"""
        import shutil

        zip_path = "dashboard-deploy.zip"

        try:
            shutil.make_archive(
                "dashboard-deploy",
                "zip",
                self.output_dir,
            )
            logger.info(f"Created deployment zip: {zip_path}")
            return zip_path
        except Exception as e:
            logger.error(f"Failed to create zip file: {e}")
            raise

    def _upload_to_netlify(self, zip_path: str) -> Optional[str]:
        """Upload zip file to Netlify"""
        try:
            # Get existing deploy info
            site_url = f"{self.api_base}/sites/{self.site_id}"
            site_resp = requests.get(site_url, headers=self._get_headers())
            site_resp.raise_for_status()

            # Create a new deploy
            deploy_url = f"{self.api_base}/sites/{self.site_id}/deploys"

            with open(zip_path, "rb") as f:
                files = {"file": f}
                headers = {"Authorization": f"Bearer {self.auth_token}"}

                deploy_resp = requests.post(deploy_url, files=files, headers=headers)
                deploy_resp.raise_for_status()

            deploy_data = deploy_resp.json()
            deploy_id = deploy_data.get("id")

            logger.info(f"Deploy created with ID: {deploy_id}")

            # Poll for deployment completion
            return self._wait_for_deploy(deploy_id)

        except requests.exceptions.RequestException as e:
            logger.error(f"Netlify API request failed: {e}")
            raise

    def _wait_for_deploy(self, deploy_id: str, max_attempts: int = 30) -> Optional[str]:
        """Wait for deployment to complete"""
        import time

        headers = self._get_headers()
        deploy_url = f"{self.api_base}/sites/{self.site_id}/deploys/{deploy_id}"

        for attempt in range(max_attempts):
            try:
                resp = requests.get(deploy_url, headers=headers)
                resp.raise_for_status()
                deploy_data = resp.json()
                state = deploy_data.get("state", "building")

                logger.info(f"Deploy state: {state}")

                if state == "ready":
                    url = deploy_data.get("ssl_url") or deploy_data.get("url")
                    logger.info(f"Deploy ready at: {url}")
                    return url

                elif state == "error":
                    error_msg = deploy_data.get("error_message", "Unknown error")
                    logger.error(f"Deploy failed: {error_msg}")
                    return None

                # Wait before next check
                if attempt < max_attempts - 1:
                    time.sleep(2)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking deploy status: {e}")
                return None

        logger.error("Deploy timeout - exceeded maximum wait time")
        return None

    def deploy(self) -> bool:
        """Execute deployment to Netlify"""
        logger.info("Starting Netlify deployment...")

        # Try CLI first, fall back to API
        deploy_url = self.deploy_using_cli()

        if not deploy_url:
            logger.info("CLI deployment did not return URL, trying API...")
            deploy_url = self.deploy_using_api()

        if deploy_url:
            logger.info(f"Deployment successful! URL: {deploy_url}")
            return True
        else:
            logger.error("Deployment failed")
            return False


def main():
    """Main entry point"""
    try:
        deployer = NetlifyDeployer()
        success = deployer.deploy()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
