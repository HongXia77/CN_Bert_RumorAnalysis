# 远程数据同步工作流

更新时间：2026-04-20

## 核心原则

- 远程主机作为长期在线的数据主节点
- 远程主机负责爬取、增量更新、保存原始文件
- 本机不做实时被动接收，只在需要时主动拉取最新副本
- 系统运行优先连接远程数据库，本机主要用于开发、训练和备份

## 当前远程现状

- 远程主机：`rehxx@10.51.221.116`
- 当前已验证目录：`/home/rehxx/monitor_piyao_pt/piyao_platform`
- 当前已验证脚本：`/home/rehxx/monitor_piyao_pt/piyao_sync_linux.py`
- 当前已建立标准根目录：`/home/rehxx/rumor_feeds`
- 当前已建立标准样板：`/home/rehxx/rumor_feeds/piyao_platform`

## 本地拉取脚本

脚本位置：

- `data/tools/pull_remote_platform_data.py`

配置模板：

- `data/tools/remote_sync_profile.example.json`
- 远程标准目录模板：`data/tools/remote_feed_layout.example.json`

### 推荐运行方式

PowerShell:

```powershell
$env:REMOTE_SYNC_PASSWORD="你的远程密码"
python data\tools\pull_remote_platform_data.py --config data\tools\remote_sync_profile.example.json
```

脚本会：

- 通过 SFTP 连接远程主机
- 遍历配置中的平台目录
- 仅下载远程端发生变化的文件
- 将同步清单写入 `output/remote_sync`

## 标准化后的同步目录

当前推荐把标准结构同步到：

```text
data/platform_feeds/<platform_name>/
```

例如：

```text
data/platform_feeds/piyao_platform/current/articles.jsonl
data/platform_feeds/piyao_platform/logs/sync.log
data/platform_feeds/piyao_platform/meta/latest_summary.json
```

完整标准见：

- `REMOTE_PLATFORM_LAYOUT_STANDARD.md`

## 当前同步输出

- 同步清单：`output/remote_sync/<profile>_manifest.json`
- 最近一次摘要：`output/remote_sync/<profile>_latest_summary.json`
- 历史运行记录：`output/remote_sync/runs/*.json`

## 后续扩展多平台

后续每增加一个平台，只需要在配置里新增一个平台块：

```json
{
  "name": "platform_x",
  "remote_dir": "/home/rehxx/rumor_feeds/platform_x",
  "local_dir": "data/platform_feeds/platform_x",
  "include": ["current/*.jsonl", "current/*.csv", "logs/*.log", "meta/*.json"]
}
```

建议统一远程目录结构：

```text
/home/rehxx/rumor_feeds/
  piyao_platform/
    current/
    normalized/
    logs/
    meta/
    snapshots/
    archive/
  hunan_piyao/
  shaanxi_piyao/
  food_rumor_platform/
```

这样本地拉取脚本不需要修改，只改配置即可。

## 安全建议

- 不要把 SSH 密码写进仓库文件
- 运行时通过环境变量传递密码
- 后续最好切换为 SSH key 登录
- 如果后面接入更多平台，优先统一到远程端目录，再由本机统一拉取
