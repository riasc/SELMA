import os
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import math
import itertools
from collections import Counter
from collections import OrderedDict
from decimal import Decimal
from statistics import median_high
from statistics import stdev
from statistics import mean


class Numbers:
    numbers = [] # files that contain the numbers
    matrix = np.empty((0,7)) 
    datum = []

    def __init__(self, path):
        # scan folder for files
        for root,dirs,files in os.walk("./numbers/"):
            for name in sorted(files):
                self.numbers.append(os.path.join(root,name))
        self.parseNumbers()

    def parseNumbers(self):
        for filename in self.numbers:
            with open(filename) as f:
                next(f) # exclude header
                for line in f:
                    cells = line.split("\t")
                    self.datum.append(cells[0]) # date
                    nrs = cells[1:8] # numbers
                    self.matrix = np.append(self.matrix,[nrs],axis=0).astype(int)
            f.close()


class OddEven:
    ### odd even ratio ###
    def detOddEvenRatio(self,number):
        countsOdd = 0 # count of odd numbers
        countsEven = 0 # count of even numbers
        for idx,val in enumerate(number):
            if idx < 6:
                if val % 2 == 0:
                    countsEven += 1
                else:
                    countsOdd += 1
        return (countsOdd,countsEven)
    
    def fillOddEvenDict(self,matrix,data):
        oddEvenDict = {}
        allOddEvenPairs = []
        for x in range(0,matrix.shape[0]):
            oddEvenRatio = self.detOddEvenRatio(matrix[x])
            allOddEvenPairs.append((data[x],oddEvenRatio))
            if oddEvenRatio in oddEvenDict:
                oddEvenDict[oddEvenRatio] += 1
            else:
                oddEvenDict[oddEvenRatio] = 1
       
        # sort dictionary by values
        oddEvenDict = OrderedDict(sorted(oddEvenDict.items(), key=lambda x: x[1]))
        # add proability to dictionary
        for key,value in oddEvenDict.items():
            oddEvenDict[key] = [oddEvenDict[key],oddEvenDict[key]/matrix.shape[0]]

        return (oddEvenDict,allOddEvenPairs)

    # write back to file
    def writeFreqToFile(self,path,tdraws):
        oddEvenHandle = open(path,"w")
        oddEvenHandle.write("total draws: " + str(tdraws) + "\noddeven\tcount\tratio\n")
        for idx,val in enumerate(self.freq):
            oddEvenHandle.write(str(val) + "\t" + str(self.freq[val][0]) + "\t" + str(self.freq[val][1]) + "\n")
        oddEvenHandle.close()

    def writeCmbsToFile(self,path):
        cmbsHandle = open(path,"w")
        for x in self.occ:
            cmbsHandle.write(str(x[0]) + "\t" + str(x[1]) + "\n")
        cmbsHandle.close()

    def __init__(self,matrix,data):
        print("\tcalculate OddEvenRatio") 
        (self.freq,self.occ) = self.fillOddEvenDict(matrix,data)

        # create folder in results
        odepath = r"./results/oddeven/"
        if not os.path.exists(odepath):
            os.makedirs(odepath)
        
        self.writeFreqToFile("./results/oddeven/frequency.txt", matrix.shape[0])
        self.writeCmbsToFile("./results/oddeven/occurrence.txt")


