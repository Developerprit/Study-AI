# Study AI

> A teaching-first, fully local knowledge framework.
> 一个「教学式」的纯本地知识框架。

Study AI learns the way a student does: it starts **empty** — knowing only common
Chinese characters and symbols, with **zero knowledge** — and grows by being *taught*.
A developer chats with the **builder**, which records, extracts and summarizes every
turn. One command, `build study`, packages the whole conversation into a portable
`.study` file. The **client** then loads that file and answers queries by retrieval —
no internet, no API, no hallucination.

---

## How it works (the 4 principles)

1. The builder creates StudyAI with **only common Chinese characters + symbols** and no knowledge.
2. The developer chats to teach it knowledge; StudyAI **records and auto-summarizes**.
3. The developer runs `build study`; StudyAI packs all history into a `.study` file the client can use.
4. It is, fundamentally, a process of **learning and accepting external knowledge**.

## Install / Build

- Pure Python 3.13, zero third-party dependencies for the logic.
- Prebuilt single-file executable: `studyai.exe` (builder + client in one binary).
- Build it yourself:

```bash
python -m venv venv && venv/Scripts/pip install nuitka
python -m nuitka --onefile --output-filename=studyai.exe studyai_cli.py
```

## Usage

### Builder — teach it, then export

```bash
studyai.exe builder --name my-study --theme dark
# StudyAI:builder> 机器学习是人工智能的分支，使用大量数据训练模型。
# Recorded. Extracted 1 sentence(s). Key terms: 学习, 模型, 分支 ...
# StudyAI:builder> build study
# Built .study -> my-study.study (1 unit(s), 2 turn(s))
```

Special commands inside the builder: `build study`, `status`, `summary`, `exit`.
Use `--resume file.study` to keep teaching an existing knowledge base.

### Client — load and query

```bash
studyai.exe client --file my-study.study --theme light
# StudyAI:client> 什么是机器学习
# [Match #0] 机器学习是人工智能的分支，使用大量数据训练模型。
#     机器学习是人工智能的分支，使用大量数据训练模型。
```

Commands inside the client: `info`, `list`, `exit`. Queries with no match return an
honest "No relevant knowledge found" instead of fabricating an answer.

## The `.study` file format

A self-describing, checksummed binary container:

```
[8 bytes magic "STUDYAI\x01"] [4 bytes uint32 LE length] [gzip(json payload)]
```

Payload: `version`, `name`, `created`, `builder`, `base_chars`, `vocab_hash`,
`knowledge[]` (each: `id, raw, sentences, bigrams, summary`), `history[]`, `checksum`.
On load it validates magic → length → gzip → checksum → version, failing clearly on corruption.

## Retrieval (pure heuristic, no model)

Knowledge is indexed by **CJK character bigrams**. A query is matched by bigram overlap
with each unit; top matches are returned. Pure-ASCII or empty queries return nothing,
so the client never invents facts it was not taught.

## Tests

```bash
python run_tests.py   # ALL TESTS PASSED
```

Covers vocabulary generation, knowledge extraction, `.study` round-trip, corruption
detection, and retrieval correctness.

## License

Released under the **Available License** — https://license.kscm.top/available.md

## 中文文档

See [README-zh.md](./README-zh.md).
