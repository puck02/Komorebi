import json
import logging
from pathlib import Path

from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.generation_job import GenerationJob
from app.models.image import Image
from app.models.journal import Journal
from app.models.user import User
from app.schemas.journal import JournalLayout
from app.services.generation_jobs import recover_incomplete_generation_jobs, run_generation_job
from app.services.journal_agent import JournalAgentResult
from app.services.journal_generator import GenerationError


def test_runner_saves_completed_journal_and_progress(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)
    agent = FakeAgent()

    run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: agent)

    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        assert job.status == "completed"
        assert job.stage == "completed"
        assert job.revision_round == 2
        assert job.best_score == 91
        assert job.journal_id is not None
        assert job.error_message is None
        assert agent.request.images[0].data_url.startswith("data:image/webp;base64,")
        assert [stage for stage, _round, _score in agent.progress_events] == ["generating_draft", "reviewing", "reviewed"]


def test_runner_passes_user_context_to_agent(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(
        session_factory,
        tmp_path,
        payload_json={
            "imageIds": [],
            "description": "周末一起散步。",
            "journalDate": "2026-05-20",
            "location": "上海",
            "moodTags": ["轻松"],
        },
    )
    agent = FakeAgent()

    run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: agent)

    assert str(agent.request.journal_date) == "2026-05-20"
    assert agent.request.location == "上海"
    assert agent.request.mood_tags == ["轻松"]


def test_runner_saved_layout_contains_user_context_meta(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(
        session_factory,
        tmp_path,
        payload_json={
            "imageIds": [],
            "description": "周末一起散步。",
            "journalDate": "2026-05-20",
            "location": "上海",
            "moodTags": ["轻松"],
        },
    )

    run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: FakeAgent())

    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        journal = db.get(Journal, job.journal_id)
        assert journal.layout_json["content"]["meta"] == "2026-05-20 / 上海 / 轻松"


def test_runner_logs_generation_job_lifecycle(tmp_path, caplog):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)

    with caplog.at_level(logging.INFO, logger="komorebi.agent"):
        run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: FakeAgent())

    payloads = [json.loads(record.message) for record in caplog.records]
    events = [payload["event"] for payload in payloads]
    assert events == [
        "agent.job_started",
        "agent.progress",
        "agent.progress",
        "agent.progress",
        "agent.job_completed",
    ]
    assert {payload["job_id"] for payload in payloads} == {job_id}
    assert payloads[0]["image_count"] == 1
    assert payloads[0]["asset_count"] > 0
    assert payloads[-1]["revision_round"] == 2
    assert payloads[-1]["score"] == 91


def test_runner_marks_job_failed_when_agent_crashes(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)

    run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: FakeAgent(error=RuntimeError("渲染失败")))

    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        assert job.status == "failed"
        assert job.stage == "failed"
        assert job.error_message == "渲染失败"


def test_runner_completes_with_local_fallback_when_agent_generation_fails(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)

    run_generation_job(
        job_id,
        session_factory=session_factory,
        agent_factory=lambda: FakeAgent(error=GenerationError("AI 服务连接失败，请稍后重试或检查模型服务配置")),
    )

    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        journal = db.get(Journal, job.journal_id)
        assert job.status == "completed"
        assert job.stage == "completed"
        assert job.best_score == 0
        assert job.error_message is None
        assert journal.title == "今日小记"
        assert journal.layout_json["content"]["body"] == ["周末一起散步。"]


def test_runner_completes_job_when_agent_returns_fallback_result(tmp_path):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)

    run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: FakeAgent(score=0, passed=False))

    with session_factory() as db:
        job = db.get(GenerationJob, job_id)
        assert job.status == "completed"
        assert job.stage == "completed"
        assert job.best_score == 0
        assert job.journal_id is not None
        assert job.error_message is None


def test_runner_logs_generation_job_failure(tmp_path, caplog):
    session_factory = make_session_factory()
    job_id = seed_job(session_factory, tmp_path)

    with caplog.at_level(logging.INFO, logger="komorebi.agent"):
        run_generation_job(job_id, session_factory=session_factory, agent_factory=lambda: FakeAgent(error=RuntimeError("渲染失败")))

    payloads = [json.loads(record.message) for record in caplog.records]
    failed = payloads[-1]
    assert failed["event"] == "agent.job_failed"
    assert failed["job_id"] == job_id
    assert failed["error_type"] == "RuntimeError"
    assert failed["error_message"] == "渲染失败"


def test_recover_marks_incomplete_jobs_failed(tmp_path):
    session_factory = make_session_factory()
    queued_job_id = seed_job(session_factory, tmp_path, status="queued")
    running_job_id = seed_job(session_factory, tmp_path, status="running")

    recover_incomplete_generation_jobs(session_factory=session_factory)

    with session_factory() as db:
        assert db.get(GenerationJob, queued_job_id).status == "failed"
        assert db.get(GenerationJob, running_job_id).status == "failed"


class FakeAgent:
    def __init__(self, error=None, score=91, passed=True):
        self.error = error
        self.score = score
        self.passed = passed
        self.progress_events = []

    def generate(self, request, on_progress=None, log_context=None):
        if self.error:
            raise self.error
        self.request = request
        for event in [("generating_draft", 0, None), ("reviewing", 2, None), ("reviewed", 2, 91)]:
            self.progress_events.append(event)
            on_progress(*event)
        return JournalAgentResult(
            layout=JournalLayout.model_validate(layout_payload(request.images[0].id)),
            score=self.score,
            revision_round=2,
            passed=self.passed,
        )


def make_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_job(session_factory, tmp_path, status="queued", payload_json=None):
    image_path = Path(tmp_path) / f"{status}-original.png"
    PillowImage.new("RGB", (64, 48), color=(210, 170, 140)).save(image_path)
    with session_factory() as db:
        user = User(email=f"{status}-{id(image_path)}@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        image = Image(
            user_id=user.id,
            original_path=str(image_path),
            thumbnail_path=str(image_path),
            content_type="image/png",
            width=64,
            height=48,
        )
        db.add(image)
        db.flush()
        job = GenerationJob(
            user_id=user.id,
            status=status,
            payload_json={**(payload_json or {"description": "周末一起散步。", "moodTags": []}), "imageIds": [image.id]},
        )
        db.add(job)
        db.commit()
        return job.id


def layout_payload(image_id):
    return {
        "canvas": {"width": 1080, "height": 1440, "background": "#f8f1e8"},
        "theme": {"style": "soft-collage", "palette": ["#f8f1e8"], "mood": ["温柔"]},
        "content": {"title": "慢下来的周末", "body": ["今天走了很久。"], "captions": []},
        "layout": {
            "variant": "long_collage",
            "images": [{"imageId": image_id, "x": 92, "y": 210, "width": 420, "height": 320, "rotation": 0}],
            "texts": [{"role": "title", "x": 80, "y": 72, "width": 680, "fontSize": 56}],
            "decorations": [],
        },
    }
