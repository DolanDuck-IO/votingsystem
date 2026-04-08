# VotingSystem

一个面向信息安全竞赛与研究展示的可验证投票系统项目。

本仓库围绕目录中的三篇论文展开：

- `2026-613.pdf`：Haechi，基于承诺的无密钥线下可验证投票方案
- `2026-565.pdf`：Zeeperio，面向选举审计的紧凑证明与自动化验证方案
- `2026-545.pdf`：Aggios，基于聚合器与分区证明的可扩展公开可验证投票方案

当前项目已经实现了一套以 `2026-613` 为核心的 Python 原型框架，并为 `2026-565` 与 `2026-545` 的后续接入预留了明确的扩展接口。

在当前版本中，项目已经从纯脚本原型升级为：

- 一个可运行的 Python 核心投票框架
- 一个基于 `FastAPI + SQLite` 的可演示服务层
- 一个连接后端 API 的单页前端控制台
- 一组用于系统级接口验证的基础测试

## 项目定位

当前状态：`可运行原型（working prototype）`

已经具备：

- 端到端演示流程
- 选举清单与选票编码
- Pedersen 风格向量承诺层
- `cast / challenge` 投票流程
- 公共选举记录
- 聚合计票开封与公开验证
- `FastAPI` 服务接口
- `SQLite` 持久化存储
- 审计日志
- 单页前端演示页面
- 面向未来证明后端与聚合后端的扩展接口

尚未达到生产级：

- 真实零知识证明后端
- 服务化部署层
- 数据库持久化
- 面向选民/管理员/审计者的 Web 界面
- 链上或智能合约验证器
- Aggios 风格聚合器工作流

因此，本仓库目前更适合被理解为“架构完整、流程可跑通的研究型原型”，而不是可直接用于真实选举的最终系统。

## 项目目标

这个项目的目标，不只是复现论文中的某一个密码学细节，而是逐步发展为一个适合信息安全作品赛展示的完整系统，具备以下特点：

- 有清晰的密码学设计主线
- 有可解释的端到端投票与验证流程
- 有可替换、可扩展的证明与验证后端
- 有继续工程化、服务化、界面化的空间

换句话说，这个仓库既是论文研究的落地点，也是后续参赛作品的工程基础。

## 为什么以 2026-613 为核心

当前实现选择以 `2026-613 / Haechi` 作为系统主干，原因是它在工程上最适合作为第一阶段基础架构：

1. 载入选举配置
2. 设备采集选民选择
3. 将整张选票编码为向量
4. 对整张票生成单个承诺
5. 生成确认码链
6. 允许选民选择 `cast` 或 `challenge`
7. 将已投票记录到公共选举记录中
8. 在投票结束后公开聚合承诺与聚合开封
9. 由公共验证者检查计票一致性

相比一开始就直接进入 zk-SNARK 或聚合器协议实现，这一模型更容易搭建、演示和解释，也更适合作为竞赛项目的第一阶段版本。

## 架构概览

当前代码主要由以下几个核心组件组成：

- `ElectionManifest`
  定义选举项目、候选人、每个竞赛项的投票规则。

- `VotingDevice`
  模拟 Haechi 风格的投票设备，负责准备选票、生成确认码、支持 `cast/challenge`、维护运行时 tally。

- `PedersenContext`
  实现当前原型使用的承诺层，用于整票承诺和聚合开封验证。

- `ElectionRecord`
  存储公共选举记录，包括已投选票与挑战选票。

- `ElectionVerifier`
  负责验证确认码链、挑战票开封、聚合承诺以及最终 tally 开封。

- `Proof Backends`
  当前使用占位式证明对象来跑通完整数据流，后续可以替换为真实的密码学证明后端。

## 仓库结构

```text
.
|-- 2026-545.pdf
|-- 2026-565.pdf
|-- 2026-613.pdf
|-- PAPER_ANALYSIS.md
|-- README.md
|-- pyproject.toml
|-- src/
|   `-- haechi_voting/
|       |-- __init__.py
|       |-- api.py
|       |-- crypto.py
|       |-- demo.py
|       |-- device.py
|       |-- extensions.py
|       |-- main.py
|       |-- models.py
|       |-- proofs.py
|       |-- record.py
|       |-- serialization.py
|       |-- service.py
|       |-- static/
|       |   |-- app.js
|       |   |-- index.html
|       |   `-- styles.css
|       `-- verifier.py
`-- tests/
    |-- test_api_flow.py
    `-- test_demo_flow.py
