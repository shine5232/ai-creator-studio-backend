"""End-to-end test for VideoMergeService using real ffmpeg.

Usage:
    cd openclaw-server
    python tests/test_video_merge_e2e.py
"""

import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from sqlalchemy import select

from app.models.project import Project
from app.models.script import Script, Shot, Storyboard
from app.services.video_merge_service import VideoMergeService
from app.worker.db import get_sync_session, SyncSessionLocal


UPLOAD_DIR = Path("data/uploads")
CLIPS = [
    UPLOAD_DIR / "clip_001.mp4",
    UPLOAD_DIR / "clip_002.mp4",
    UPLOAD_DIR / "clip_003.mp4",
]
BGM = UPLOAD_DIR / "test_bgm.m4a"


def setup_test_data() -> int:
    """Insert a Project → Script → Storyboard → Shots chain and return project_id."""
    with get_sync_session() as session:
        # Check if test project already exists
        existing = session.execute(
            select(Project).where(Project.name == "[E2E Test] Merge")
        ).scalar_one_or_none()
        if existing:
            # Clean up old data
            session.delete(existing)
            session.flush()

        project = Project(
            user_id=1,
            name="[E2E Test] Merge",
            status="draft",
        )
        session.add(project)
        session.flush()
        pid = project.id

        script = Script(
            project_id=pid,
            title="Test Script",
            content="Test content",
            is_current=True,
        )
        session.add(script)
        session.flush()
        sid = script.id

        storyboard = Storyboard(
            script_id=sid,
            total_shots=3,
        )
        session.add(storyboard)
        session.flush()
        sbid = storyboard.id

        for i, clip_path in enumerate(CLIPS, start=1):
            shot = Shot(
                storyboard_id=sbid,
                shot_number=i,
                description=f"Test shot {i}",
                video_path=str(clip_path),
                video_status="completed",
                video_duration=3.0,
            )
            session.add(shot)

        session.commit()
        return pid


def teardown_test_data(project_id: int):
    """Remove test data."""
    with get_sync_session() as session:
        project = session.get(Project, project_id)
        if project:
            session.delete(project)
            session.commit()
    print(f"  [cleanup] Deleted test project {project_id}")


def test_probe():
    """Test 1: probe_duration."""
    print("\n=== Test 1: probe_duration ===")
    svc = VideoMergeService()
    for clip in CLIPS:
        dur = svc.probe_duration(str(clip))
        print(f"  {clip.name}: {dur:.3f}s")
        assert dur > 0, f"Duration should be > 0, got {dur}"
    print("  PASS")


def test_normalize():
    """Test 2: normalize_video."""
    print("\n=== Test 2: normalize_video ===")
    svc = VideoMergeService()
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(dir=str(UPLOAD_DIR / "temp")) as tmp:
        out = Path(tmp) / "norm_test.mp4"
        svc.normalize_video(str(CLIPS[0]), str(out))
        assert out.exists(), "Normalised file not created"

        # Verify output params
        import json, subprocess
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(out)],
            capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)
        vs = [s for s in info["streams"] if s["codec_type"] == "video"][0]
        w, h = vs["width"], vs["height"]
        codec = vs["codec_name"]
        print(f"  Output: {w}x{h}  codec={codec}")
        assert (w, h) == (1080, 1920), f"Expected 1080x1920, got {w}x{h}"
        assert codec == "h264", f"Expected h264, got {codec}"
    print("  PASS")


