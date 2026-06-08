from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.schemas.journal import JournalLayout
from app.services.agent_observability import issue_summary, layout_observability_summary, log_agent_event
from app.services.journal_generator import GenerationError, JournalGenerationRequest, build_fallback_layout, sanitize_model_layout
from app.services.layout_rules import check_layout_rules

QUALITY_THRESHOLD = 85
MAX_REVISION_ROUNDS = 3


class JournalAgentClient(Protocol):
    def generate_layout(self, request: JournalGenerationRequest) -> dict[str, Any]:
        pass

    def review_layout(
        self,
        request: JournalGenerationRequest,
        layout: dict[str, Any],
        screenshot_data_url: str,
        rule_issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        pass

    def revise_layout(
        self,
        request: JournalGenerationRequest,
        layout: dict[str, Any],
        screenshot_data_url: str,
        review: dict[str, Any],
        revision_round: int,
        best_score: float,
    ) -> dict[str, Any]:
        pass


class JournalRenderer(Protocol):
    def render(self, layout: dict[str, Any], request: JournalGenerationRequest) -> str:
        pass


@dataclass(frozen=True)
class JournalAgentResult:
    layout: JournalLayout
    score: float
    revision_round: int
    passed: bool


@dataclass(frozen=True)
class JournalCandidate:
    layout: JournalLayout
    screenshot_data_url: str
    review: dict[str, Any]
    score: float
    revision_round: int
    rule_issues: list[dict[str, Any]]


class JournalAgent:
    def __init__(
        self,
        client: JournalAgentClient,
        renderer: JournalRenderer,
        *,
        max_revision_rounds: int = MAX_REVISION_ROUNDS,
        quality_threshold: float = QUALITY_THRESHOLD,
        rule_checker: Callable[[JournalLayout, JournalGenerationRequest], list[dict[str, Any]]] = check_layout_rules,
    ):
        self.client = client
        self.renderer = renderer
        self.max_revision_rounds = max_revision_rounds
        self.quality_threshold = quality_threshold
        self.rule_checker = rule_checker

    def generate(
        self,
        request: JournalGenerationRequest,
        on_progress: Callable[[str, int, float | None], None] | None = None,
        log_context: dict[str, Any] | None = None,
    ) -> JournalAgentResult:
        notify = on_progress or (lambda _stage, _round, _score: None)
        context = log_context or {}
        notify("generating_draft", 0, None)
        try:
            raw_layout = self.client.generate_layout(request)
        except GenerationError as exc:
            return self._result_from_fallback_layout(request, context, exc)
        try:
            current = self._review_candidate(raw_layout, request, 0, notify, context)
        except GenerationError as exc:
            return self._result_from_unreviewed_layout(raw_layout, request, 0, context, exc)
        best_any = current
        best_valid = current if not current.rule_issues else None

        for revision_round in range(1, self.max_revision_rounds + 1):
            if self._passes(current):
                return result_from_candidate(current, passed=True)

            base = best_valid or best_any
            notify("revising", revision_round, base.score)
            log_agent_event(
                "agent.revision_requested",
                **context,
                revision_round=revision_round,
                base_score=base.score,
                base_revision_round=base.revision_round,
            )
            try:
                raw_layout = self.client.revise_layout(
                    request,
                    base.layout.model_dump(by_alias=True),
                    base.screenshot_data_url,
                    base.review,
                    revision_round,
                    base.score,
                )
                current = self._review_candidate(raw_layout, request, revision_round, notify, context)
            except GenerationError as exc:
                log_agent_event(
                    "agent.refinement_unavailable",
                    **context,
                    revision_round=revision_round,
                    best_score=base.score,
                    best_revision_round=base.revision_round,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc) or exc.__class__.__name__,
                )
                return result_from_candidate(base, passed=False)
            if current.score > best_any.score:
                best_any = current
            if not current.rule_issues and (best_valid is None or current.score > best_valid.score):
                best_valid = current

        if self._passes(current):
            return result_from_candidate(current, passed=True)
        return result_from_candidate(best_valid or best_any, passed=False)

    def _review_candidate(
        self,
        raw_layout: dict[str, Any],
        request: JournalGenerationRequest,
        revision_round: int,
        notify: Callable[[str, int, float | None], None],
        log_context: dict[str, Any],
    ) -> JournalCandidate:
        cleaned = sanitize_model_layout(raw_layout, request)
        layout = JournalLayout.model_validate(cleaned)
        rule_issues = self.rule_checker(layout, request)
        notify("reviewing", revision_round, None)
        try:
            screenshot_data_url = self.renderer.render(layout.model_dump(by_alias=True), request)
        except Exception as error:
            raise GenerationError("视觉渲染失败，请稍后重试") from error
        review = self.client.review_layout(request, layout.model_dump(by_alias=True), screenshot_data_url, rule_issues)
        score = float(review.get("score", 0))
        notify("reviewed", revision_round, score)
        review_issues = review.get("issues", [])
        if not isinstance(review_issues, list):
            review_issues = []
        log_agent_event(
            "agent.candidate_reviewed",
            **log_context,
            revision_round=revision_round,
            score=score,
            passed=review.get("passed") is True,
            rule_issues=issue_summary(rule_issues),
            review_issues=issue_summary(review_issues),
            **layout_observability_summary(layout, request.assets),
        )
        return JournalCandidate(layout, screenshot_data_url, review, score, revision_round, rule_issues)

    def _result_from_unreviewed_layout(
        self,
        raw_layout: dict[str, Any],
        request: JournalGenerationRequest,
        revision_round: int,
        log_context: dict[str, Any],
        error: GenerationError,
    ) -> JournalAgentResult:
        cleaned = sanitize_model_layout(raw_layout, request)
        layout = JournalLayout.model_validate(cleaned)
        rule_issues = self.rule_checker(layout, request)
        log_agent_event(
            "agent.review_unavailable",
            **log_context,
            revision_round=revision_round,
            error_type=error.__class__.__name__,
            error_message=str(error) or error.__class__.__name__,
            rule_issues=issue_summary(rule_issues),
            **layout_observability_summary(layout, request.assets),
        )
        if any(issue.get("severity") == "high" for issue in rule_issues):
            fallback = JournalLayout.model_validate(sanitize_model_layout(build_fallback_layout(request), request))
            log_agent_event(
                "agent.review_unavailable_fallback_generated",
                **log_context,
                revision_round=revision_round,
                error_type=error.__class__.__name__,
                error_message=str(error) or error.__class__.__name__,
                rule_issues=issue_summary(rule_issues),
                **layout_observability_summary(fallback, request.assets),
            )
            return JournalAgentResult(fallback, 0, revision_round, False)
        return JournalAgentResult(layout, 0, revision_round, False)

    def _result_from_fallback_layout(
        self,
        request: JournalGenerationRequest,
        log_context: dict[str, Any],
        error: GenerationError,
    ) -> JournalAgentResult:
        cleaned = sanitize_model_layout(build_fallback_layout(request), request)
        layout = JournalLayout.model_validate(cleaned)
        log_agent_event(
            "agent.generation_unavailable",
            **log_context,
            error_type=error.__class__.__name__,
            error_message=str(error) or error.__class__.__name__,
            **layout_observability_summary(layout, request.assets),
        )
        return JournalAgentResult(layout, 0, 0, False)

    def _passes(self, candidate: JournalCandidate) -> bool:
        return not candidate.rule_issues and candidate.score >= self.quality_threshold and candidate.review.get("passed") is True


def result_from_candidate(candidate: JournalCandidate, *, passed: bool) -> JournalAgentResult:
    return JournalAgentResult(candidate.layout, candidate.score, candidate.revision_round, passed)
