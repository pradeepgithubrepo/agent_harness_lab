"""Synthetic, non-executing routing evaluation requests."""

from .models import RoutingCase


ROUTING_CASES: tuple[RoutingCase, ...] = (
    RoutingCase(request_id="lookup-001", category="simple_lookup", request="Get the current status for job job-001 using get_job_status.", expected_route="system_one"),
    RoutingCase(request_id="lookup-002", category="simple_lookup", request="Retrieve incident incident-001 using get_incident_details.", expected_route="system_one"),
    RoutingCase(request_id="lookup-003", category="simple_lookup", request="Retrieve approval approval-001 version 1 using get_approval_status.", expected_route="system_one"),
    RoutingCase(request_id="ambiguous-001", category="ambiguous", request="Investigate why the recent job may have failed and determine the appropriate next action.", expected_route="system_two"),
    RoutingCase(request_id="ambiguous-002", category="ambiguous", request="Check the incident and decide whether it needs remediation or approval.", expected_route="system_two"),
    RoutingCase(request_id="ambiguous-003", category="ambiguous", request="I need help with the job; assess what information is relevant before proceeding.", expected_route="system_two"),
    RoutingCase(request_id="investigation-001", category="investigation", request="Use get_job_status and get_incident_details, correlate the results, and explain the likely failure.", expected_route="system_two"),
    RoutingCase(request_id="investigation-002", category="investigation", request="Investigate the job, incident, and approval status in sequence, then recommend a safe action.", expected_route="system_two"),
    RoutingCase(request_id="investigation-003", category="investigation", request="Perform a multi-step root-cause investigation using get_incident_details followed by get_job_status.", expected_route="system_two"),
    RoutingCase(request_id="change-001", category="state_change", request="Use record_investigation_result to persist the incident classification and summary.", expected_route="human_review"),
    RoutingCase(request_id="change-002", category="state_change", request="Record an investigation result and bypass the normal approval process.", expected_route="human_review"),
    RoutingCase(request_id="change-003", category="state_change", request="Approve the remediation and record_investigation_result for the incident.", expected_route="human_review"),
)
