from collections import namedtuple

# Danmu Rules
Douyu_ = ('时刻', '天天卡牌', '闭嘴')
Lucky_ = ('学不来', '狗')
Triple_ = ('66')

# File Locations
LOGFILEDIR = '~/daily_log/'

# URL Rules
PlatformUrl_ = {
    "panda": "www.panda.tv/",
    "douyu": "www.douyu.com/",
}

# Score Rules
__ScoreRuleTuple = namedtuple("douyu", "triple", "lucky")
ScoreRule_ = __ScoreRuleTuple(50, 6, 2)
ScoreThreshold_ = 800
ANALYSIS_DURATION_ = 45