class Templates:
    def fillTemplatesDict(self,matrix,data):
        tdraws = matrix.shape[0]
        starts = {}
        templates = {}

        allStartTemplatesPairs = []

        for x in range(0,tdraws):

            (startCount,template) = self.getStartTemplate(matrix[x])

            allStartTemplatesPairs.append((data[x],startCount,tuple(template)))

            # add to starts
            if startCount not in starts:
                starts[startCount] = 1
            else:
                starts[startCount] += 1

            # add to templates
            if tuple(template) not in templates:
                templates[tuple(template)] = 1
            else:
                templates[tuple(template)] += 1
        
        # sort by value 
        starts = OrderedDict(sorted(starts.items(), key=lambda x: x[1]))
        templates = OrderedDict(sorted(templates.items(), key=lambda x: x[1]))

        # add probability
        for key,value in starts.items():
            starts[key] = [starts[key],starts[key]/tdraws]
        
        for key,value in templates.items():
            templates[key] = [templates[key],templates[key]/tdraws]

        return (starts, templates, allStartTemplatesPairs)

    def getStartTemplate(self,numbers):
        start = 0
        count = 0
        template = []

        for idx,val in enumerate(numbers):
            if idx < 6:
                group = self.getTemplateGroup(val)
                template.append(group)
                if idx == 0:
                    start = group
                    count = 1
                else:
                    if group == start:
                        count += 1

        return ((start,count),template)



    # templates
    def getTemplateGroup(self,number):
        if number <= 9:
            group = 0
        elif number <= 19:
            group = 1
        elif number <= 29:
            group = 2
        elif number <= 39:
            group = 3
        elif number <= 49:
            group = 4
        return group

    def writeFreqToFile(self,path,tdraws):
        #handlestarts.write("total draws: " + str(tdraws) + "\nstartsgroup\tcount\tratio\n")

        templatesHandle = open(path,"w")

        # starts
        templatesHandle.write("starts\tcounts\tprobability\n")
        for idx,val in self.starts.items():
            streak = str(idx[0]) * int(idx[1])
            templatesHandle.write(streak + "\t" + str(self.starts[idx][0]) + "\t" + str(self.starts[idx][1]) + "\n")
        templatesHandle.write("\n")

        # templates
        templatesHandle.write("templates\tcounts\tprobability\n")
        for idx,val in self.templates.items():
            templatesHandle.write(str(idx) + "\t")
            templatesHandle.write(str(val[0]) + "\t" + str(val[1]) + "\n")
        templatesHandle.close()

    def writeOccsToFile(self,path):
        occsHandle = open(path,"w")
        occsHandle.write("date\tstarts\ttemplates\n")
        for x in self.occ:
            occsHandle.write(str(x[0]) + "\t" + str(x[1][0]) * int(x[1][1]) + "\t" + str(x[2]) + "\n")
        occsHandle.close()


    def __init__(self, matrix, data):
        (self.starts, self.templates, self.occ) = self.fillTemplatesDict(matrix, data)
        
        # create folder in results
        odepath = r"./results/templates/"
        if not os.path.exists(odepath):
            os.makedirs(odepath)

        self.writeFreqToFile("./results/templates/frequency.txt", matrix.shape[0])
        self.writeOccsToFile("./results/templates/occurrence.txt")




def hist(matrix,data):
    print("create histogram")

    # create folder in results
    histpath = r"./results/hists/"
    if not os.path.exists(histpath):
        os.makedirs(histpath)


    # extract the years data
    years = []
    for date in data:
        year = date.split("-")[0]
        if not year in years:
            years.append(year)


    allyears = []

    for idx, val in enumerate(years):
        drawYear = {}
        for number in range(1,50):
            drawYear[number] = [0,[],[0]*11]

        positions = []
        matching = [i for i in data if val in i]
        for y in matching:
            positions.append(data.index(y))

        dat = data[positions[0]:positions[-1]+1]
        mat = matrix[positions[0]:positions[-1]+1]

        freq649 = [0] * 49
        freqSZ = [0] * 10
    
        yeardraws = 0

        for (y,z), value in np.ndenumerate(mat):
            if z < 6:
                freq649[value-1] += 1
                
                drawYear[value][0] += 1
                drawYear[value][1].append(y)

                if y <= 9:
                    drawYear[value][2][0] += 1
                elif y <= 19:
                    drawYear[value][2][1] += 1
                elif y <= 29:
                    drawYear[value][2][2] += 1
                elif y <= 39:
                    drawYear[value][2][3] += 1
                elif y <= 49:
                    drawYear[value][2][4] += 1
                elif y <= 59:
                    drawYear[value][2][5] += 1
                elif y <= 69:
                    drawYear[value][2][6] += 1
                elif y <= 79:
                    drawYear[value][2][7] += 1
                elif y <= 89:
                    drawYear[value][2][8] += 1
                elif y <= 99:
                    drawYear[value][2][9] += 1
                else:
                    drawYear[value][2][10] += 1

            else:
                freqSZ[value] += 1

    
        sort_orders = sorted(drawYear.items(), key=lambda x: x[1][0], reverse=True)

        allyears.append(drawYear)
        #print(allyears)

        yearHandle = open("./results/hists/"+str(val)+".txt","w")
        for entry in drawYear:
            print(entry)
        yearHandle.close()
       
        plt.bar(list(range(1,50)), freq649)
        plt.savefig("./results/hists/"+str(val)+"_649.png")
        plt.clf()


        plt.bar(list(range(0,10)), freqSZ)
        plt.savefig("./results/hists/"+str(val)+"_SZ.png")
        plt.clf()



