from .rule import *


class DanmuCounter:
    def __init__(self, name):
        self.name = name
        self.DanmuList = []
        self.TripleSixList = []
        self.DouyuList = []
        self.LuckyList = []

    def reset(self):
        self.DanmuList = []
        self.TripleSixList = []
        self.DouyuList = []
        self.LuckyList = []

    def count_danmu(self, content):
        if self.DanmuList:
            self.DanmuList[-1] += 1
            if any(word in content for word in Douyu_):
                self.DouyuList[-1] += 1
            if any(word in content for word in Lucky_):
                self.LuckyList[-1] += 1
            if any(word in content for word in Triple_):
                self.TripleSixList[-1] += 1

    def add_block(self):
        self.DanmuList.append(0)
        self.TripleSixList.append(0)
        self.DouyuList.append(0)
        self.LuckyList.append(0)

    def get_score(self, block_id=-1):
        return self.DouyuList[block_id] * ScoreRule_.douyu \
               + self.TripleSixList[block_id] * ScoreRule_.triple \
               + self.LuckyList[block_id] * ScoreRule_.lucky

    def get_count(self, block_id=-1):
        CountRes = namedtuple("CountRes", ["danmu", "triple", "lucky", "douyu"])

        return CountRes(self.DanmuList[block_id], self.TripleSixList[block_id],
                        self.LuckyList[block_id], self.DouyuList[block_id])