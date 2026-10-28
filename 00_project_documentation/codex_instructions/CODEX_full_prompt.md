# Codex执行任务：JB–Singapore跨境无人机物流SCI研究——2026年5–9月真实气象数据下载、审计与XLSX交付

你是运行在我 Windows 本地工程里的 Codex 编程代理。现在请**真正运行、调试并完成历史气象数据的联网下载**，不是只给我代码或生成空白表。

## 0. 工程根目录及不得破坏的内容

现有工程根目录：`C:\Users\DELL\Desktop\20261019`

截图中至少有这些文件和目录：`.idea/`、`.venv/`、`__pycache__/`、`figures/`、`fig_01.py`、`main.py`、`plot_check.png`、`requirements.txt` 和 Word 文档。你必须先读取工程目录并理解现有结构；严禁覆盖、删除、重命名已有文件/目录或改动其他仿真逻辑。新功能以 `weather_pipeline/` 和 `data/weather_2026/` 为主要路径。如果我已把随附工具包解压到工程根目录，请直接使用其 `weather_pipeline/download_weather.py`、`weather_pipeline/points.csv`、`requirements-weather.txt`、`tests/test_weather_pipeline.py`，先检查并修复问题，不要重写无关模块。如果这些文件尚不存在，请按本提示的接口需求在新文件里实现。

## 1. 研究边界和必须取得的日期

* 日期（本地时间UTC+08:00）：2026年05月01日至2026年09月30日，包含5、6、7、8、9月，各月单独保存。
* 研究区域：Causeway（Johor Bahru CIQ–Woodlands）与 Second Link（Sultan Abu Bakar CIQ–Tuas），两条走廊均需包含马来西亚侧和新加坡侧。
* 暂定四个WGS84参考点，由 `weather_pipeline/points.csv` 提供：CW_MY、CW_SG、SL_MY、SL_SG。需要优先在原工程搜索我**已冻结的GIS点位/线路CSV或GeoJSON**；若找到，先汇报其坐标来源和是否可直接更新 `points.csv`，不要凭空编造新的无人机航路。四个参考点不是已获许可的跨境无人机航线。
* 数据必须为**真实API返回值**。严格禁止随机模拟、人工填充值、用天气代码推算“实测值”、将缺失数据设置为0、将1小时数据伪装成30分钟实测。
* 希望优先30分钟分辨率；如源数据只有逐小时，则**原样使用逐小时**，不可线性插值冒充真实观测。

## 2. 实际数据源及类型，不得混淆

A. Open-Meteo Historical Weather API（ERA5再分析）：

`https://archive-api.open-meteo.com/v1/archive`

官方说明：`https://open-meteo.com/en/docs/historical-weather-api`

务必设置 `models=era5`（不要默认best_match），`timezone=UTC`，`wind_speed_unit=ms`。取得 `precipitation,rain,wind_speed_10m,wind_speed_100m,wind_direction_10m,wind_direction_100m,wind_gusts_10m,temperature_2m,relative_humidity_2m`。ERA5风阵风是模式/再分析参数，**不是NEA观测的真实阵风**。ERA5原生时间间隔为1小时；网格分辨率约0.25°，切勿因为查询四个点就宣称有公里级独立实测。ERA5累计降雨标记的时间t代表前一小时 `[t-1h,t)`，需要专门保留降雨起止时间并在主表中对齐。下载时要额外覆盖UTC边界（北京时间/马来西亚时间=UTC+8）。

B. NASA POWER Hourly API（模型/卫星分析估算，非地面气象站）：

`https://power.larc.nasa.gov/api/temporal/hourly/point`

官方说明：`https://power.larc.nasa.gov/docs/services/api/temporal/hourly/`

使用 `time-standard=UTC`，不可使用默认LST。目标参数 `PRECTOTCORR,WS10M,WD10M,T2M,RH2M`；先探测参数有效性和数据范围，如NASA返回不支持的参数，查其官方参数目录并修复，不可写入假值。NASA POWER小时时间戳表示该小时开始，降雨参数为mm/hour。NASA的网格空间分辨率比口岸尺度粗，属于交叉对照源，不能当成第二个独立地面站。

C. 新加坡NEA data.gov.sg（**新加坡侧真实气象站观测**）：

* `https://api-open.data.gov.sg/v2/real-time/api/rainfall`
* `https://api-open.data.gov.sg/v2/real-time/api/wind-speed`
* `https://api-open.data.gov.sg/v2/real-time/api/wind-direction`

官方文档：https://guide.data.gov.sg/developer-guide/real-time-apis

`?date=YYYY-MM-DD`查询每天，必须持续跟随 `data.paginationToken`，直到没有下一页，记录每页成功/失败和重复分页令牌。不能只请求第一页面后声称下载了全日。NEA可选API Key放到系统环境变量 `DATAGOVSG_API_KEY`，通过HTTP请求头 `x-api-key` 读取；禁止把API Key写入文件、日志或代码。要处理429，限制调用速率，失败请求能够缓存/补抓/重试。

NEA风速原始单位knots，统一转m/s（系数约0.514444444）。官方风速数据是10分钟平均风的分钟级观测，**不能写成瞬时gust**。风向用向量/圆统计，不可直接取角度算术平均。雨量为5分钟更新的站点读数；先确认原始数据的统计区间和时间含义，才能按6个完整的5分钟值求30分钟累计mm，样本缺失必须保留NA并记录完整性，不可将NA当0。以新加坡侧点位到站点的球面距离匹配，保存站点ID、经纬度、距离和元数据；如无足够近的站点则缺失，不把最近站读数冒充口岸现场测量。马来西亚没有NEA实测覆盖，必须标注无MY侧实测；METMalaysia另行正式申请。

