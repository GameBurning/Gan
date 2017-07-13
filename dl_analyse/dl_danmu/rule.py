from collections import namedtuple

# Danmu Rules
Douyu_ = ('时刻', '天天卡牌', '逗鱼')
Lucky_ = ('学不来', '狗')
Triple_ = ('66')

# File Path
LogFilePath_ = '~/Gan/video/output/'

# URL Rules
PlatformUrl_ = {
    "panda": "www.panda.tv/",
    "douyu": "www.douyu.com/",
    "zhanqi": "www.zhanqi.tv/"
}

# Score Rules
ScoreRuleTuple = namedtuple("ScoreRuleTuple", ["douyu", "triple", "lucky"])
ScoreRule_ = ScoreRuleTuple(50, 6, 2)
ScoreThreshold_ = 2000
Block_Size_In_Second_ = 45
Block_Num_Per_Video_ = 4


# Developer Mode
Record_Mode_ = True
