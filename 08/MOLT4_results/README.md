# 08号最终CSV

主文件为08.csv，包含全部阶段；csv/保留七段独立结果。
每段按有效击球的实际时间顺序，baseline保留前10、training前140、test前30。没有按分数挑选。
strength_value单位为O到B长度，angle_value单位为度；both同时保留两项。
缺少可靠评分证据的分量留空，strength_status/angle_status和needs_review保留原因及复核状态。
audit/uncapped为截取前的结果，只用于追溯；分析使用主文件或csv/中的最终结果。
原视频、录制日志和session未修改；完整逐帧证据保存在本项目本轮工作目录。