## 3. 先探测，再正式下载；不要只给下载链接

按此执行顺序工作：

1. `pwd`/检查根目录、Python版本、`.venv/Scripts/python.exe`、依赖与已有气象文件；保护当前工程。
2. 在虚拟环境安装独立 `requirements-weather.txt`，**不覆盖已有 `requirements.txt`**。
3. 运行离线单元测试：`python -m unittest discover -s tests -v`；错误必须修复再进行联网请求。
4. 对2026年5月运行 `--probe --months 5`，真正访问三种API：显示HTTP状态、返回字段、首末时间戳、风速和降雨样本、数据站点数和API实际记录数；区分NEA首分页和完整日数据。如果源拒绝连接/返回空数组，不要擅自认为下载成功，而要定位原因、尝试官方允许的请求结构。
5. 先正式下载5月：优先 `--months 5 --sources openmeteo,nasa` 得到小时数据，然后 `--months 5 --sources openmeteo,nasa,nea` 补充NEA实测。
6. 只有5月有真实数值、API原始JSON文件、时间覆盖率和可复核的xlsx后，才继续6、7、8、9月；出现API限流允许降低请求频率并断点续传。
7. 后续运行 `--months 6 7 8 9 --sources openmeteo,nasa,nea`；五个月一共五个XLSX，不能互相覆盖。
8. 如果特定源确实不可访问，**保留从其他源实际下载的数据**，在工作簿中标为部分完成，给我具体错误、HTTP状态、未取月份以及可复制的解决方式，不得编造完整率。

## 4. 输出目录和XLSX格式

输出到 `C:\Users\DELL\Desktop\20261019\data\weather_2026\`：

```
data/weather_2026/
  raw/openmeteo/         # 原始逐点逐月API JSON，gzip归档
  raw/nasa/              # 原始逐点逐月API JSON，gzip归档
  raw/nea/               # 原始逐日逐分页JSON，gzip归档
  processed/
    JB_SG_Weather_2026_05.xlsx
    JB_SG_Weather_2026_06.xlsx
    JB_SG_Weather_2026_07.xlsx
    JB_SG_Weather_2026_08.xlsx
    JB_SG_Weather_2026_09.xlsx
    # 同名 .qc.csv
  download.log
  api_log.csv
  probe_2026_05.json
```

每月XLSX至少保留：`Weather_Hourly`（四点逐小时风雨并列，每个字段明确来源）、`ERA5_Hourly`、`NASA_Hourly`、`NEA_30min_Wide`（SG两点实测30分钟风雨并列，如覆盖允许）、`NEA_30min`、`NEA_SelectedRaw`、`NEA_Station_Selection`、`NEA_Station_Metadata`、`NEA_Day_Status`、`CrossVal_NASA`、`CrossVal_NEA`、`QC_Coverage`、`Point_Metadata`、`Source_Registry`、`API_Log`和`README`。

所有数据包括 `point_id,corridor,timestamp_utc,timestamp_sgt,wind_speed_ms,wind_direction_deg,wind_gust_ms,rainfall_mm,source_class,source_url,station_id/ERA5 grid provenance` 中适用的字段；不适用或未获得的数据留NA。CSV/Excel必须可以按2026年5、6、7、8、9月分别读取。NASA与ERA5时间语义不同，必须按降水覆盖的**实际小时区间**匹配；风速对照需注明不同统计时段。NEA30分钟观测与ERA5一小时对照的样本数和不确定性需保留。

## 5. 科研核验验收条件

* 每个自然月每个参考点的理论小时槽位：5月744、6月720、7月744、8月744、9月720；30分钟槽位对应1488、1440、1488、1488、1440。主表四点对应每月 `4×小时数` 行。只有具有实际数值的时段才能计算有效覆盖率。
* 分别报告风速、阵风、降雨的真实有效记录数、缺测率、异常值（负降雨/不可能风速/风向越界）、NEA分页完成率。禁止把索引行当作实际天气记录。
* 核验口岸站点实际距离、ERA5返回的真实网格经纬度、ERA5 vs NASA 和 NEA vs ERA5对比。NASA粗网格可能多个参考点使用同一个格子，不得称为独立站点。
* 在每月工作簿列出准确的下载URL、数据类型（实测/再分析/估算）、时间戳规范、单位、官网、原始文件SHA256和请求日志。
* 检测月份边界是否错配，例如2026-05-01 00:00 +08与2026-04-30 16:00 UTC对应，5月31日23:00的降雨不能错误落到6月。
* 重要：若程序返回空白表、只有日期索引或只抓到NEA第一页，则**视为下载失败**，不能报告“已完成”。

## 6. 给我的最终回报格式

不要只返回“代码已准备”。必须在本机实际执行并逐月报告：

- 本机工程目录、Python环境与执行命令；
- 哪些API成功/失败（附具体错误及官方来源）；
- 五个月每个月ERA5、NASA、NEA风雨变量的**非空记录数和覆盖率**；
- 五个XLSX、原始JSON目录、下载日志的真实磁盘路径与大小；
- 数据质量问题与论文使用限制；
- 如仍有网络/鉴权问题，指出阻塞点并停留在诚实的“部分完成”状态。

请从检查现有工程开始，直到上述工作实际完成。不要覆盖我其他论文/交通仿真代码。
