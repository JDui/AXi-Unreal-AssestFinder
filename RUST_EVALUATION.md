# Rust 重构性能评估

评估日期：2026-07-24

## 结论

Rust 适合重构“目录扫描 + 大文件精确比对”核心，但当前测试未证明整套应用会获得数量级提升。

- 128 MiB / 快速集：Rust 中位数 `0.0604s`，优化后 Python `0.0904s`，提升 `1.50x`。
- 512 MiB / 大文件集：Rust 中位数 `0.1123s`，优化后 Python `0.2856s`，提升 `2.54x`。
- 结果主要反映 Windows 文件缓存命中后的 CPU、内存复制、解释器开销。
- 冷盘、机械硬盘、网络盘场景主要受 I/O 限制，Rust 相对收益通常会收窄。
- 512 MiB 资产集的绝对节省约 `0.17s`。直接为 2.0 引入额外 EXE、IPC、构建矩阵与签名成本，收益不足。

因此：2.0 生产路径保留 Python 后台线程实现；Rust 原型保留为后续大项目验证入口。

## 公平性

两版均：

- 仅扫描 `.uasset`、`.umap`、`.uexp`、`.ubulk`。
- 先按相对路径和文件大小筛选。
- 相同大小文件按 1 MiB 块完整读取并逐字节比较。
- 最多使用 8 个工作线程。
- 交替执行 Python / Rust，取 5 或 7 次中位数。
- 测试集包含 1 个同大小修改、1 个新增、1 个删除，其余不变。

命令：

```powershell
cargo build --release --manifest-path rust_diff_probe\Cargo.toml

python benchmarks\benchmark_diff.py `
  --rust-bin rust_diff_probe\target\release\ue_asset_diff_probe.exe `
  --files 64 --size-mb 2 --runs 7

python benchmarks\benchmark_diff.py `
  --rust-bin rust_diff_probe\target\release\ue_asset_diff_probe.exe `
  --files 128 --size-mb 4 --runs 5
```

## 模块取舍

| 模块 | Rust 适配度 | 结论 |
|---|---:|---|
| 文件夹扫描、字节比对 | 高 | 已完成原型；达到接入阈值后可替换 |
| UE 二进制解析 | 中 | 可减少解析开销，但需先补齐格式回归样本 |
| 差异包复制 | 低 | 主要受磁盘写入限制 |
| Tk GUI、拖放 | 低 | 重写成本高，性能收益小 |

## 建议接入阈值

同时满足以下条件再接入 Rust 生产后端：

1. 真实项目资产总量至少 10 GiB 或文件数至少 100,000。
2. 冷缓存基准总耗时提升至少 `2.0x`，或用户等待减少至少 5 秒。
3. Rust 输出扩展为完整差异记录，并与 `asset_diff.py` 做交叉一致性测试。
4. PyInstaller 构建、Windows 签名、缺失二进制回退路径全部自动化。