```

## 快速开始

环境要求：

- Python `3.10+`

在 PowerShell 中运行演示：

```powershell
$env:PYTHONPATH = "src"
python -m haechi_voting.demo
```

运行测试：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

运行 API 服务：

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn haechi_voting.main:app --reload
```

默认服务启动后可访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/app`
- `http://127.0.0.1:8000/docs`

## 演示内容

当前 demo 会模拟以下过程：

- 1 张正常投出的选票
- 1 张被挑战的选票
- 1 张额外正常投出的选票
- 最终 tally 生成与公开验证

预期结果：

- `2` 张 cast ballots
- `1` 张 challenged ballot
- 验证通过

## API 能力

当前服务层已经提供以下核心接口：

- `GET /health`
- `GET /elections`
- `POST /elections`
- `GET /elections/{election_id}`
- `POST /elections/{election_id}/ballots/prepare`
- `POST /elections/{election_id}/ballots/{ballot_id}/cast`
- `POST /elections/{election_id}/ballots/{ballot_id}/challenge`
- `POST /elections/{election_id}/tally`
- `GET /elections/{election_id}/record`
- `GET /elections/{election_id}/verify`
- `GET /elections/{election_id}/audit-logs`

这些接口已经接入 SQLite 持久化，因此当前系统不再只是一次性脚本，而是具备了基础的服务化能力。

## 前端展示层

当前前端是一个直接挂载在 FastAPI 上的单页应用，用于评审展示和本地联调。

主要能力：

- 快速创建演示选举
- 浏览现有选举
- 动态渲染 ballot form
- 执行 `prepare / cast / challenge`
- 触发 `tally / verify`
- 查看公开记录、验证结果和审计日志

访问地址：

- `http://127.0.0.1:8000/app`

## 三篇论文与系统的对应关系

### 1. 论文 613：Haechi

这是当前项目的核心基础。

已经映射到系统中的内容包括：

- 整票承诺
- `cast-or-challenge` 工作流
- 公共选举记录
- 聚合承诺开封
- 公开 tally 验证

### 2. 论文 565：Zeeperio

这篇论文在当前项目中被视为“验证层升级方向”。

未来可接入方式：

- 用紧凑证明替换占位式 proof 对象
- 引入独立的 receipt proof 与 dispute proof 接口
- 接入自动化验证甚至链上验证

当前预留接入点：

- `src/haechi_voting/extensions.py`

### 3. 论文 545：Aggios

这篇论文在当前项目中被视为“聚合层升级方向”。

未来可接入方式：

- 增加 aggregator 角色
- 支持批量发布 tally
- 增加 inclusion acknowledgement 和 dispute handling
- 引入大规模场景下的分区证明验证

当前预留接入点：

- `src/haechi_voting/extensions.py`

## 安全说明

当前仓库主要展示的是：

- 系统结构
- 数据流
- 承诺式可验证流程
- 论文到工程实现的映射方式

它**尚未**实现论文中承诺的完整密码学安全性。

当前主要限制包括：

- 证明系统仍是占位实现
- 没有经过加固的部署模型
- 没有 trusted setup 管理
- 没有真实的选民身份认证子系统
- 没有完善的对抗性网络和设备威胁建模

因此，本项目目前不能用于真实选举场景。

## 开发路线图

如果要把它继续推进成更成熟的竞赛作品，建议按下面的顺序演进：

1. 用真实证明后端替换占位 proof。
2. ~~增加 `FastAPI` 等服务层。~~（已完成）
3. ~~增加 `SQLite` 或 `PostgreSQL` 等持久化存储。~~（已完成）
4. ~~增加适合评审展示的 Web 界面。~~（已完成基础部分）
5. 接入 Zeeperio 风格的紧凑验证后端。
6. 增加 Aggios 风格的聚合器模块。
7. 补充异常路径、安全路径、对抗场景测试。
8. 增加部署脚本、可复现实验数据和系统架构图。

## 文档说明

- `README.md`
  项目总览、使用说明与开发路线。

- `PAPER_ANALYSIS.md`
  三篇论文如何映射到系统设计中的详细分析，以及后续如何分阶段接入 565 与 545。

## 协作建议

推荐团队协作方式：

- 保持 Python 框架作为主集成层
- 将较重的密码学模块独立为单独模块或服务
- 通过 Pull Request 管理多人协作
- 将 proof backend 与 aggregation backend 视为相对独立的子系统

这样可以让不同方向的成员并行推进，而不至于频繁破坏主系统。

## License

当前仓库还没有加入许可证文件。

如果后续准备公开展示、多人协作或持续演进，建议尽快补充明确的开源许可证或比赛允许范围内的授权说明。
