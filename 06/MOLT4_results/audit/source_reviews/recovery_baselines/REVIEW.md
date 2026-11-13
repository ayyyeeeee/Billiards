# 两段 baseline strength 局部复核：保持空分

结论：01/03 的第 8 杆均有真实手部干预，现有原片不能恢复可靠的自由越轴速度或自然停点。**不建议集成任何候选 raw 包；主分析原诊断和所有 scalar 保持不变。**

- 01：检查 89–100 秒。96.800 秒球仍运动，距 Y 轴垂距约 26.06 cm；96.9 秒手靠近接触，97.0 秒前后抓住球，97.3 秒以后为搬回 O 的过程。冻结 f6 仅使用正常光检测（暗光门未启用），没有比原缓存多出可用缺测点。原 `assumed_stationary_hand` unresolved 保留。
- 03：检查 87–97 秒。约 93.2 秒来手接触球，其后运动已受到手干预；93.100 秒安全自由观测距 Y 轴垂距约 100.10 cm。拿前 92.700–92.884 秒有 11 个实际红球点能由冻结暗光轮廓补回，但仍没有自由越轴或可确认自然停点。原 `unexpected_longitudinal_cushion_before_crossing` unresolved 保留。

03 的 94.050 秒原点位于远处上库，源帧显示它不是实际球。f6 此时选到实际手/球接触区，hand_fraction=0.455；该轮廓只证明当前有非自由手接触，不能证明可靠的球中心。试探替换这一点会让原有 assumed-stop 分支输出约 0.473879 的假定拿球停点分数，这不是本次找到的可靠自然停点或自由越轴证据，因此明确拒绝、未采用。该试探单独保存为 `REJECTED_nonfree_hand_hypothesis.npz`，不得集成或当作恢复成功。

## 冻结证据

- `manual_review_manifest.json`：两例最终人工结论、输入/source/候选包校验值。
- 各段目录的 `manual_review.json`：原评分、未采用候选复算、原帧列表及逐点色像素/hand 证据。
- `original_source_frames/`：未绘制标记的源帧 PNG；源解码 PTS 与原缓存逐帧对应。
- `remeasure_contactsheet_*.jpg`：每 0.1 秒原片局部拼图。紫圈为原点，黄圈为当前 f6 的同帧实测点。
- `local_measurements.npz` / `frame_remeasurements.json`：原窗逐帧因果测量、方法、当前轮廓面积、真实 HSV 红像素支持、原/新行。
- `*_NOT_ADOPTED_review_candidate.npz`：完整 data/fps/quad/median 四数组。01 是零 patch 的未改数据参照；03 仅补 11 个拿前真实 missing 点，所有原已观测坐标、全部 PTS 和其他行不变。两条仍 unresolved；其他 attempts 的全部字段及所有 numeric scores 均精确不变。

局部检测使用冻结 counter `f6dddc5877b318f2607c5f23fb01650ac93d6a93cdcd139dd364c96e6e989043` 和 live_detection `6ae8428ba2eb48198be42506ab3d831868476702d83843a493002de9c887ba4e`，同帧轮廓支持函数来自已冻结的 participant07 提取脚本，全部代码、cfg、来源 hash 已记录。原片/缓存/cal/report/代码处理前后 hash 相同。没有写主 analysis、修改规则、平滑点位、伪造手接触或推算新的自由速度。

manifest SHA256：`b671cecb3f30e8c746255f1c51f9dffc1b9a29bad06395b838b23f2a0bd31c94`。
