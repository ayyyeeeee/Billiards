# 05号最终CSV

主文件为05.csv；csv/包含7段独立结果。
逐段按实际有效击球的时间顺序，baseline最多前10、training前140、test前30；不按分数挑选，不补造缺杆。
strength_value单位为O到B长度，angle_value单位为度；both独立保留两项。
缺少可靠证据的分量留空；各status、needs_review及tracking_observation_review保留复核原因。
未证实自然停止的手拿/视频结尾估计不作为strength分数，主分量留空；旧估计仅保留strength_unconfirmed_estimate列，不能作为实测停点使用。
audit/uncapped为截取前完整结果，仅用于追溯；正式分析请使用主文件或csv/。
原视频、session、录制日志、MOLT4_results1及08/09交付未改。完整原始观测仍在processing_info指定工作目录。

SHA清单为delivery_manifest.json；清单自身SHA保存在本轮工作目录deployment.json。
