from unittest.mock import MagicMock
import pytest
from google.adk.events.request_input import RequestInput
from google.adk.events.event import Event
from app.nodes.hitl_approval_node import hitl_approval_node, HITLApprovalOutput
from app.nodes.optimization_planner_node import CleanupAction, ActionPlan, OptimizationPlannerOutput


@pytest.mark.asyncio
async def test_hitl_approval_yields_request() -> None:
    # Set up input
    actions = [
        CleanupAction(
            path="/allowed/dup1.txt",
            action_type="delete",
            reasoning="duplicate",
            estimated_space_recovered=1000,
            safe_to_delete=True,
            confidence=0.95,
        ),
        CleanupAction(
            path="/allowed/unsafe.txt",
            action_type="delete",
            reasoning="unsafe",
            estimated_space_recovered=2000,
            safe_to_delete=False,
            confidence=0.95,
        ),
    ]
    plan = ActionPlan(actions=actions, reasoning=["Test reasoning"], estimated_recovery=3000, dry_run=True)
    node_input = OptimizationPlannerOutput(action_plan=plan, reasoning="Planner done")

    # Mock context
    ctx = MagicMock()
    ctx.resume_inputs = None

    generator = hitl_approval_node(ctx, node_input)
    
    # First yield should be a RequestInput
    first_yield = await generator.__anext__()
    assert isinstance(first_yield, RequestInput)
    assert first_yield.interrupt_id == "hitl_approved"
    assert "dup1.txt" in first_yield.message
    assert "unsafe.txt" in first_yield.message


@pytest.mark.asyncio
async def test_hitl_approval_approved() -> None:
    actions = [
        CleanupAction(
            path="/allowed/dup1.txt",
            action_type="delete",
            reasoning="duplicate",
            estimated_space_recovered=1000,
            safe_to_delete=True,
            confidence=0.95,
        ),
        CleanupAction(
            path="/allowed/unsafe.txt",
            action_type="delete",
            reasoning="unsafe",
            estimated_space_recovered=2000,
            safe_to_delete=False,
            confidence=0.95,
        ),
    ]
    plan = ActionPlan(actions=actions, reasoning=["Test reasoning"], estimated_recovery=3000, dry_run=True)
    node_input = OptimizationPlannerOutput(action_plan=plan, reasoning="Planner done")

    # Mock context
    ctx = MagicMock()
    ctx.resume_inputs = {"hitl_approved": "yes"}

    generator = hitl_approval_node(ctx, node_input)
    
    # Should yield an Event with the output
    event_yield = await generator.__anext__()
    assert isinstance(event_yield, Event)
    
    output: HITLApprovalOutput = event_yield.output
    assert isinstance(output, HITLApprovalOutput)
    
    # Verify safety: unsafe.txt should have been filtered out
    assert len(output.approved_actions) == 1
    assert output.approved_actions[0].path == "/allowed/dup1.txt"
    assert "Selected 1 safe action" in output.reasoning


@pytest.mark.asyncio
async def test_hitl_approval_rejected() -> None:
    actions = [
        CleanupAction(
            path="/allowed/dup1.txt",
            action_type="delete",
            reasoning="duplicate",
            estimated_space_recovered=1000,
            safe_to_delete=True,
            confidence=0.95,
        ),
    ]
    plan = ActionPlan(actions=actions, reasoning=["Test reasoning"], estimated_recovery=1000, dry_run=True)
    node_input = OptimizationPlannerOutput(action_plan=plan, reasoning="Planner done")

    # Mock context
    ctx = MagicMock()
    ctx.resume_inputs = {"hitl_approved": "no"}

    generator = hitl_approval_node(ctx, node_input)
    event_yield = await generator.__anext__()
    
    output: HITLApprovalOutput = event_yield.output
    assert len(output.approved_actions) == 0
    assert "User approved the plan: False" in output.reasoning
