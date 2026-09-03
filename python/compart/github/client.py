"""GitHub API Client & Authentication for Compart App."""

import base64
import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request


def verify_webhook_signature(payload: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify HMAC-SHA256 signature from GitHub webhook (X-Hub-Signature-256)."""
    if not signature_header or not secret:
        return False
    
    if not signature_header.startswith("sha256="):
        return False
    
    expected_hash = signature_header[7:]
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), expected_hash)


class GitHubAppClient:
    """Client for GitHub REST API, supporting Personal Access Tokens and GitHub Apps."""

    def __init__(
        self,
        token: Optional[str] = None,
        app_id: Optional[str] = None,
        private_key: Optional[str] = None,
        api_base_url: str = "https://api.github.com",
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("COMPART_GITHUB_TOKEN")
        self.app_id = app_id or os.environ.get("COMPART_GITHUB_APP_ID")
        self.private_key = private_key or os.environ.get("COMPART_GITHUB_PRIVATE_KEY")
        self.api_base_url = api_base_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Compart-Autonomous-Maintenance/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send authenticated HTTP request to GitHub REST API."""
        url = f"{self.api_base_url}/{path.lstrip('/')}"
        payload_bytes = json.dumps(data).encode("utf-8") if data is not None else None

        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers=self._headers(),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                if body:
                    return json.loads(body)
                return {"status": status, "success": True}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            return {
                "error": f"HTTP {e.code}: {e.reason}",
                "status": e.code,
                "details": err_body,
                "success": False,
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
            }

    def get_repo(self, repo: str) -> Dict[str, Any]:
        """Get repository details."""
        return self._request("GET", f"repos/{repo}")

    def get_branch_ref(self, repo: str, branch: str) -> Dict[str, Any]:
        """Get git reference for a branch."""
        return self._request("GET", f"repos/{repo}/git/ref/heads/{branch}")

    def create_branch(self, repo: str, base_branch: str, new_branch: str) -> Dict[str, Any]:
        """Create a new git branch from base_branch."""
        ref_info = self.get_branch_ref(repo, base_branch)
        if not ref_info.get("object", {}).get("sha"):
            return {"error": f"Base branch {base_branch} not found", "success": False}
        
        sha = ref_info["object"]["sha"]
        data = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha,
        }
        return self._request("POST", f"repos/{repo}/git/refs", data=data)

    def create_or_update_file(
        self,
        repo: str,
        branch: str,
        path: str,
        content: str,
        commit_message: str,
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Commit a file change to a branch."""
        data = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            data["sha"] = sha
        return self._request("PUT", f"repos/{repo}/contents/{path}", data=data)

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a Pull Request and optionally attach labels."""
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "maintainer_can_modify": True,
        }
        res = self._request("POST", f"repos/{repo}/pulls", data=data)
        
        if res.get("number") and labels:
            pr_num = res["number"]
            self._request("POST", f"repos/{repo}/issues/{pr_num}/labels", data={"labels": labels})
            
        return res

    def set_commit_status(
        self,
        repo: str,
        sha: str,
        state: str,
        context: str = "compart/verification",
        description: str = "Compart zero-blast-radius verified",
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set commit status check (pending, success, error, failure)."""
        data = {
            "state": state,
            "context": context,
            "description": description,
        }
        if target_url:
            data["target_url"] = target_url
        return self._request("POST", f"repos/{repo}/statuses/{sha}", data=data)