def test_concat():
    """Test 3: concat_videos."""
    print("\n=== Test 3: concat_videos ===")
    svc = VideoMergeService()
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(dir=str(UPLOAD_DIR / "temp")) as tmp:
        tmp = Path(tmp)
        # First normalise all clips
        norm_paths = []
        for i, clip in enumerate(CLIPS):
            out = tmp / f"norm_{i}.mp4"
            svc.normalize_video(str(clip), str(out))
            norm_paths.append(str(out))

        concat_out = tmp / "concat.mp4"
        svc.concat_videos(norm_paths, str(concat_out))
        assert concat_out.exists(), "Concat file not created"

        # Verify total duration ≈ 3 * 3 = 9s (at 24fps re-encoded)
        dur = svc.probe_duration(str(concat_out))
        print(f"  Concatenated duration: {dur:.2f}s (expected ~9s)")
        assert 8.5 < dur < 9.5, f"Duration off: {dur}"
    print("  PASS")


def test_background_music():
    """Test 4: add_background_music."""
    print("\n=== Test 4: add_background_music ===")
    svc = VideoMergeService()
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(dir=str(UPLOAD_DIR / "temp")) as tmp:
        tmp = Path(tmp)
        # Normalise one clip
        norm = tmp / "norm.mp4"
        svc.normalize_video(str(CLIPS[0]), str(norm))

        mixed = tmp / "mixed.mp4"
        svc.add_background_music(str(norm), str(BGM), str(mixed))
        assert mixed.exists(), "Mixed file not created"

        dur = svc.probe_duration(str(mixed))
        print(f"  Mixed duration: {dur:.2f}s")
        assert dur > 0
    print("  PASS")


def test_full_merge():
    """Test 5: full merge pipeline (no music)."""
    print("\n=== Test 5: full merge pipeline (no music) ===")
    project_id = setup_test_data()
    try:
        svc = VideoMergeService()
        progress_log = []

        def on_progress(pct, msg):
            progress_log.append((pct, msg))
            print(f"  [{pct:3d}%] {msg}")

        output = svc.merge_project_videos(
            project_id=project_id,
            add_music=False,
            music_path=None,
            on_progress=on_progress,
        )
        assert Path(output).exists(), f"Output file not found: {output}"
        dur = svc.probe_duration(output)
        print(f"  Final output: {output} ({dur:.2f}s)")
        assert dur > 8, f"Expected ~9s, got {dur}"

        # Verify progress went to 100
        assert progress_log[-1][0] == 100, "Progress did not reach 100%"

        # Verify DB was updated
        with get_sync_session() as session:
            project = session.get(Project, project_id)
            assert project.output_video_path == output
            assert project.status == "completed"
            assert project.output_duration is not None
            print(f"  DB: output_video_path={project.output_video_path}")
            print(f"  DB: status={project.status}, output_duration={project.output_duration}s")
    finally:
        teardown_test_data(project_id)
    print("  PASS")


def test_full_merge_with_music():
    """Test 6: full merge pipeline with background music."""
    print("\n=== Test 6: full merge pipeline (with music) ===")
    project_id = setup_test_data()
    try:
        svc = VideoMergeService()

        output = svc.merge_project_videos(
            project_id=project_id,
            add_music=True,
            music_path=str(BGM),
            on_progress=lambda p, m: print(f"  [{p:3d}%] {m}"),
        )
        assert Path(output).exists(), f"Output file not found: {output}"
        dur = svc.probe_duration(output)
        print(f"  Final output: {output} ({dur:.2f}s)")
        assert dur > 8, f"Expected ~9s, got {dur}"
    finally:
        teardown_test_data(project_id)
    print("  PASS")


if __name__ == "__main__":
    # Ensure temp dir exists
    (UPLOAD_DIR / "temp").mkdir(parents=True, exist_ok=True)

    # Check user_id=1 exists
    with SyncSessionLocal() as session:
        from app.models.user import User
        user = session.get(User, 1)
        if not user:
            # Create a test user
            from app.services.auth_service import AuthService
            svc = AuthService(session)
            user = svc.create_user("e2e_test", "test@test.com", "password123")
            session.commit()
            print(f"Created test user id={user.id}")

    tests = [
        test_probe,
        test_normalize,
        test_concat,
        test_background_music,
        test_full_merge,
        test_full_merge_with_music,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