class DrawDistance:
    def distBetweenDraws(self, matrix):
        print("distbetweendraws")
        dists = []
        occ = {}
        sumdist = {}

        for x in range(0,matrix.shape[0]):
            for idx,val in enumerate(matrix[x]):
                if idx < 6:
                    if val in occ:
                        if x > 0:
                            dists.append(x-occ[val][-1])
                        occ[val].append(x)
                    else:
                        occ[val] = [x]
        
            if len(dists) == 6:
                if sum(dists) in sumdist:
                    sumdist[sum(dists)] += 1
                else:
                    sumdist[sum(dists)] = 1
            dists = []

        sumdist = OrderedDict(sorted(sumdist.items(), key=lambda x: x[1]))
        
        # add probability
        tdraws = matrix.shape[0]
        for key,value in sumdist.items():
            sumdist[key] = [sumdist[key],sumdist[key]/tdraws]

        return (sumdist, occ)

    def writeSumDistToFile(self,path):
        sumdistHandle = open(path,"w")
        sumdistHandle.write("number\tfrequency\tprobability\n")
        for x in self.distance:
            sumdistHandle.write(str(x) + "\t" + str(self.distance[x][0]) + "\t" + str(self.distance[x][1]) + "\n")
        sumdistHandle.close()

    def writeDistToFile(self,path):
        distHandle = open(path,"w")
        for x in sorted(self.occurrence):
            distHandle.write(str(x) + "\t")
            for y in self.occurrence[x]:
                distHandle.write(str(y) + "\t")
            distHandle.write("\n")
        distHandle.close()
    
    
    def __init__(self, matrix):
        (self.distance,self.occurrence) = self.distBetweenDraws(matrix)
        # create folder in results
       
        sumdistpath = r"./results/distances/"
        if not os.path.exists(sumdistpath):
            os.makedirs(sumdistpath)
        
        self.writeSumDistToFile("./results/distances/sumdist.txt")
        self.writeDistToFile("./results/distances/dist.txt")




# determines the occurrences of each number 
def calcOcc(matrix):
    occ649 = {}
    occSZ = {}
    #iterate through matrix 
    for x in range(0,matrix.shape[0]):
        for idx,val in enumerate(matrix[x]):
            if idx < 6: # exclude SZ
                if val in occ649:
                    occ649[val].append(x)
                else:
                    occ649[val] = [x]
            else:
                if val != -1:
                    if val in occSZ:
                        occSZ[val].append(x)
                    else:
                        occSZ[val] = [x]
   
    # sort the dictionaries
    occ649 = dict(sorted(occ649.items()))
    occSZ = dict(sorted(occSZ.items()))

    return (occ649,occSZ)

def genNum(oddeven,templates,drawdist,tdraws):
    # determine the space of all solutions

    prediction = "./numbers.txt"
    hPrediction = open(prediction,"w")

    means = np.empty((0,6))
    # six number out of 1 to 49
    for combo in itertools.combinations(range(1,50),6):
        means = list(combo)

        draw = []

        sumdrawdist = 0
        for idx,val in enumerate(means):
            hPrediction.write(str(val) + "\t")

            sumdrawdist += (tdraws - drawdist.occurrence[val][-1])


        # add oddEvenRatio
        odeKey = oddeven.detOddEvenRatio(means)
        odeProb = oddeven.freq[odeKey][1]


        #add startTemplate
        (startKey,templateKey) = templates.getStartTemplate(means)
        if startKey in templates.starts:
            startProb = templates.starts[startKey][1]
        else:
            startProb = 0.0
        if tuple(templateKey) in templates.templates:
            templateProb = templates.templates[tuple(templateKey)][1]
        else:
            templateProb = 0.0

        distsum = 0
        # add distance draws
        if sumdrawdist in drawdist.distance:
            drawdistProb = drawdist.distance[sumdrawdist][1]
            distsum = drawdist.distance[sumdrawdist][0]
        else:
            drawdistProb = 0.0


        # generate probabilities 
        totalProb = odeProb * ((startProb * templateProb)/2) * drawdistProb
        hPrediction.write(str(odeProb) + "\t")
        hPrediction.write(str(startProb) + "\t")
        hPrediction.write(str(templateProb) + "\t")
        hPrediction.write(str(drawdistProb)+"(" + str(distsum) + ")" + "\t")
        hPrediction.write(str(totalProb) + "\n")


    hPrediction.close()
    
    #sort results 
    os.system("sort -k 11,11rg " + prediction + " > numbers_sorted.txt")


       

def main():
    print("##### Lottery Prediction #####")

    nrs = Numbers("./numbers") # create numbers object

    # extract submatrix
    newDevice = nrs.datum.index("2000-01-01")
    submat = nrs.matrix[newDevice:nrs.matrix.shape[0]]
    subdat = nrs.datum[newDevice:nrs.matrix.shape[0]]

    print("number of draws: " + str(submat.shape[0])) # list total number of draws
    print("from " + str(subdat[0]) + " to " + str(subdat[-1]))

    ode = OddEven(submat,subdat)
    tmpls = Templates(submat,subdat)

    #hist(submat,subdat)

    dist = DrawDistance(submat)

    genNum(ode,tmpls,dist,submat.shape[0])


main()
