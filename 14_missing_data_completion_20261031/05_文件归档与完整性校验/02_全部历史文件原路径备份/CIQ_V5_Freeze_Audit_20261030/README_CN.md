# V5 独立空间基准冻结与剩余实验工程

**源数据不修改。** 输入ZIP位于 `input/`；正式冻结以其中 `data/CIQ_ABC_V5_ACTIVE.gpkg` 为准。

打开 `V5_FORMAL_FREEZE_AND_REMAINING_EXPERIMENTS_CN.md` 查看结论；`V5_INDEPENDENT_AUDIT.json` 为机器验收报告。

重新运行：`python reproduce_independent_v5_audit.py input/CIQ_ABC_QGIS322_V5_ONE_WMP228_68_NODES_FULL_PROJECT(1).zip audit_rerun`。需 geopandas、pandas、pyproj、shapely。

本包的 `SOURCE_28_SHA256_CHECKS.csv`、节点/连接输出、V4对照、`V5_31_BLOCKS_EXPERIMENT_BACKLOG.csv` 和签名表是重新执行的可审核证据。旧 Stage 3–8 文件没有被写入或更改。
