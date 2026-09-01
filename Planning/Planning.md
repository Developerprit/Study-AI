# Study AI — Planning / 技术方案

> A teaching-first, fully local knowledge framework.
> 一个「教学式」的纯本地知识框架。

---

## 1. 概述 / Overview

Study AI 是一个**教学式（teaching-first）**知识框架，分两端：

- **构建端 Builder**：StudyAI 出生时**只有中文常用字 + 符号，没有任何知识**。开发者通过对话把知识「教」给它；它自动记录每一轮对话、抽取知识单元、做抽取式总结。输入 `build study` 后，把所有历史打包成 `.study` 文件。
- **客户端 Client**：加载 `.study` 文件，基于二元组（bigram）检索把已学知识「用」起来回答查询，无外部依赖、不臆造。

This realizes the 4-step principle in `Study-AI.txt`:
本框架严格对应 `Study-AI.txt` 的 4 条原理：
1. Builder creates StudyAI with only common Chinese chars + symbols, zero knowledge.
2. Developer chats to teach; StudyAI records & summarizes automatically.
3. `build study` packages all history into a `.study` the client can use.
4. Essentially a process of learning & accepting external knowledge.

## 2. 技术决策 / Decisions

| 项 / Item | 决策 / Decision | 理由 / Why |
|---|---|---|
| 语言 Language | 纯 Python 3.13 | 中文/文本处理顺手，零原生依赖 |
| 形态 Form | 单文件 exe（Nuitka 打包） | 「开发软件」= 纯 exe |
| 入口 Entry | CLI 子命令 `builder` / `client` | 本质 CLI 工具 |
| 智能内核 Brain | 纯本地启发式 | 关键词抽取 + 抽取式总结 + 二元组检索，无 API、零成本、最易保证无 bug |
| 主题 Theme | `--theme dark\|light` | 满足浅色/深色模式要求（CLI 着色） |
| 许可证 License | Available License | 默认许可证 |
| 仓库 Repo | github.com/Developerprit/Study-AI | 默认上传 |

## 3. 架构 / Architecture

单模块 `studyai.py`（逻辑）+ `studyai_cli.py`（入口），结构如下：

```
studyai.py          # 全部核心逻辑
  base_vocab()      # GB2312 一级 3755 汉字 + 符号
  KnowledgeEntry   # 知识单元：分句 / 二元组 / 抽取式总结 / 关键词
  Study             # 知识库模型（name/created/knowledge/history/vocab）
  write_study()/read_study()   # .study 二进制读写
  retrieve()        # 客户端二元组检索
  run_builder()/run_client()   # 两端 REPL
  main()            # argparse 入口
studyai_cli.py     # from studyai import main
run_tests.py       # 自测脚本（必须全绿）
```

## 4. `.study` 文件格式 / Format

二进制，自描述、可校验：

```
[8 bytes magic "STUDYAI\x01"] [4 bytes uint32 LE compressed-len] [gzip(json payload)]
```

`payload` 字段：
- `version`：1
- `name`：知识库名
- `created`：ISO 时间戳
- `builder`：构建端版本号
- `base_chars`：基础汉字数量（客户端可独立复现，不存全表）
- `vocab_hash`：基础字表 sha256（版本/完整性校验）
- `knowledge[]`：每条 `{id, raw, sentences, bigrams, summary}`
- `history[]`：每轮 `{role, text, ts}`
- `checksum`：除 checksum 外全部字段的 sha256（防损坏）

读取时校验 magic → length → 解压 → json → checksum → version，任一失败抛清晰错误。

## 5. 测试计划 / Tests

`run_tests.py` 覆盖：
- `test_vocab`：字表非空且全为 CJK/符号（>3000 字）
- `test_knowledge`：分句 ≥2、二元组非空、总结非空
- `test_store_roundtrip`：内存构建 → 写盘 → 读回，字段完全一致
- `test_retrieve`：相关查询命中正确单元；纯 ASCII 查询返回空（不臆造）

交付前必须运行并全绿（「每次交付都要查看代码是否可用」）。

## 6. 交付物 / Deliverables

- `studyai.exe`（Nuitka 单文件，builder/client 子命令）
- `studyai.py` / `studyai_cli.py` / `run_tests.py`（源码）
- `README.md` + `README-zh.md`（双语，README.md 内链 README-zh.md）
- `index.html`（根目录商业风落地页，浅/深双主题，中英双语）
- 上传至 `github.com/Developerprit/Study-AI`（先验证仓库存在）
- 许可证：Available License
