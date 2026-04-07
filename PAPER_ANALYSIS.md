# 三篇论文的系统化分析与框架映射

## 一、三篇论文分别在讲什么

### 1. 2026-613: Haechi

这篇论文的核心是：

- 面向线下、设备中心的投票场景
- 不再使用加密选票和密钥管理
- 改用“对整张票做承诺，再对总票同态聚合”
- 选民通过 `cast-or-challenge` 验证设备是否诚实记录
- 计票时只公开聚合结果和聚合开封
- 用更紧凑的证明降低公开记录体积

它最适合作为系统主骨架，因为它直接定义了：

- 参与方
- 投票设备行为
- 选民交互流程
- 公告板数据结构
- 公开验证流程

### 2. 2026-565: Zeeperio

这篇论文的核心不是重写投票流程，而是：

- 把选举验证变成一组多项式约束
- 用 succinct proof / zk-SNARK 压缩验证证据
- 支持自动化验证，甚至链上验证
- 把 `receipt check`、`dispute resolution` 做成更细的证明接口

所以它更适合作为“验证层升级”，而不是替代 Haechi 主流程。

### 3. 2026-545: Aggios

这篇论文的核心不是设备端单票处理，而是：

- 引入聚合器 `aggregator`
- 由聚合器批量收集投票、批量发布计票
- 用分区证明 `EPA` 证明“所有合法投票被正确划分到候选人子集”
- 适合频繁、大规模、账本写入昂贵的场景

所以它更适合作为“聚合层升级”和“远程/代理式投票扩展”。

## 二、为什么以 613 作为框架基础

从工程角度看，613 最适合做主框架，原因有三点：

1. 它对系统边界定义最清晰
- manifest
- voting device
- election record
- voter verification
- tally verification

2. 它天然适合先做本地可运行原型
- 不依赖链
- 不依赖复杂的 trustee/key ceremony
- 不要求先实现 KZG、SNARK、SRS 管理

3. 它正好能给 565 和 545 留出清晰插槽
- 565 接到“证明与验证后端”
- 545 接到“批量聚合与发布后端”

## 三、当前 Python 框架如何对应 613

### 1. `models.py`

对应论文中的：

- election manifest
- contests
- ballots
- tally report
- verification report

### 2. `crypto.py`

对应论文中的：

- 向量承诺
- 聚合同态性
- ballot identifier hash
- confirmation code chain

当前实现使用了 Pedersen 风格向量承诺，用来模拟 613 的核心机制：

- 单票承诺
- 聚合承诺
- 聚合开封

### 3. `device.py`

对应论文中的设备端流程：

- `prepare_ballot()`
  生成选票向量、随机数、承诺、确认码、格式证明

- `cast_ballot()`
  将承诺放入公开记录，并累加到运行中的 tally

- `challenge_ballot()`
  公开开封信息，供选民审计，但不计入 tally

- `tally()`
  发布聚合承诺、聚合随机数、聚合票向量

### 4. `record.py`

对应论文中的 public election record / bulletin board。

### 5. `verifier.py`

对应论文中的公开验证流程：

- 检查 identifier hash
- 检查 confirmation code chain
- 检查 challenge ballot 开封
- 检查 cast ballot 聚合承诺
- 检查 aggregate opening

### 6. `proofs.py`

这里是整个框架最重要的预留点。

613 论文里真正关键的是“选票格式正确性证明”和“计票正确性证明”。当前代码里先提供了：

- `WellFormednessProofSystem`
- `TallyProofSystem`

这样以后可以无缝替换为：

- Haechi 压缩 Σ 协议证明
- Bulletproof / DekartProof 风格范围证明
- KZG/Plonk/SNARK 风格证明后端

## 四、565 的技术该如何应用到这个框架里

565 最适合接到 `proofs.py + verifier.py + extensions.py` 这条线上。

### 1. 应用点一：把逐条本地核验，升级成 succinct proof

当前框架的验证器是：

- 下载公开记录
- 逐条检查
- 再检查聚合开封

565 可以把这一步升级成：

- 将选举记录整理成多项式列
- 对所有约束一次性生成紧凑证明
- 验证器只验证一个短证明

落地位置：

- 替换 `PlaceholderWellFormednessProofSystem`
- 替换 `PlaceholderTallyProofSystem`

### 2. 应用点二：把 challenge/receipt/dispute 变成分离的证明接口

当前框架只有：

- cast
- challenge

565 的启发是把选民侧检查再细化成：

- `receipt proof`
- `print audit proof`
- `dispute proof`

这意味着后续可把 `verifier.py` 扩成三类 API：

