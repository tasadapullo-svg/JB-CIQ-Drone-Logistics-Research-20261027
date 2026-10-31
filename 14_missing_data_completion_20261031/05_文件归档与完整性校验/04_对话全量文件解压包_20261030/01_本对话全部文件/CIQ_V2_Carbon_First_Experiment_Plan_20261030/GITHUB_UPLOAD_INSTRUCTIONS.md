# GitHub 更新方法 — 不覆盖历史工程

原仓库：https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027
固定历史 commit：`4569817b8145efe2ae06f4b21addc1986f971c12`

建议新增根目录 `11_v2_carbon_first_experiments/` 并把本包内容移入，不删除原有任何历史文件。

```bash
# 在克隆后的项目根目录下：
mkdir -p 11_v2_carbon_first_experiments
# 将本包解压文件复制进入上述新文件夹（不覆盖旧 Stage3–8）
git add 11_v2_carbon_first_experiments
git commit -m "Plan V2 petrol-road vs hybrid UAV carbon-first experiments"
git push origin main
```

**上传每次节点结果前必做**：
1. 检查是否含私人 API key、证书、token、许可敏感材料、不可再分发源数据。
2. 运行 `verify_stage.py` 记录输入存在性与字段检查。
3. 运行 SHA256 manifest 记录输入输出、脚本版本、随机种子和时区。
4. 将实验输出与审计报告放回对应 `STAGES/V2_Sxx/outputs/`；不把原始源数据替换为改写版。
5. 对大文件遵守既有仓库的 20 MiB split 约定。

在真实三分区 QGIS 工程、燃油 M0 和两款无人机任务能耗证据未冻结前，任何阶段保持 HOLD，不要运行正式碳结果。
