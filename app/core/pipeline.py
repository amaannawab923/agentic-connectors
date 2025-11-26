"""Pipeline orchestrator for connector generation.

This module orchestrates the multi-agent connector generation pipeline
using Claude Agent SDK for all agent interactions.

Pipeline flow:
1. Research - Gather implementation patterns (WebSearch, WebFetch, Read)
2. Generate - Create connector code (Write, Read)
3. Test - Validate code works (Bash, Read)
4. Fix (up to 3 times) - Fix any test failures
5. Review - Code quality review (Read)
6. Improve (up to 2 times) - Address review feedback
7. Publish - Push to GitHub (Bash for git)

Budget enforcement:
- Max budget: $7.00 per connector
- Warning at: $5.00
- Force publish at: $6.00
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Settings
from ..models.enums import PipelineState, AgentType, TestStatus, ReviewDecision
from ..models.schemas import (
    ConnectorRequest,
    ConnectorResponse,
    AgentResult,
    GeneratedFile,
    TestResult,
    ReviewResult,
    BudgetStatus,
    PipelineStatus,
)
from .budget import BudgetController
from .state import PipelineStateManager
from ..agents.research import ResearchAgent
from ..agents.generator import GeneratorAgent
from ..agents.tester import TesterAgent
from ..agents.reviewer import ReviewerAgent
from ..agents.publisher import PublisherAgent

logger = logging.getLogger(__name__)


class ConnectorPipeline:
    """Orchestrates the connector generation pipeline using Claude Agent SDK.

    This pipeline uses specialized agents for each phase:
    - ResearchAgent: WebSearch, WebFetch, Read tools for API documentation
    - GeneratorAgent: Write, Read tools for code generation
    - TesterAgent: Bash, Read tools for running tests
    - ReviewerAgent: Read tool for code analysis
    - PublisherAgent: Bash tool for git operations

    All agents use Claude Agent SDK with:
    - Streaming responses for real-time progress
    - Tool allowlists per agent type
    - Security hooks to block dangerous operations
    - Automatic context management

    Attributes:
        settings: Configuration settings for the pipeline.
        budget: Budget controller for cost management.
        state: Pipeline state manager.
        hooks: Security hooks for agent tool usage.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
    ):
        """Initialize the connector pipeline.

        Args:
            settings: Configuration settings. Uses defaults if not provided.
        """
        self.settings = settings or Settings()
        self.budget = BudgetController(
            max_budget=self.settings.max_budget,
            warning_threshold=self.settings.warning_threshold,
            force_publish_threshold=self.settings.force_publish_threshold,
        )
        self.state: Optional[PipelineStateManager] = None

        # Initialize agents
        self.research_agent = ResearchAgent(settings=self.settings)
        self.generator_agent = GeneratorAgent(settings=self.settings)
        self.tester_agent = TesterAgent(settings=self.settings)
        self.reviewer_agent = ReviewerAgent(settings=self.settings)
        self.publisher_agent = PublisherAgent(settings=self.settings)

        logger.info("Pipeline initialized")

    async def run(self, request: ConnectorRequest) -> ConnectorResponse:
        """Run the complete connector generation pipeline.

        Args:
            request: The connector generation request.

        Returns:
            ConnectorResponse with results.
        """
        start_time = time.time()
        job_id = f"job-{int(time.time())}-{request.connector_name}"

        # Initialize state manager
        self.state = PipelineStateManager(job_id=job_id)
        self.state.update_state(PipelineState.PENDING)

        logger.info(f"Starting pipeline for {request.connector_name} (job: {job_id})")

        try:
            # Phase 1: Research
            research_result = await self._run_research(request)
            if not research_result.success:
                return self._create_failure_response(
                    request, job_id, start_time,
                    f"Research failed: {research_result.error}"
                )

            research_doc = research_result.output
            self.state.set_artifact("research_doc", research_doc)

            # Check budget
            if self.budget.is_exceeded():
                return self._create_budget_exceeded_response(request, job_id, start_time)

            # Phase 2: Generate
            generate_result = await self._run_generation(request, research_doc)
            if not generate_result.success:
                return self._create_failure_response(
                    request, job_id, start_time,
                    f"Generation failed: {generate_result.error}"
                )

            generated_files = self._parse_generated_files(generate_result.output)
            self.state.set_artifact("generated_files", generated_files)

            # Check budget
            if self.budget.is_exceeded():
                return self._create_budget_exceeded_response(request, job_id, start_time)

            # Phase 3: Test & Fix Loop
            test_result, generated_files = await self._run_test_fix_loop(
                request, generated_files, research_doc
            )

            if not test_result.passed:
                # If tests still fail after max retries, decide based on budget
                if self.budget.should_force_publish():
                    logger.warning("Tests failed but budget threshold reached - proceeding to review")
                else:
                    return self._create_failure_response(
                        request, job_id, start_time,
                        f"Tests failed after {self.settings.max_test_retries} attempts"
                    )

            # Check budget
            if self.budget.is_exceeded():
                return self._create_budget_exceeded_response(request, job_id, start_time)

            # Phase 4: Review & Improve Loop
            review_result, generated_files = await self._run_review_improve_loop(
                request, generated_files, test_result.passed
            )

            # Check budget
            if self.budget.is_exceeded():
                return self._create_budget_exceeded_response(request, job_id, start_time)

            # Phase 5: Publish
            publish_result = await self._run_publish(request, generated_files)

            # Create success response
            self.state.update_state(PipelineState.COMPLETED)

            return ConnectorResponse(
                job_id=job_id,
                connector_name=request.connector_name,
                status=PipelineStatus(
                    state=PipelineState.COMPLETED,
                    current_agent=None,
                    test_attempts=self.state.test_attempts,
                    review_cycles=self.state.review_cycles,
                    errors=[],
                ),
                budget=self.budget.get_status(),
                files_generated=[f["path"] for f in generated_files] if generated_files else [],
                pr_url=self.publisher_agent.get_pr_url(),
                research_summary=research_doc[:1000] if research_doc else None,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception(f"Pipeline failed for {request.connector_name}")
            self.state.update_state(PipelineState.FAILED)
            return self._create_failure_response(request, job_id, start_time, str(e))

    async def _run_research(self, request: ConnectorRequest) -> AgentResult:
        """Run the research phase."""
        self.state.update_state(PipelineState.RESEARCHING)
        logger.info(f"Starting research for {request.connector_name}")

        # Check budget before starting
        estimated_cost = self.settings.cost_per_research
        if not self.budget.can_afford(estimated_cost):
            return AgentResult(
                agent=AgentType.RESEARCH,
                success=False,
                error="Insufficient budget for research",
            )

        result = await self.research_agent.execute(
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            api_doc_url=request.api_doc_url,
            reference_repos=request.reference_repos,
            custom_requirements=request.custom_requirements,
        )

        # Charge actual cost (estimate if not tracked)
        actual_cost = self._calculate_agent_cost(result, self.settings.cost_per_research)
        self.budget.charge(actual_cost, "research")

        self.state.add_agent_result(result)
        return result

    async def _run_generation(
        self,
        request: ConnectorRequest,
        research_doc: str,
        fix_errors: Optional[List[str]] = None,
        review_feedback: Optional[List[str]] = None,
    ) -> AgentResult:
        """Run the code generation phase.

        Uses the GeneratorAgent with Write and Read tools from Claude Agent SDK.
        The agent generates connector code files based on research documentation.

        Args:
            request: The connector request containing name and type.
            research_doc: Research documentation to base generation on.
            fix_errors: Optional list of errors to fix from failed tests.
            review_feedback: Optional list of improvements from code review.

        Returns:
            AgentResult with generated files as JSON output.
        """
        self.state.update_state(PipelineState.GENERATING)
        logger.info(f"Starting generation for {request.connector_name}")

        # Check budget before starting
        estimated_cost = self.settings.cost_per_generation
        if not self.budget.can_afford(estimated_cost):
            return AgentResult(
                agent=AgentType.GENERATOR,
                success=False,
                error="Insufficient budget for generation",
            )

        # Create output directory for generated files
        output_dir = str(
            Path(self.settings.output_base_dir) /
            f"source-{request.connector_name}"
        )

        result = await self.generator_agent.execute(
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            research_doc=research_doc,
            output_dir=output_dir,
            fix_errors=fix_errors,
            review_feedback=review_feedback,
        )

        # Charge actual cost
        actual_cost = self._calculate_agent_cost(result, self.settings.cost_per_generation)
        self.budget.charge(actual_cost, "generation")

        self.state.add_agent_result(result)
        return result

    async def _run_test(
        self,
        request: ConnectorRequest,
        generated_files: List[Dict[str, Any]],
    ) -> AgentResult:
        """Run the testing phase."""
        self.state.update_state(PipelineState.TESTING)
        logger.info(f"Starting testing for {request.connector_name}")

        # Check budget before starting
        estimated_cost = self.settings.cost_per_test
        if not self.budget.can_afford(estimated_cost):
            return AgentResult(
                agent=AgentType.TESTER,
                success=False,
                error="Insufficient budget for testing",
            )

        # Convert dict files to GeneratedFile objects
        gen_files = [
            GeneratedFile(
                path=f["path"],
                content=f["content"],
                description=f.get("description", ""),
            )
            for f in generated_files
        ]

        # Create output directory
        output_dir = str(
            Path(self.settings.output_base_dir) /
            f"source-{request.connector_name}"
        )

        result = await self.tester_agent.execute(
            generated_files=gen_files,
            connector_name=request.connector_name,
            credentials=request.test_credentials,
            output_dir=output_dir,
        )

        # Charge actual cost
        actual_cost = self._calculate_agent_cost(result, self.settings.cost_per_test)
        self.budget.charge(actual_cost, "test")

        self.state.add_agent_result(result)
        self.state.increment_test_attempts()

        return result

    async def _run_test_fix_loop(
        self,
        request: ConnectorRequest,
        generated_files: List[Dict[str, Any]],
        research_doc: str,
    ) -> tuple[TestResult, List[Dict[str, Any]]]:
        """Run the test and fix loop up to max retries."""
        current_files = generated_files
        test_result = None

        for attempt in range(self.settings.max_test_retries + 1):
            # Run tests
            test_agent_result = await self._run_test(request, current_files)

            if not test_agent_result.success:
                logger.error(f"Test execution failed: {test_agent_result.error}")
                test_result = TestResult(
                    status=TestStatus.ERROR,
                    passed=False,
                    errors=[test_agent_result.error or "Unknown error"],
                )
                break

            # Parse test result
            try:
                test_data = json.loads(test_agent_result.output)
                test_result = TestResult(**test_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse test result: {e}")
                test_result = TestResult(
                    status=TestStatus.ERROR,
                    passed=False,
                    errors=["Failed to parse test results"],
                )
                break

            # Check if tests passed
            if test_result.passed:
                logger.info(f"Tests passed on attempt {attempt + 1}")
                break

            # Check if we should retry
            if attempt >= self.settings.max_test_retries:
                logger.warning(f"Max test retries ({self.settings.max_test_retries}) exceeded")
                break

            # Check budget before fix
            if self.budget.is_exceeded() or self.budget.should_force_publish():
                logger.warning("Budget threshold reached - skipping fix attempt")
                break

            # Run fix generation
            logger.info(f"Fixing errors (attempt {attempt + 1})")
            self.state.update_state(PipelineState.FIXING)

            fix_result = await self._run_generation(
                request=request,
                research_doc=research_doc,
                fix_errors=test_result.errors,
            )

            if fix_result.success:
                current_files = self._parse_generated_files(fix_result.output)
                self.state.set_artifact("generated_files", current_files)

        return test_result, current_files

    async def _run_review(
        self,
        request: ConnectorRequest,
        generated_files: List[Dict[str, Any]],
        test_passed: bool,
    ) -> AgentResult:
        """Run the code review phase."""
        self.state.update_state(PipelineState.REVIEWING)
        logger.info(f"Starting review for {request.connector_name}")

        # Check budget before starting
        estimated_cost = self.settings.cost_per_review
        if not self.budget.can_afford(estimated_cost):
            return AgentResult(
                agent=AgentType.REVIEWER,
                success=False,
                error="Insufficient budget for review",
            )

        # Convert dict files to GeneratedFile objects
        gen_files = [
            GeneratedFile(
                path=f["path"],
                content=f["content"],
                description=f.get("description", ""),
            )
            for f in generated_files
        ]

        result = await self.reviewer_agent.execute(
            generated_files=gen_files,
            connector_name=request.connector_name,
            test_passed=test_passed,
        )

        # Charge actual cost
        actual_cost = self._calculate_agent_cost(result, self.settings.cost_per_review)
        self.budget.charge(actual_cost, "review")

        self.state.add_agent_result(result)
        self.state.increment_review_cycles()

        return result

    async def _run_review_improve_loop(
        self,
        request: ConnectorRequest,
        generated_files: List[Dict[str, Any]],
        test_passed: bool,
    ) -> tuple[ReviewResult, List[Dict[str, Any]]]:
        """Run the review and improve loop up to max cycles."""
        current_files = generated_files
        review_result = None
        research_doc = self.state.get_artifact("research_doc", "")

        for cycle in range(self.settings.max_review_cycles + 1):
            # Run review
            review_agent_result = await self._run_review(
                request, current_files, test_passed
            )

            if not review_agent_result.success:
                logger.error(f"Review execution failed: {review_agent_result.error}")
                review_result = ReviewResult(
                    decision=ReviewDecision.NEEDS_WORK,
                    approved=False,
                    score=0.0,
                    summary="Review failed to execute",
                )
                break

            # Parse review result
            try:
                review_data = json.loads(review_agent_result.output)
                review_result = ReviewResult(**review_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse review result: {e}")
                review_result = ReviewResult(
                    decision=ReviewDecision.NEEDS_WORK,
                    approved=False,
                    score=5.0,
                    summary="Review result could not be parsed",
                )
                break

            # Check if approved
            if review_result.approved:
                logger.info(f"Code approved on cycle {cycle + 1} (score: {review_result.score})")
                break

            # Check if we should retry improvements
            if cycle >= self.settings.max_review_cycles:
                logger.warning(f"Max review cycles ({self.settings.max_review_cycles}) exceeded")
                break

            # Check budget before improvement
            if self.budget.is_exceeded() or self.budget.should_force_publish():
                logger.warning("Budget threshold reached - skipping improvement")
                break

            # Run improvement generation
            logger.info(f"Improving code (cycle {cycle + 1})")
            self.state.update_state(PipelineState.IMPROVING)

            # Get improvement suggestions from reviewer
            improvements = self.reviewer_agent.get_improvement_suggestions(review_result)

            improve_result = await self._run_generation(
                request=request,
                research_doc=research_doc,
                review_feedback=improvements,
            )

            if improve_result.success:
                current_files = self._parse_generated_files(improve_result.output)
                self.state.set_artifact("generated_files", current_files)

                # Re-run tests after improvement
                test_agent_result = await self._run_test(request, current_files)
                if test_agent_result.success:
                    try:
                        test_data = json.loads(test_agent_result.output)
                        test_passed = test_data.get("passed", False)
                    except:
                        test_passed = False

        return review_result, current_files

    async def _run_publish(
        self,
        request: ConnectorRequest,
        generated_files: List[Dict[str, Any]],
    ) -> AgentResult:
        """Run the publish phase."""
        self.state.update_state(PipelineState.PUBLISHING)
        logger.info(f"Starting publish for {request.connector_name}")

        # Convert dict files to GeneratedFile objects
        gen_files = [
            GeneratedFile(
                path=f["path"],
                content=f["content"],
                description=f.get("description", ""),
            )
            for f in generated_files
        ]

        # Create output directory
        output_dir = str(
            Path(self.settings.output_base_dir) /
            f"source-{request.connector_name}"
        )

        result = await self.publisher_agent.execute(
            generated_files=gen_files,
            connector_name=request.connector_name,
            output_dir=output_dir,
            repo_path=request.repo_path,
            create_pr=request.create_pr,
        )

        self.state.add_agent_result(result)
        return result

    def _parse_generated_files(self, output: str) -> List[Dict[str, Any]]:
        """Parse generated files from agent output."""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            logger.error("Failed to parse generated files JSON")
            return []

    def _calculate_agent_cost(
        self,
        result: AgentResult,
        estimated_cost: float,
    ) -> float:
        """Calculate actual agent cost based on token usage."""
        if result.tokens_used:
            # Calculate based on actual token usage
            # Assuming ~$3/1M input, ~$15/1M output for Sonnet
            # Rough estimate: average $9/1M tokens
            return (result.tokens_used / 1_000_000) * 9.0
        return estimated_cost

    def _create_failure_response(
        self,
        request: ConnectorRequest,
        job_id: str,
        start_time: float,
        error: str,
    ) -> ConnectorResponse:
        """Create a failure response."""
        self.state.update_state(PipelineState.FAILED)

        return ConnectorResponse(
            job_id=job_id,
            connector_name=request.connector_name,
            status=PipelineStatus(
                state=PipelineState.FAILED,
                current_agent=self.state.current_state.value if self.state else None,
                test_attempts=self.state.test_attempts if self.state else 0,
                review_cycles=self.state.review_cycles if self.state else 0,
                errors=[error],
            ),
            budget=self.budget.get_status(),
            files_generated=[],
            duration_seconds=time.time() - start_time,
        )

    def _create_budget_exceeded_response(
        self,
        request: ConnectorRequest,
        job_id: str,
        start_time: float,
    ) -> ConnectorResponse:
        """Create a budget exceeded response."""
        self.state.update_state(PipelineState.BUDGET_EXCEEDED)

        return ConnectorResponse(
            job_id=job_id,
            connector_name=request.connector_name,
            status=PipelineStatus(
                state=PipelineState.BUDGET_EXCEEDED,
                current_agent=self.state.current_state.value if self.state else None,
                test_attempts=self.state.test_attempts if self.state else 0,
                review_cycles=self.state.review_cycles if self.state else 0,
                errors=[f"Budget exceeded: ${self.budget.total_spent:.2f} of ${self.budget.max_budget:.2f}"],
            ),
            budget=self.budget.get_status(),
            files_generated=[],
            duration_seconds=time.time() - start_time,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "state": self.state.current_state.value if self.state else "not_started",
            "budget": self.budget.get_status().model_dump(),
            "test_attempts": self.state.test_attempts if self.state else 0,
            "review_cycles": self.state.review_cycles if self.state else 0,
        }
