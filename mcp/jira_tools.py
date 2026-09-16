"""
jira_tools.py — MCP tools for Jira integration
"""
import json
import httpx
import logging
from typing import Optional

from mcp_config import JIRA_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN
from database import upsert_memory, add_memory_link
from logger import logger

# Setup logging
logger.info("Initializing Jira tools...")

def register_jira_tools(mcp):
    """Register Jira-specific tools onto the FastMCP instance."""

    @mcp.tool()
    def sync_jira_issue(issue_id: str, api_key: str = "") -> str:
        """
        Fetches data for a specific Jira issue and upserts it into the Project Memory 'Jira' domain.
        """
        # Note: Jira tools are internal to the MCP server, but we still check auth
        # if the tool is being called via a route that passes the api_key.
        # For now, we assume the MCP server has the authority to sync.

        if not JIRA_URL or not JIRA_API_TOKEN:
            return "Error: Jira configuration missing in .env"

        try:
            # Jira API uses Basic Auth (Email:Token)
            with httpx.Client(auth=(JIRA_USER_EMAIL, JIRA_API_TOKEN)) as client:
                url = f"{JIRA_URL}/rest/api/3/issue/{issue_id}"
                response = client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()

            # Extract relevant fields
            fields = data.get("fields", {})
            summary = fields.get("summary", "No Summary")
            description = fields.get("description", "No Description")
            # Jira description is a complex object (ADF), we just take the raw text or a summary for now
            if isinstance(description, dict):
                description = "Detailed description available in Jira ticket."

            status = fields.get("status", {}).get("name", "Unknown")
            priority = fields.get("priority", {}).get("name", "Unknown")
            assignee = fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned"
            labels = fields.get("labels", [])

            # Build the memory value
            value = f"Issue: {summary}\nStatus: {status}\nPriority: {priority}\nAssignee: {assignee}\n\nDescription: {description}"

            # Metadata for structured tracking
            metadata = {
                "status": status,
                "priority": priority,
                "assignee": assignee,
                "url": f"{JIRA_URL}/browse/{issue_id}"
            }

            # Upsert into 'Jira' domain
            action = upsert_memory(
                domain="Jira",
                concept=issue_id,
                value=value,
                tag_list=labels,
                exp=None,
                metadata=metadata
            )

            return f"{action.capitalize()} Jira issue {issue_id} into project memory."

        except httpx.HTTPStatusError as e:
            logger.error(f"Jira API error for {issue_id}: {e.response.text}")
            return f"Error: Could not fetch Jira issue {issue_id}. {e.response.status_code}"
        except Exception as e:
            logger.error(f"Unexpected error syncing Jira issue {issue_id}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    def link_to_jira(domain: str, concept: str, issue_id: str, api_key: str = "") -> str:
        """
        Syncs a Jira issue and then creates a link between a project memory and that ticket.
        """
        # 1. First sync the Jira issue to ensure it exists in the 'Jira' domain
        sync_result = sync_jira_issue(issue_id)
        if "Error" in sync_result:
            return sync_result

        # 2. Create the relational link
        try:
            success = add_memory_link(domain, concept, "Jira", issue_id)
            if success:
                return f"Successfully linked '{concept}' in '{domain}' to Jira issue {issue_id}."
            else:
                return f"Link already exists between '{concept}' and {issue_id}."
        except ValueError as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def search_jira(query: str, api_key: str = "") -> str:
        """
        Searches for Jira issues based on a query and returns matching Issue Keys and summaries.
        """
        if not JIRA_URL or not JIRA_API_TOKEN:
            return "Error: Jira configuration missing in .env"

        try:
            with httpx.Client(auth=(JIRA_USER_EMAIL, JIRA_API_TOKEN)) as client:
                # Use JQL search
                url = f"{JIRA_URL}/rest/api/3/search"
                params = {"jql": f"text ~ '{query}'", "maxResults": 10}
                response = client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

            issues = data.get("issues", [])
            if not issues:
                return f"No Jira issues found matching '{query}'."

            results = []
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "No Summary")
                results.append(f"[{key}] {summary}")

            return "Matching Jira issues:\n" + "\n".join(results)

        except Exception as e:
            logger.error(f"Error searching Jira: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    def list_jira_issues(project_key: str, api_key: str = "") -> str:
        """
        Lists all issues for a given Jira project.
        """
        if not JIRA_URL or not JIRA_API_TOKEN:
            return "Error: Jira configuration missing in .env"

        try:
            with httpx.Client(auth=(JIRA_USER_EMAIL, JIRA_API_TOKEN)) as client:
                url = f"{JIRA_URL}/rest/api/3/search"
                params = {"jql": f"project = '{project_key}'", "maxResults": 50}
                response = client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

            issues = data.get("issues", [])
            if not issues:
                return f"No issues found for project {project_key}."

            results = []
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "No Summary")
                results.append(f"[{key}] {summary}")

            return f"Issues in project {project_key}:\n" + "\n".join(results)

        except Exception as e:
            logger.error(f"Error listing Jira issues: {e}")
            return f"Error: {str(e)}"
