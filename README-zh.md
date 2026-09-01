# Study AI（中文文档）

> 一个「教学式」的纯本地知识框架。

Study AI 像学生一样学习：它**出生即空壳**——只认识中文常用字和符号，**没有任何知识**——
靠被「教」而成长。开发者在**构建端**跟它对话，它记录、抽取、总结每一轮。一条
`build study` 命令把整段对话打包成可移植的 `.study` 文件。**客户端**加载该文件后通过
检索回答问题——无联网、无 API、不臆造。

---

## 工作原理（四条原理）

1. 构建端创建 StudyAI，最开始它只有中文常用字 + 符号，没有任何知识。
2. 构建端开发者与它对话传授知识，StudyAI 自动记录并尝试总结。
3. 开发者输入 `build study`，StudyAI 把所有历史记录打包成 `.study`，客户端可以使用。
4. 这本质上是一个学习并接受外部知识的过程。

## 安装 / 构建

- 纯 Python 3.13，核心逻辑零第三方依赖。
- 已提供单文件可执行程序 `studyai.exe`（构建端与客户端合一）。
- 自行构建：

```bash
python -m venv venv && venv/Scripts/pip install nuitka
python -m nuitka --onefile --output-filename=studyai.exe studyai_cli.py
```

## 用法

### 构建端 —— 教它，然后导出

```bash
studyai.exe builder --name my-study --theme dark
# StudyAI:builder> 机器学习是人工智能的分支，使用大量数据训练模型。
# Recorded. Extracted 1 sentence(s). Key terms: 学习, 模型, 分支 ...
# StudyAI:builder> build study
# Built .study -> my-study.study (1 unit(s), 2 turn(s))
```

构建端内置命令：`build study`、`status`、`summary`、`exit`。
使用 `--resume file.study` 可在已有知识库上继续教学。

### 客户端 —— 加载并查询

```bash
studyai.exe client --file my-study.study --theme light
# StudyAI:client> 什么是机器学习
# [Match #0] 机器学习是人工智能的分支，使用大量数据训练模型。
#     机器学习是人工智能的分支，使用大量数据训练模型。
```

客户端内置命令：`info`、`list`、`exit`。无匹配的查询会如实返回「未在知识库中检索到相关内容」，
而不是编造答案。

## `.study` 文件格式

自描述、带校验和的二进制容器：

```
[8 字节 magic "STUDYAI\x01"] [4 字节 uint32 小端长度] [gzip(json 载荷)]
```

载荷字段：`version`、`name`、`created`、`builder`、`base_chars`、`vocab_hash`、
`knowledge[]`（每条含 `id, raw, sentences, bigrams, summary`）、`history[]`、`checksum`。
加载时依次校验 magic → 长度 → gzip → checksum → 版本，损坏即明确报错。

## 检索（纯启发式，无模型）

知识以**中文二元组（bigram）**建索引。查询时按二元组重叠度与各单位匹配，返回最相关结果。
纯 ASCII 或空查询返回空，因此客户端绝不会编造未被传授的内容。

## 测试

```bash
python run_tests.py   # ALL TESTS PASSED
```

覆盖：字表生成、知识抽取、`.study` 往返、损坏检测、检索正确性。

## 许可证

基于 **Available License** 发布 —— https://license.kscm.top/available.md

## English docs

See [README.md](./README.md).