- `verify_main_tally()`
- `verify_receipt()`
- `verify_dispute()`

### 3. 应用点三：自动化公共验证

613 默认是“任何人下载记录，本地验证”。

565 提供的升级方向是：

- 自动验证服务
- 智能合约验证
- 固定大小的公开证明

这在框架里对应：

- `extensions.py` 中的 `ZeeperioStyleBackend`

它的职责应该是：

1. 把 election record 转成 witness table / polynomial columns
2. 生成 succinct proof bundle
3. 发布给链上或其他公共验证器
4. 输出验证结果

### 4. 应用点四：更适合大规模公开审计

当选票数很大时，613 的公开记录虽然已经比传统加密投票小，但验证仍是“基于记录”的。

565 进一步优化的是：

- 验证成本不再线性跟票数增长
- 更适合自动化大规模复验

所以如果项目后面要走：

- 大型校园投票
- DAO/组织频繁投票
- 面向公众的长期公开审计

565 是优先级很高的第二阶段升级。

## 五、545 的技术该如何应用到这个框架里

545 最适合接到 `device -> record -> tally` 这一段之间，作为批量聚合层。

### 1. 应用点一：加入 aggregator 角色

当前 613 框架是：

- 设备直接把单票承诺写入 election record

545 可以改成：

- 选民先注册到某个 aggregator
- aggregator 收集很多票
- aggregator 只发布批量 tally 与 proof

这样可以显著减少公告板写入量。

### 2. 应用点二：用分区证明替代“每票直接上板”

545 的核心技术是 EPA：

- 证明一个承诺向量被正确拆分成多个互不重叠子向量
- 每个子向量对应一个候选人
- 所有合法投票都被覆盖、没有遗漏、没有重复

在当前框架里，这意味着可以新加一层：

- `AggregatorRegistry`
- `AggregatorBatch`
- `PartitionProof`
- `InclusionAcknowledgement`

这些都应该放在未来的 `aggregation/` 模块里。

### 3. 应用点三：把 tally 从“设备级”扩成“聚合器级”

当前 613 是设备自己维护：

- running tally
- running randomness

545 的应用方式是把这两个量迁移到聚合器：

- 每个聚合器维护自己的 batch tally
- 最后多个 batch 再汇总成全局 tally

这会让系统更适合：

- 分布式采集
- 代理式投票
- 高频投票
- 账本写入昂贵的环境

### 4. 应用点四：加入 inclusion ack 和 dispute

545 有一个很强的工程价值：它不仅证明 tally，还让选民对“自己那票是否被批量纳入”给出确认或提出争议。

在当前框架里可以这样扩展：

- cast 后不是立刻认为一定入账
- 而是聚合器返回 inclusion proof
- 选民回发 ack
- 若无 ack，进入 dispute 流程

这会比现在简单的 `challenge ballot` 更适合远程或聚合式场景。

### 5. 应用点五：Aggios-Split 可扩展更强隐私

如果以后要做的不只是线下设备投票，而是更接近远程、多方代理场景，那么 545 里的 `Aggios-Split` 很重要。

它的启发是：

- 一张票不要只交给一个聚合器
- 而是切成真实票 + 干扰票，分发给多个聚合器
- 只要串通的聚合器不超过阈值，就不能确定选民真实选择

这在当前框架中应作为第三阶段升级，而不是第一阶段直接实现。

## 六、三篇论文在系统里的推荐分层

推荐把系统分三层理解：

### 第一层：613 负责“主流程骨架”

- 选票输入
- 单票承诺
- cast/challenge
- election record
- aggregate opening

### 第二层：565 负责“证明与公开验证升级”

- proof compression
- receipt proof
- dispute proof
- automated verification
- optional on-chain verification

### 第三层：545 负责“批量聚合与规模扩展”

- aggregator
- batch tally
- partition proof
- voter inclusion ack
- dispute accountability

## 七、当前版本的边界与下一步

当前版本已经做到：

- 能运行
- 有 613 风格的数据流
- 有 commitment + confirmation chain + challenge + tally + verifier
- 有 565/545 的扩展接口

当前还没有做到：

- 真正的 zk well-formedness proof
- 真正的 compressed Sigma proof
- KZG / SNARK / EPA
- 链上验证
- aggregator 注册与批量提交

推荐下一步按下面顺序做：

1. 先把 `proofs.py` 替换为真实的 613 证明后端
2. 再扩 `verifier.py`，加入 receipt/dispute 细分接口
3. 再增加 aggregator 模块，引入 545 的批量聚合
4. 最后如果需要自动化公共验证，再接 565 风格的 succinct backend
