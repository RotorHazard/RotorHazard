# Averager:  Tracks a running average, and min/max/last values

class Averager:
    """Tracks a running average, and min/max/last values"""
    def __init__(self, maxNumItems):
        self.dataItemsList = []
        self.maxNumItems = maxNumItems
        self.minVal = 0
        self.maxVal = 0
        self.lastVal = 0
        self.avgVal_ = 0
        self.dataItemsTotal = 0
        self.dataListLen = 0
        self.newAvgFlag = False

    def addItem(self, value):
        self.lastVal = value
        if self.dataListLen >= self.maxNumItems:
            if value < self.minVal:
                self.minVal = value
            elif value > self.maxVal:
                self.maxVal = value
            poppedVal = self.dataItemsList.pop(0)
            self.dataItemsTotal -= poppedVal
            self.dataItemsList.append(value)
            self.dataItemsTotal += value
            self.newAvgFlag = True
            # if popped value was min/max then get new min/max from list
            if poppedVal <= self.minVal:
                self.minVal = min(self.dataItemsList)
            if poppedVal >= self.maxVal:
                self.maxVal = max(self.dataItemsList)
        else:
            self.dataListLen += 1
            self.dataItemsList.append(value)
            self.dataItemsTotal += value
            if self.dataListLen > 1:
                if value < self.minVal:
                    self.minVal = value
                elif value > self.maxVal:
                    self.maxVal = value
                self.newAvgFlag = True
            else:
                self.minVal = self.maxVal = self.avgVal_ = value

    def getAvgVal(self):
        if self.newAvgFlag:
            self.newAvgFlag = False
            self.avgVal_ = self.dataItemsTotal / self.dataListLen
        return self.avgVal_

    def getIntAvgVal(self):
        return int(round(self.getAvgVal()))

    def __getitem__(self, item):
        return self.dataItemsList[item]

    def __len__(self):
        return self.dataListLen

if __name__ == "__main__":
    import random
    print("Starting test")
    averagerObj = Averager(500)
    for i in range(100000):
        val = random.randint(0, 1000)
        averagerObj.addItem(val)
        #print(str(averagerObj.dataItemsList) + "\t" + str(averagerObj.minVal) + " " + \
        #      str(averagerObj.getIntAvgVal()) + " " + str(averagerObj.maxVal) + " " + str(averagerObj.lastVal))
        if averagerObj.minVal != min(averagerObj.dataItemsList):
            print("*** min mismatch ***")
        if averagerObj.getIntAvgVal() != int(round(sum(averagerObj.dataItemsList)/len(averagerObj.dataItemsList))):
            print("*** avg mismatch ***")
        if averagerObj.maxVal != max(averagerObj.dataItemsList):
            print("*** max mismatch ***")
        if averagerObj.lastVal != val:
            print("*** last mismatch ***")
    print("Test complete")
