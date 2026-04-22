# 远程多平台目录规范与统一产出结构

更新时间：2026-04-20

## 设计目标

- 远程主机长期在线，负责所有平台的采集与沉淀
- 每个平台使用统一目录骨架，方便后续扩展
- 本机同步逻辑不依赖具体平台名称，只依赖标准结构
- 保留兼容空间，不强行打断当前已经在跑的旧脚本

## 标准根目录

推荐远程统一根目录：

```text
/home/rehxx/rumor_feeds/
```

每个平台一个子目录：

```text
/home/rehxx/rumor_feeds/piyao_platform
/home/rehxx/rumor_feeds/hunan_piyao
/home/rehxx/rumor_feeds/shaanxi_piyao
/home/rehxx/rumor_feeds/food_rumor_platform
```

## 每个平台的标准子目录

```text
<platform_root>/
  current/
  normalized/
  logs/
  meta/
  snapshots/
  archive/
```

### 目录职责

- `current/`
  当前可直接使用的最新原始产物
- `normalized/`
  按统一字段清洗后的标准化数据
- `logs/`
  采集和更新日志
- `meta/`
  平台信息、最近一次摘要、文件说明
- `snapshots/`
  按日期生成的快照包
- `archive/`
  历史版本、旧文件归档

## 当前标准文件名

推荐至少统一这几类文件：

```text
current/articles.jsonl
current/articles.csv
logs/sync.log
meta/latest_summary.json
meta/platform_info.json
```

后续如果平台已经支持标准化清洗，可继续补：

```text
normalized/articles.normalized.jsonl
normalized/articles.normalized.csv
```

## `platform_info.json` 推荐字段

```json
{
  "platform_name": "piyao_platform",
  "display_name": "中国互联网联合辟谣平台",
  "source_category": "official",
  "source_url": "https://www.piyao.org.cn/",
  "language": "zh-CN",
  "layout_version": "v1"
}
```

## 当前兼容策略

- 旧脚本和旧目录可以继续跑
- 通过一次“标准目录初始化”把旧目录里的当前产物复制到新结构
- 本机同步脚本优先面向新结构
- 业务代码是否切到新结构，可以后续逐步迁移

## 本地同步建议

本地推荐把标准结构同步到：

```text
data/platform_feeds/<platform_name>/
```

例如：

```text
data/platform_feeds/piyao_platform/current/articles.jsonl
data/platform_feeds/piyao_platform/meta/latest_summary.json
```

这样可以避免和旧的 `data/piyao_platform` 平铺文件冲突。

## 脚本与模板

- 远程目录初始化脚本：
  - `data/tools/setup_remote_feed_layout.py`
- 远程布局模板：
  - `data/tools/remote_feed_layout.example.json`
- 本地拉取脚本：
  - `data/tools/pull_remote_platform_data.py`

## 推荐迁移节奏

1. 先保持旧目录持续产出，不中断现有远程爬虫
2. 在远程创建标准目录骨架
3. 把旧目录中的“当前产物”复制到标准结构
4. 本机开始从标准结构拉取
5. 等后续所有平台都接入后，再考虑让远程爬虫直接输出到标准结构
