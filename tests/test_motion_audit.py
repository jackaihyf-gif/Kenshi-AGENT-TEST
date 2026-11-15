from kenshi_test.motion_audit import audit_motion, parse_log

SOURCE = "run lower tracks=2 b2=(1.00000,0.00000,0.00000,0.00000)"


def sample(version="0.8.2", source=SOURCE, weight="1.000"):
    return (
        "KenshiLua logger initialized\n"
        f"[JACK T60 WearLab v{version}] Ready. test\n"
        "[JACK T60 MotionAudit] SOURCES owner=test count=174\n"
        f"{source}\n"
        f"[JACK T60 MotionAudit] PLAYING owner=test speed=20 order=2 "
        f"run lower[w={weight},t=0.500]; run upper[w=1.000,t=0.500]\n"
    )


def audit(tmp_path, text):
    log = tmp_path / "game.log"
    reference = tmp_path / "reference.txt"
    log.write_text(text, encoding="utf-8")
    reference.write_text(SOURCE, encoding="utf-8")
    return audit_motion(log, reference, "0.8.2", ["run"], tmp_path / "reports")


def test_observed_sources_and_activation_do_not_claim_visual_acceptance(tmp_path):
    report, directory = audit(tmp_path, sample())
    assert report.exit_code == 0
    assert not report.game_verified
    assert report.evidence_kind == "game_log_observation"
    assert (directory / "captured-kenshilua.log").read_text("utf-8") == sample()


def test_wrong_version_and_fullbody_source_are_detected(tmp_path):
    report, _ = audit(tmp_path, sample("0.8.1", SOURCE.replace("tracks=2", "tracks=27")))
    assert report.exit_code == 1
    assert {c.name for c in report.checks if c.status == "failed"} == {
        "loaded_version", "loaded_source_fingerprints",
    }


def test_enabled_zero_weight_is_not_activation(tmp_path):
    report, _ = audit(tmp_path, sample(weight="0.000"))
    assert report.exit_code == 6
    assert next(c for c in report.checks if c.name == "activation_run").status == "skipped"


def test_new_session_does_not_reuse_old_samples(tmp_path):
    text = sample() + "KenshiLua logger initialized\n[JACK T60 WearLab v0.8.2] Ready.\n"
    assert parse_log(text)["samples"] == []
    report, _ = audit(tmp_path, text)
    assert report.exit_code == 6


def test_all_bodies_must_match_reference(tmp_path):
    text = sample() + "[JACK T60 MotionAudit] SOURCES owner=second count=174\n"
    text += SOURCE.replace("tracks=2", "tracks=27") + "\n"
    report, _ = audit(tmp_path, text)
    assert report.exit_code == 1


def test_missing_source_clip_does_not_pass(tmp_path):
    report, _ = audit(tmp_path, sample(source=SOURCE.replace("run lower", "run upper")))
    assert report.exit_code == 1
