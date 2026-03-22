import os
import numpy as np
import matplotlib.pyplot as plt

from selma.config import RESULTS_DIR


def hist(matrix,data):
    print("create histogram")

    # create folder in results
    histpath = os.path.join(RESULTS_DIR, "hists")
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

        yearHandle = open(os.path.join(histpath, str(val)+".txt"),"w")
        for entry in drawYear:
            print(entry)
        yearHandle.close()

        plt.bar(list(range(1,50)), freq649)
        plt.savefig(os.path.join(histpath, str(val)+"_649.png"))
        plt.clf()


        plt.bar(list(range(0,10)), freqSZ)
        plt.savefig(os.path.join(histpath, str(val)+"_SZ.png"))
        plt.clf()
