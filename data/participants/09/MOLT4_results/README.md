# 09号最终CSV

主文件为09.csv，包含全部阶段；csv/保留七段独立结果。
每段按有效击球的实际时间顺序，baseline保留前10、training前140、test前30。没有按分数挑选。
strength_value单位为O到B长度，angle_value单位为度；both同时保留两项。
缺少可靠评分证据的分量留空，strength_status/angle_status和needs_review保留原因及复核状态。
audit/uncapped为截取前的结果，只用于追溯；分析使用主文件或csv/中的最终结果。
原视频、录制日志和session未修改；完整逐帧证据保存在本项目本轮工作目录。

训练138杆有效目标碰库；另2次在线确认经原帧复核为上方角袋消失，未确认球回到台面，不补为有效杆。
训练第25、30、49、68杆在确认自然停止前已被拿走；手搬过Y不能作为自由球越轴，strength保留空值。
训练第93杆和test both第15杆已用实际红球轮廓重测恢复自然停点；评分规则、模型及test both的angle未改变。
