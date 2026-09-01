# -*- coding: utf-8 -*-
"""Self-tests for Study AI. Run: python run_tests.py
All checks must pass before delivery ("ensure no bugs")."""

import os
import tempfile
import studyai


def test_vocab():
    chars = studyai.base_chinese_chars()
    assert len(chars) > 3000, "base chinese chars should exceed 3000, got %d" % len(chars)
    for c in chars:
        assert studyai._is_cjk(c), "non-CJK char in base set: %r" % c
    v = studyai.base_vocab()
    assert studyai.vocab_hash() == studyai.vocab_hash()
    assert 0.0 <= studyai.vocab_coverage("abc") <= 1.0


def test_knowledge():
    e = studyai.KnowledgeEntry(0, "机器学习是人工智能的一个分支。深度学习使用神经网络进行训练。")
    assert len(e.sentences) >= 2, "expected >=2 sentences, got %d" % len(e.sentences)
    assert e.bigrams, "bigrams should not be empty"
    assert e.summary, "summary should not be empty"
    kw = e.top_keywords(6)
    assert isinstance(kw, list) and len(kw) > 0


def test_store_roundtrip():
    s = studyai.Study("test-study")
    s.add_turn("developer", "量子计算利用量子比特。")
    s.add_knowledge("量子计算利用量子比特进行并行运算，速度远超经典计算机。")
    s.add_turn("studyai", "[learned unit #0]")
    path = os.path.join(tempfile.gettempdir(), "studyai_test.study")
    studyai.write_study(path, s)
    assert os.path.getsize(path) > 0
    s2 = studyai.read_study(path)
    assert s2.name == s.name
    assert s2.created == s.created
    assert len(s2.knowledge) == len(s.knowledge)
    assert s2.knowledge[0].raw == s.knowledge[0].raw
    assert s2.knowledge[0].summary == s.knowledge[0].summary
    assert s2.vocab_hash == s.vocab_hash
    assert s2.builder == s.builder
    os.remove(path)


def test_store_corruption():
    s = studyai.Study("corrupt")
    s.add_knowledge("这是一条用于校验的知识。")
    path = os.path.join(tempfile.gettempdir(), "studyai_corrupt.study")
    studyai.write_study(path, s)
    with open(path, "r+b") as f:
        f.seek(len(studyai.STUDY_MAGIC) + 4)  # into compressed payload
        f.write(b"\x00\x00\x00\x00")
    try:
        studyai.read_study(path)
        raise AssertionError("should have raised on corrupted file")
    except (ValueError, OSError):
        pass
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_retrieve():
    s = studyai.Study("retrieve")
    s.add_knowledge("机器学习是人工智能的分支，使用大量数据训练模型。")
    s.add_knowledge("烹饪需要控制火候与时间，才能做出美味菜肴。")
    hits = studyai.retrieve(s, "什么是机器学习")
    assert hits, "expected at least one hit for relevant query"
    assert "机器" in hits[0].raw, "top hit should be the ML entry"
    none = studyai.retrieve(s, "xyz123")
    assert none == [], "pure-ASCII query should return empty (no hallucination)"
    empty = studyai.retrieve(s, "")
    assert empty == []


def test_cli_help():
    import argparse
    try:
        studyai.main([])
        raise AssertionError("empty argv should require a subcommand")
    except SystemExit as e:
        assert e.code != 0


if __name__ == "__main__":
    test_vocab()
    test_knowledge()
    test_store_roundtrip()
    test_store_corruption()
    test_retrieve()
    test_cli_help()
    print("ALL TESTS PASSED")
