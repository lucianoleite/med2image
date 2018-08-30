mycolors = ( (0,0,0,0), (0,9/255.,204/255.,1), (0,214/255.,42/255.,1), (242/255.,217/255.,24/255.,1), (204/255.,129/255.,41/255.,1), (220/255.,24/255.,24/255.,1)) 

mycolors = ( (0,0,0,0), 
(0.168841, 0.168841, 0.972549,1), # azul medio
(0, 0.837995, 0.164996,1), # verdinho
(0.949996, 0.850004, 0.0939956,1), #amarelinho
(0.952941, 0.523522, 0.0941176,1), # laranja
(0.952941, 0.523522, 0.0941176), # laranja
(1, 0.682353, 0.682353, 1), # rosinha
(0.862745, 0.0941176, 0.0941176,1), #vermelho
(1, 0, 1, 1), #pink
(0, 0.5, 1, 1) #azul claro
) 

mycolors = ( (0,0,0,0), 
(0.168841, 0.168841, 0.972549,1), # azul medio
(0.952941, 0.523522, 0.0941176,1), # laranja (0, 0.837995, 0.164996,1), # verdinho
(0.949996, 0.850004, 0.0939956,1), #amarelinho
(0.949996, 0.850004, 0.0939956,1), #amarelinho (0.952941, 0.523522, 0.0941176,1), # laranja
(0.949996, 0.850004, 0.0939956,1), #amarelinho (0.952941, 0.523522, 0.0941176), # laranja
(0.862745, 0.0941176, 0.0941176,1), #vermelho (1, 0.682353, 0.682353, 1), # rosinha
(0, 0.837995, 0.164996,1), # verdinho (0.862745, 0.0941176, 0.0941176,1), #vermelho
(1, 0, 1, 1), #pink
(0.168841, 0.168841, 0.972549,1), # azul medio (0, 0.5, 1, 1) #azul claro 
) 
mycolors = ( (0,0,0,0), 
(0.168841, 0.168841, 0.972549,1), # azul medio
(0.952941, 0.523522, 0.0941176,1), # laranja (0, 0.837995, 0.164996,1), # verdinho
(0.949996, 0.850004, 0.0939956,1), #amarelinho
(0.949996, 0.850004, 0.0939956,1), #amarelinho (0.952941, 0.523522, 0.0941176,1), # laranja
(0.949996, 0.850004, 0.0939956,1), #amarelinho (0.952941, 0.523522, 0.0941176), # laranja
(0.862745, 0.0941176, 0.0941176,1), #vermelho (1, 0.682353, 0.682353, 1), # rosinha
(0, 0.837995, 0.164996,1), # verdinho (0.862745, 0.0941176, 0.0941176,1), #vermelho
(1, 0, 1, 1), #pink
(0.168841, 0.168841, 0.972549,1), # azul medio (0, 0.5, 1, 1) #azul claro 
) 
mycolors = (
(0,0,0,0),
(0.168841, 0.168841, 0.972549,1), # azul medio
(0, 0.837995, 0.164996,1), # verdinho
(1, 0, 1, 1), #pink
(0.949996, 0.850004, 0.0939956,1), #amarelinho
(1, 0.682353, 0.682353, 1), # rosinha
(0.952941, 0.523522, 0.0941176,1), # laranja
(0.862745, 0.0941176, 0.0941176,1), #vermelho
) 

# #mycolors = tuple(reversed(mycolors))
# global_color_dict = {
#     0 : (0,0,0,0),
#     1 : (0.168841, 0.168841, 0.972549,1), # azul medio
#     2 : (0, 0.837995, 0.164996,1), # verdinho
#     3 : (0.949996, 0.850004, 0.0939956,1), #amarelinho
#     4 : (0.952941, 0.523522, 0.0941176,1), # laranja
#     5 : (0.952941, 0.523522, 0.0941176,1), # laranja*********** ou seria vermelho?
#     6 : (1, 0.682353, 0.682353, 1), # rosinha
#     7 : (0.862745, 0.0941176, 0.0941176,1), #vermelho
#     8 : (1, 0, 1, 1), #pink
# }

import os
from ast import literal_eval
import re

#mycolors = tuple(reversed(mycolors))
def createColorDict(file):
    # leitura do arquivo
    global_color_dict = {}
    f = open(file, 'r')
    listColors = []
    for line in f:
        # separa palavras apenas fora do parenteses
        words = re.findall('\[[^\]]*\]|\([^\)]*\)|\"[^\"]*\"|\S+', line)
        for word in words:
            if "(" in word:
                # transforma texto em tupla
                newWord = literal_eval(word)
                # adiciona a nova palavra na lista
                listColors.append(newWord)

    # definindo o dicionario de cores
    counter=0
    for item in listColors:
        global_color_dict[counter] = item
        counter += 1
    # print global_color_dict
    return global_color_dict

# def getFileColor():
#     currentPath = os.path.abspath('')
#     subFolder = 'med2image'
#     for file in os.listdir("../med2image/med2image"):
#         if file.endswith(".txt"):
#             # print(file)
#             fullPath = os.path.join(currentPath,subFolder,file)
#             # print("createColorDict(fullPath)",createColorDict(fullPath))
#             return createColorDict(fullPath)

# global_color_dict = {
#     0 : (0,0,0,0),
#     1 : (0.168841, 0.168841, 0.972549,1), # azul medio
#     2 : (0, 0.837995, 0.164996,1), # verdinho
#     3 : (0.949996, 0.850004, 0.0939956,1), #amarelinho
#     4 : (0.952941, 0.523522, 0.0941176,1), # laranja
#     5 : (0.862745, 0.0941176, 0.0941176,1), #  vermelho?
#     6 : (1, 0.682353, 0.682353, 1), # rosinha
#     7 : (0.862745, 0.0941176, 0.0941176,1), #vermelho
#     8 : (1, 0, 1, 1), #pink
# }