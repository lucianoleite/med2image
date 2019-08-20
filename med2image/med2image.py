# NAME
#
#        med2image
#
# DESCRIPTION
#
#        'med2image' converts from medical image data files to
#        display-friendly formats (like png and jpg).
#
# HISTORY
#
# 23 February 2015
# o Initial design and coding.
#

# System imports
import os
import glob
import numpy as np
import re

# System dependency imports
import nibabel as nib
import dicom
import pylab
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
# Project specific imports
from . import error
from . import message as msg
from . import systemMisc as misc
from .color_map import createColorDict
from math import ceil
import math
import numpy
import collections
from PIL import Image

class med2image(object):
    """
        med2image accepts as input certain medical image formatted data
        and converts each (or specified) slice of this data to a graphical
        display format such as png or jpg.

    """

    _dictErr = {
        'inputFileFail'   : {
            'action'        : 'trying to read input file, ',
            'error'         : 'could not access/read file -- does it exist? Do you have permission?',
            'exitCode'      : 10},
        'emailFail'   : {
            'action'        : 'attempting to send notification email, ',
            'error'         : 'sending failed. Perhaps host is not email configured?',
            'exitCode'      : 20},
        'dcmInsertionFail': {
            'action'        : 'attempting insert DICOM into volume structure, ',
            'error'         : 'a dimension mismatch occurred. This DICOM file is of different image size to the rest.',
            'exitCode'      : 20},
        'ProtocolNameTag': {
            'action'        : 'attempting to parse DICOM header, ',
            'error'         : 'the DICOM file does not seem to contain a ProtocolName tag.',
            'exitCode'      : 30},
        'PatientNameTag': {
            'action': 'attempting to parse DICOM header, ',
            'error': 'the DICOM file does not seem to contain a PatientName tag.',
            'exitCode': 30},
        'PatientAgeTag': {
            'action': 'attempting to parse DICOM header, ',
            'error': 'the DICOM file does not seem to contain a PatientAge tag.',
            'exitCode': 30},
        'PatientNameSex': {
            'action': 'attempting to parse DICOM header, ',
            'error': 'the DICOM file does not seem to contain a PatientSex tag.',
            'exitCode': 30},
        'PatientIDTag': {
            'action': 'attempting to parse DICOM header, ',
            'error': 'the DICOM file does not seem to contain a PatientID tag.',
            'exitCode': 30},
        'SeriesDescriptionTag': {
            'action': 'attempting to parse DICOM header, ',
            'error': 'the DICOM file does not seem to contain a SeriesDescription tag.',
            'exitCode': 30}
    }

    # Custom constants
    NON_SEGMENTED = 'Projecao Tomografica'
    SEG_PHASES = 'Projecao Segmentada Fases'
    SEG_PORE = 'Projecao Segmentada Poro'
    SEG_PORE_LABELED = 'Projecao Segmentada Pore Labeled'
    SEG_MINERALS = 'Projecao Segmentada Minerais'
    COLORED_TYPES = [SEG_PHASES, SEG_PORE_LABELED, SEG_MINERALS]
    SEGMENTED =  COLORED_TYPES + [SEG_PORE]
    NON_COLORED_TYPES = [NON_SEGMENTED, SEG_PORE]
        
    def log(self, *args):
        '''
        get/set the internal pipeline log message object.

        Caller can further manipulate the log object with object-specific
        calls.
        '''
        if len(args):
            self._log = args[0]
        else:
            return self._log

    def name(self, *args):
        '''
        get/set the descriptive name text of this object.
        '''
        if len(args):
            self.__name = args[0]
        else:
            return self.__name

    def description(self, *args):
        '''
        Get / set internal object description.
        '''
        if len(args):
            self._str_desc = args[0]
        else:
            return self._str_desc

    def log(self): return self._log

    @staticmethod
    def urlify(astr, astr_join = '_'):
        # Remove all non-word characters (everything except numbers and letters)
        astr = re.sub(r"[^\w\s]", '', astr)
        
        # Replace all runs of whitespace with an underscore
        astr = re.sub(r"\s+", astr_join, astr)
        
        return astr

    def __init__(self, **kwargs):
        self.slice_number               = -1
        self.mycm                       = None # modifies default Greys_r colormap. It can map blue color for lower values
                                               # if NON_SEGMENTED or generates a colormap based on the colormap file
        #
        # Object desc block
        #
        self._str_desc                  = ''
        self._log                       = msg.Message()
        self._log._b_syslog             = True
        self.__name                     = "med2image"

        # Directory and filenames
        self._str_workingDir            = ''
        self._str_inputFile             = ''
        self._str_outputFileStem        = ''
        self._str_outputFileType        = ''
        self._str_outputDir             = ''
        self._str_inputDir              = ''

        self._b_convertAllSlices        = False
        self._str_sliceToConvert        = ''
        self._str_frameToConvert        = ''
        self._sliceToConvert            = -1
        self._frameToConvert            = -1

        self._str_stdout                = ""
        self._str_stderr                = ""
        self._exitCode                  = 0

        # The actual data volume and slice
        # are numpy ndarrays
        self._b_4D                      = False
        self._b_3D                      = False
        self._b_DICOM                   = False
        self._Vnp_4DVol                 = None
        self._Vnp_3DVol                 = None
        self._Mnp_2Dslice               = None
        self._dcm                       = None
        self._dcmList                   = []

        # A logger
        self._log                       = msg.Message()
        self._log.syslog(True)

        # Flags
        self._b_showSlices              = False
        self._b_convertMiddleSlice      = False
        self._b_convertMiddleFrame      = False
        self._b_reslice                 = False
        self.func                       = None #transformation function

        #Custom attributes for colored segmentations
        self.segmentationType           = None # to check if is colored 
        self.colorTxt                   = None # to customize colormap
        self.blueLimit                  = 60   # to customize grayscale with blue spots
        # self.maxMatrixValue             = None # can represent the number of phases (SEG_MINERALS/SEG_PHASES) or simply
        #                                        # the greatest value on the matrix (NON_SEGMENTED,SEG_PORE_LABELED)
        # self.minMatrixValue             = None # usada para poros azuis
        self.minAllowedValue            = 0 # assumindo que seja 0. Valores positivos bugam algumas coisas, negativos
                                            # provavelmente tb

        # self.segmentationType       = value
        for key, value in kwargs.items():
            if key == "inputFile":          self._str_inputFile         = value
            if key == "outputDir":          self._str_outputDir         = value
            if key == "outputFileStem":     self._str_outputFileStem    = value
            if key == "outputFileType":     self._str_outputFileType    = value
            if key == "sliceToConvert":     self._str_sliceToConvert    = value
            if key == "frameToConvert":     self._str_frameToConvert    = value
            if key == "showSlices":         self._b_showSlices          = value
            if key == 'reslice':            self._b_reslice             = value
            if key == 'segmentationType':   self.segmentationType       = value.replace('_',' ') # recebe Projecao_Segmentada_Fases mas testa Projecao Segmentada Fases
            if key == 'colorTxt':           self.colorTxt               = value # path/to/colormap.txt
            if key == 'blueLimit':          self.blueLimit              = int(value) # valor limite para definir poro como azul

        if self._str_frameToConvert.lower() == 'm':
            self._b_convertMiddleFrame = True
        elif len(self._str_frameToConvert):
            self._frameToConvert = int(self._str_frameToConvert)

        if self._str_sliceToConvert.lower() == 'm':
            self._b_convertMiddleSlice = True
        elif len(self._str_sliceToConvert):
            self._sliceToConvert = int(self._str_sliceToConvert)

        self._str_inputDir               = os.path.dirname(self._str_inputFile)
        if not len(self._str_inputDir): self._str_inputDir = '.'
        str_fileName, str_fileExtension  = os.path.splitext(self._str_outputFileStem)
        if len(self._str_outputFileType):
            str_fileExtension            = '.%s' % self._str_outputFileType

        if len(str_fileExtension) and not len(self._str_outputFileType):
            self._str_outputFileType     = str_fileExtension

        if not len(self._str_outputFileType) and not len(str_fileExtension):
            self._str_outputFileType     = '.png'

    def run(self):
        '''
        The main 'engine' of the class.
        '''

    def echo(self, *args):
        self._b_echoCmd         = True
        if len(args):
            self._b_echoCmd     = args[0]

    def echoStdOut(self, *args):
        self._b_echoStdOut      = True
        if len(args):
            self._b_echoStdOut  = args[0]

    def stdout(self):
        return self._str_stdout

    def stderr(self):
        return self._str_stderr

    def exitCode(self):
        return self._exitCode

    def echoStdErr(self, *args):
        self._b_echoStdErr      = True
        if len(args):
            self._b_echoStdErr  = args[0]

    def dontRun(self, *args):
        self._b_runCmd          = False
        if len(args):
            self._b_runCmd      = args[0]

    def workingDir(self, *args):
        if len(args):
            self._str_workingDir = args[0]
        else:
            return self._str_workingDir

    def get_output_file_name(self, **kwargs):
        index   = 0
        frame   = 0
        str_subDir  = ""
        for key,val in kwargs.items():
            if key == 'index':  index       = val 
            if key == 'frame':  frame       = val
            if key == 'subDir': str_subDir  = val
        
        if self._b_4D:
            str_outputFile = '%s/%s/%s-frame%03d-slice%03d.%s' % (
                                                    self._str_outputDir,
                                                    str_subDir,
                                                    self._str_outputFileStem,
                                                    frame, index,
                                                    self._str_outputFileType)
        else:
            str_outputFile = '%s/%s/%s-slice%03d.%s' % (
                                        self._str_outputDir,
                                        str_subDir,
                                        self._str_outputFileStem,
                                        index,
                                        self._str_outputFileType)
        return str_outputFile

    def dim_save(self, **kwargs):
        dims            = self._Vnp_3DVol.shape
        self._log('Image volume logical (i, j, k) size: %s\n' % str(dims))
        str_dim         = 'z'
        b_makeSubDir    = False
        b_rot90         = False
        indexStart      = -1
        indexStop       = -1
        for key, val in kwargs.items():
            if key == 'dimension':  str_dim         = val
            if key == 'makeSubDir': b_makeSubDir    = val
            if key == 'indexStart': indexStart      = val 
            if key == 'indexStop':  indexStop       = val
            if key == 'rot90':      b_rot90         = val
        
        str_subDir  = ''
        if b_makeSubDir: 
            str_subDir = str_dim
            misc.mkdir('%s/%s' % (self._str_outputDir, str_subDir))

        dim_ix = {'x':0, 'y':1, 'z':2}
        if indexStart == 0 and indexStop == -1:
            indexStop = dims[dim_ix[str_dim]]

        # # getting max value for using in SEG_MINERALS
        # # if not self.maxMatrixValue and self.segmentationType == self.SEG_MINERALS:
        # if not self.maxMatrixValue and self.segmentationType in self.COLORED_TYPES:
        #     self.maxMatrixValue = np.amax(self._Vnp_3DVol) # number of phases

        # if not self.minMatrixValue and self.segmentationType in self.SEGMENTED:
        #     self.minMatrixValue = np.amin(self._Vnp_3DVol)

        # print("--------------self.minMatrixValue",self.minMatrixValue)
        # print("--------------self.maxMatrixValue",self.maxMatrixValue)

        if self.segmentationType in self.COLORED_TYPES:
            global_color_dict = createColorDict(self.colorTxt)
            # print("---------------------global_color_dict",global_color_dict)

            self.mycolors = list(global_color_dict.values())
            # self.mycolors = getFileColor()

            for i in range(0, dims[dim_ix['z']]):
                self.slice_number = i
                self._Mnp_2Dslice = self._Vnp_3DVol[:, :, i]

                slice_keys = numpy.unique(self._Mnp_2Dslice)
                
                for key in slice_keys:
                    if not key in self.d:
                        self.d[key] = []
                    self.d[key].append(self.slice_number)

            color_dict = {}
            for k,v in self.d.items():
                if k > 6 :
                    break 
                #print ("pore: ", k,  "len slices: ", len(v), " slices: ", v)
        
            global_colors = list(global_color_dict.values())

            if global_color_dict[0] == (0,0, 0, 0):
                transparency, global_colors = global_colors[:1], global_colors[1:]
            else:
                transparency = []
            num_colors =  len(global_colors)
            num_phases = len(self.d.items())

            # self.mycolors = transparency + list( global_colors * math.ceil( float(num_phases)/num_colors))[:num_phases] # DEPRECATED?

            # self.mycm = LinearSegmentedColormap.from_list('custom_color_map', self.mycolors ,N=len(self.mycolors)) # DEPRECATED?

            '''
            print ("The original colormap has len =  ", num_colors)
            print ("The original colormap is =  ", transparency, global_colors)
            print ("The # of phases in the input =   ", num_phases)
            print ("The extended color map has len = ", len(self.mycolors))
            '''
            # print( '[355] self.mycm(0)',self.mycm(0))
            # print( 'self.mycm(1)',self.mycm(1))
            # print( 'self.mycm(2)',self.mycm(2))
            # print( 'self.mycm(3)',self.mycm(3))
            # print( 'self.mycm(4)',self.mycm(4))
            # print( 'self.mycm(5)',self.mycm(5))
            # print( 'self.mycm(6)',self.mycm(6))
            # print( 'np.unique(self._Vnp_3DVol)',np.unique(self._Vnp_3DVol))

        for i in range(indexStart, indexStop):
        #for i in range(0, 20):

            self.slice_number = i
            if str_dim == 'x':
                self._Mnp_2Dslice = self._Vnp_3DVol[i, :, :]
            elif str_dim == 'y':
                self._Mnp_2Dslice = self._Vnp_3DVol[:, i, :]
            else:
                self._Mnp_2Dslice = self._Vnp_3DVol[:, :, i]

            self.process_slice(b_rot90)
            str_outputFile = self.get_output_file_name(index=i, subDir=str_subDir)

            self.slice_save(str_outputFile)
        
        # counting number of files in current dim path and storing in total.txt
        try:
            fullPathDim = os.path.dirname(str_outputFile)
            totalFilePath = os.path.join(fullPathDim,'total.txt')
            if os.path.isfile(totalFilePath):
                os.remove(totalFilePath)
            numberOfFiles = len([name for name in os.listdir(fullPathDim) if os.path.isfile(os.path.join(fullPathDim, name))])
            f = open(totalFilePath, 'w')
            f.write(str(numberOfFiles))
            f.close
        except Exception as ex:
            print("[dim_save] There was an error generating total.txt ",ex)

    def process_slice(self, b_rot90=None):
        '''
        Processes a single slice.
        '''
        #Entra aqui
        if b_rot90:
            #Entra aqui
            self._Mnp_2Dslice = np.rot90(self._Mnp_2Dslice)
        if self.func == 'invertIntensities':
            # Nao entra aqui
            self.invert_slice_intensities()

    d = collections.OrderedDict()
    def slice_save(self, astr_outputFile):
        '''
        Saves a single slice.

        ARGS

        o astr_output
        The output filename to save the slice to.
        '''
        self._log('Outputfile = %s\n' % astr_outputFile)
        fformat = astr_outputFile.split('.')[-1]
        if fformat == 'dcm':
            if self._dcm:
                self._dcm.pixel_array.flat = self._Mnp_2Dslice.flat
                self._dcm.PixelData = self._dcm.pixel_array.tostring()
                self._dcm.save_as(astr_outputFile)
            else:
                raise ValueError('dcm output format only available for DICOM files')
        else:
#-
            #print (cm.Greys_r)
            #print (mycm)
            # print ("[med2image 474] self._Mnp_2Dslice",self._Mnp_2Dslice[620])
            # print ("[med2image 475] self._Mnp_2Dslice",len(self._Mnp_2Dslice))
            # print ("[med2image 476] astr_outputFile",astr_outputFile)
            #print (self._str_sliceToConvert )
            #print (numpy.unique(self._Mnp_2Dslice))
            #len(d)
            # for key in slice_keys:
            #     if key in global_color_dict:
            #         slice_color_dict[key] = global_color_dict[key]
            # if len(slice_keys) <= 1:
            #     print ('a')
            #     slice_color_dict = global_color_dict.copy()
            # print("self.d len ", len(self.d))
            # slice_color_dict = global_color_dict.copy()
            # mycolors = list(slice_color_dict.values())*50
            #print ("len slice_keys =", len(slice_keys))          
            
            #pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap = cm.Greys_r)
            #pylab.imsave('/home/luciano/nifti_data/MYCM-output.png', self._Mnp_2Dslice, format=fformat, cmap = mycm)

            # print('np.unique(self._Mnp_2Dslice)', np.unique(self._Mnp_2Dslice))
            flagRemoveTransparency = False  # remove fundo pixel a pixel (tipos: Segmentada Poro e Projecao Tomografica;
                                            # outros tipos: deve usar o valor 0 mapeado na cor (0,0,0,0) pelo colormap


            # unique = np.unique(self._Mnp_2Dslice)
            # print(">>>>>>>>>>>>>>unique",unique)

            ## Correcao do colormap de tons de cinza que para matrizes que nao tenha o valor maximo 255
            # Copia o colormap de tons de cinza, exceto para o valor 0, que sera mapeado em transparencia
            if self.segmentationType in self.NON_COLORED_TYPES:
                try:
                    # sliceUniqueValues = np.unique(self._Mnp_2Dslice)
                    # greyValuesForSlice = [(0, 0, 0, 0)] + list(map(cm.Greys_r, sliceUniqueValues))
                    sliceMaxValue = np.amax(self._Mnp_2Dslice)
                    if sliceMaxValue == 0:
                        greyValuesForSlice = [(0, 0, 0, 0)] + [(1,1,1,1)]
                    else:
                        greyValuesForSlice = [(0, 0, 0, 0)] + list(map(cm.Greys_r, range(1,sliceMaxValue)))
                    # print("----------[med2image] sliceMaxValue",sliceMaxValue)
                    # print("----------[med2image] greyValuesForSlice",greyValuesForSlice)

                    ModifiedGreys_r = LinearSegmentedColormap.from_list('newcmap', greyValuesForSlice, N=len(greyValuesForSlice))
                except Exception as ex:
                    print("[med2image] Ocorreu um erro nao esperado na geracao colormap cinza", ex)
                    ModifiedGreys_r = cm.Greys_r
            else:
                ModifiedGreys_r = cm.Greys_r

            if self.segmentationType == self.SEG_PORE_LABELED:
                # pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap = self.mycm)
                unique = np.unique(self._Mnp_2Dslice)

                # debug = False
                # if "x/" in astr_outputFile:
                #     debug = True

                # Para funcionar corretamente, devemos eliminar do colormap as cores que nao serao usadas na matriz atual
                sliceColors = []
                transparency = self.mycolors[0]
                nonTransparentColors = self.mycolors[1:]
                nonTransparentColorsLen = len(nonTransparentColors)

                lastMin = 1
                for index,value in enumerate(unique):
                    # As cores se repetem a cada index = N * len(self.mycolors)
                    # if debug:
                    #     print("---------------------[med2image 551] value",value)
                    if value == 0:
                        sliceColors.append(transparency)
                    else:
                        nonTransparentColorsIndex = (value - 1) %  nonTransparentColorsLen
                        # if debug:
                        #     print("-------------[med2image 552] nonTransparentColors[nonTransparentColorsIndex]",nonTransparentColors[nonTransparentColorsIndex])
                        for innerIndex in range(lastMin,value+1):
                            # Adiciona cores aos valores intermediarios, mesmo que nao sejam usadas (provavelmente tem uma solucao melhor)
                            # Se nao fizer esse trecho, mapeia 0 - transp; 1 - cor 1; 2 - cor 2; etc
                            sliceColors.append(nonTransparentColors[nonTransparentColorsIndex])
                        lastMin = value + 1

                # mapeamento 1 cor : 1 intervalo de valor, ja adicionados os valores e cores que nao serao usados
                modifiedColormap = ListedColormap(sliceColors)

                pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap=modifiedColormap)

            elif self.segmentationType in self.COLORED_TYPES:
                unique = np.unique(self._Mnp_2Dslice)
                # Para funcionar corretamente, devemos eliminar do colormap as cores que nao serao usadas na matriz atual
                sliceColors = [c for index,c in enumerate(self.mycolors) if index in unique]

                # mapeamento 1 cor : 1 valor, ja eliminados os valores e cores que nao serao usados
                modifiedColormap = ListedColormap(sliceColors)

                pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap = modifiedColormap)
            elif self.segmentationType == self.SEG_PORE:
                # =============== obtendo somente pixels azuis para gerar camada transparente dos poros =============#
                try:
                    ## Primeira parte: salva a imagem de fundo em escala de cinzas
                    # pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap=cm.Greys_r)

                    # Precisa do maximo para que exista uma regra do colormap para todos os numeros de 0 ate o maximo
                    # sliceMaxValue = np.amax(self._Mnp_2Dslice)

                    # Copia o colormap de tons de cinza, exceto para o valor 0, que sera mapeado em transparencia
                    # newcmap = LinearSegmentedColormap.from_list('newcmap',
                    #                                             [(0, 0, 0, 0)] + list(map(cm.Greys_r, range(1,cm.Greys_r.N))),
                    #                                             N=cm.Greys_r.N)
                    newcmap = ModifiedGreys_r

                    # Salva imagem sem poros azuis, soh escala de cinza
                    pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap=newcmap)

                    ## Segunda parte: salva apenas os poros azuis e sobrepoe a imagem
                    # Obtem lista de possiveis valores da matriz/slice atual para eliminar possiveis "pulos" do colormap
                    # unique = np.unique(self._Mnp_2Dslice)
                    # print(">>>>>>>>>>>>>>unique",unique)

                    # Criando regra basica do colormap - transparente para todos os possiveis valores da matriz do slice
                    linearColormap = [(0, 0, 0, 0) for _ in range(self.minAllowedValue + 1,sliceMaxValue )]
                    # linearColormap = [(0, 0, 0, 0) for _ in unique]

                    # Para os valores entre 0 e o limite do poro azul, altera a regra do colormap para usar a cor azul
                    for i in range(self.minAllowedValue + 1,sliceMaxValue ):
                    # for i in unique:
                        if i != 0 and i < self.minAllowedValue + self.blueLimit :
                            linearColormap[i] = (0, 0.972, 0.915, 1) # cor azul claro

                    # Cria colormap de regras 1 cor : 1 valor
                    CustomCmap = ListedColormap(linearColormap)
                    # print(">>>>>>>>>>>>>>CustomCmap(0)",CustomCmap(0))
                    # print(">>>>>>>>>>>>>>CustomCmap(1)",CustomCmap(1))
                    # print(">>>>>>>>>>>>>>CustomCmap(10)",CustomCmap(10))
                    # print(">>>>>>>>>>>>>>CustomCmap(20)",CustomCmap(20))
                    # print(">>>>>>>>>>>>>>CustomCmap(30)",CustomCmap(30))
                    # print(">>>>>>>>>>>>>>CustomCmap(40)",CustomCmap(40))
                    # print(">>>>>>>>>>>>>>CustomCmap(255)",CustomCmap(255))

                    # Salva arquivo temporario que sera a camada superficial com poros azuis e fundo transparente
                    bluePoreTmpImgPath = astr_outputFile.replace('output','blue_pores')
                    pylab.imsave(bluePoreTmpImgPath, self._Mnp_2Dslice, format=fformat, cmap=CustomCmap)

                    # ones = self._Mnp_2Dslice.copy()
                    # ones[:,350] = 24
                    #
                    # pylab.imsave(bluePoreTmpImgPath, ones, format=fformat, cmap=CustomCmap)

                    background = Image.open(astr_outputFile)    # arquivo original em escala de cinza
                    foreground = Image.open(bluePoreTmpImgPath) # arquivo com poros azuis

                    # Sobrepoe os arquivos
                    Image.alpha_composite(background, foreground).save(astr_outputFile)

                    # Apaga arquivo temporario de poros azuis
                    os.remove(bluePoreTmpImgPath)
                except Exception as ex:
                    print("[slice_save @ med2image 527] Ocorreu erro na sobreposicao de poros azuis", ex)
                    print("[slice_save @ med2image] Utilizando imagem em escala de cinzas somente")
                    flagRemoveTransparency = True
                    pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap=cm.Greys_r)
                # =========================== fim do trecho para colorir com pixels azuis  ===========================#

            else:
                flagRemoveTransparency = True
                try:
                    pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap = ModifiedGreys_r) # original
                except:
                    pylab.imsave(astr_outputFile, self._Mnp_2Dslice, format=fformat, cmap=cm.Greys_r)  # original

            #===================trecho para remover transparencia e inverter eixo z ==================#
            try:
                # obtendo todos os rgb dos pixels
                img = Image.open(astr_outputFile)
                img = img.convert("RGBA")

                # Se houve algum erro na geracao dos poros azuis, eh gerada apenas a imagem em escala de cinza com fundo preto
                # O fundo sera removido manualmente
                if flagRemoveTransparency:
                    # obtendo cor de fundo
                    rgb_im = img.convert('RGB')
                    rgbFirstPixel = rgb_im.getpixel((1, 1))

                    datas = img.getdata()
                    newData = []
                    for r,g,b,a in datas:
                        if r == rgbFirstPixel[0] and g == rgbFirstPixel[1] and b == rgbFirstPixel[2]: # deixa o fundo transparente
                            newData.append((255, 255, 255, 0))
                        else: # usa a mesma cor
                                newData.append((r, g, b, a))
                    img.putdata(newData)

                # soh precisa do flip no eixo z
                axis = os.path.basename(os.path.dirname(astr_outputFile))
                if axis == 'z':
                    img = img.transpose(Image.FLIP_TOP_BOTTOM) # flip vertical

                img.save(astr_outputFile, astr_outputFile.rsplit('.',1)[1]) #sobreescreve a imagem
            except Exception as ex:
                print("[med2image] Ocorreu um erro nao esperado na etapa de flip do eixo z/remocao da transparencia", ex)
            # ===========================fim trecho para remover transparencia==========================#


    def invert_slice_intensities(self):
        '''
        Inverts intensities of a single slice.
        '''
        self._Mnp_2Dslice = self._Mnp_2Dslice*(-1) + self._Mnp_2Dslice.max()

    # def generateBluePoreColormap(self,maxTotalValue,maxBlueValue=60):
    #     maxBlueValue += 1
    #     import matplotlib.pyplot as plt
    #     from matplotlib.colors import ListedColormap
    #
    #     # outra abordagem para alterar os poros para azul
    #     my_cmap = plt.cm.Greys_r(np.arange(plt.cm.Greys_r.N))
    #     # ---------- trecho que altera o colormap padrao cinza ---------#
    #     MIN_INDEX = 0
    #     MAX_INDEX = 40
    #     try:
    #         maxIndex = int( (maxBlueValue/maxTotalValue)*len(my_cmap) )
    #         print("[generateBluePoreColormap 564] MaxIndex com limite a partir dos dados ",maxIndex)
    #     except:
    #         maxIndex = MAX_INDEX
    #     for index, ndarray in enumerate(my_cmap):
    #         # altera as primeiras linhas do colormap padrao Greys_r para usar cor azul
    #         if index < maxIndex and index > MIN_INDEX:
    #             my_cmap[index] = np.array((0, 0.972, 0.915, 1))
    #     # ------- fim do trecho que altera o colormap padrao cinza ------#
    #     my_cmap = ListedColormap(my_cmap)
    #     return my_cmap

class med2image_dcm(med2image):
    '''
    Sub class that handles DICOM data.
    '''
    def __init__(self, **kwargs):
        med2image.__init__(self, **kwargs)

        self.l_dcmFileNames = sorted(glob.glob('%s/*.dcm' % self._str_inputDir))
        self.slices         = len(self.l_dcmFileNames)

        if self._b_convertMiddleSlice:
            self._sliceToConvert = int(self.slices/2)
            self._dcm            = dicom.read_file(self.l_dcmFileNames[self._sliceToConvert],force=True)
            self._str_inputFile  = self.l_dcmFileNames[self._sliceToConvert]
            if not self._str_outputFileStem.startswith('%'):
                self._str_outputFileStem, ext = os.path.splitext(self.l_dcmFileNames[self._sliceToConvert])
        if not self._b_convertMiddleSlice and self._sliceToConvert != -1:
            self._dcm = dicom.read_file(self.l_dcmFileNames[self._sliceToConvert],force=True)
            self._str_inputFile = self.l_dcmFileNames[self._sliceToConvert]
        else:
            self._dcm = dicom.read_file(self._str_inputFile,force=True)
        if self._sliceToConvert == -1:
            self._b_3D = True
            self._dcm = dicom.read_file(self._str_inputFile,force=True)
            image = self._dcm.pixel_array
            shape2D = image.shape
            #print(shape2D)
            self._Vnp_3DVol = np.empty( (shape2D[0], shape2D[1], self.slices) )
            i = 0
            for img in self.l_dcmFileNames:
                self._dcm = dicom.read_file(img,force=True)
                image = self._dcm.pixel_array
                self._dcmList.append(self._dcm)
                #print('%s: %s\n' % (img, image.shape))
                try:
                    self._Vnp_3DVol[:,:,i] = image
                except Exception as e:
                    error.fatal(self, 'dcmInsertionFail', '\nFor input DICOM file %s\n%s\n' % (img, str(e)))
                i += 1
        if self._str_outputFileStem.startswith('%'):
            str_spec = self._str_outputFileStem
            self._str_outputFileStem = ''
            for key in str_spec.split('%')[1:]:
                str_fileComponent = ''
                if key == 'inputFile':
                    str_fileName, str_ext = os.path.splitext(self._str_inputFile) 
                    str_fileComponent = str_fileName
                else:
                    str_fileComponent = eval('self._dcm.%s' % key)
                    str_fileComponent = med2image.urlify(str_fileComponent)
                if not len(self._str_outputFileStem):
                    self._str_outputFileStem = str_fileComponent
                else:
                    self._str_outputFileStem = self._str_outputFileStem + '-' + str_fileComponent
        image = self._dcm.pixel_array
        self._Mnp_2Dslice = image

    def sanitize(value):
        # convert to string and remove trailing spaces
        tvalue = str(value).strip()
        # only keep alpha numeric characters and replace the rest by "_"
        svalue = "".join(character if character.isalnum() else '.' for character in tvalue)
        if not svalue:
            svalue = "no value provided"
        return svalue

    def processDicomField(self, dcm, field):
        value = "no value provided"
        if field in dcm:
            value = self.sanitize(dcm.data_element(field).value)
        return value

    def run(self):
        '''
        Runs the DICOM conversion based on internal state.
        '''
        self._log('Converting DICOM image.\n')
        try:
            self._log('PatientName:                                %s\n' % self._dcm.PatientName)
        except AttributeError:
            self._log('PatientName:                                %s\n' % 'PatientName not found in DCM header.')
            error.warn(self, 'PatientNameTag')
        try:
            self._log('PatientAge:                                 %s\n' % self._dcm.PatientAge)
        except AttributeError:
            self._log('PatientAge:                                 %s\n' % 'PatientAge not found in DCM header.')
            error.warn(self, 'PatientAgeTag')
        try:
            self._log('PatientSex:                                 %s\n' % self._dcm.PatientSex)
        except AttributeError:
            self._log('PatientSex:                                 %s\n' % 'PatientSex not found in DCM header.')
            error.warn(self, 'PatientSexTag')
        try:
            self._log('PatientID:                                  %s\n' % self._dcm.PatientID)
        except AttributeError:
            self._log('PatientID:                                  %s\n' % 'PatientID not found in DCM header.')
            error.warn(self, 'PatientIDTag')
        try:
            self._log('SeriesDescription:                          %s\n' % self._dcm.SeriesDescription)
        except AttributeError:
            self._log('SeriesDescription:                          %s\n' % 'SeriesDescription not found in DCM header.')
            error.warn(self, 'SeriesDescriptionTag')
        try:
            self._log('ProtocolName:                               %s\n' % self._dcm.ProtocolName)
        except AttributeError:
            self._log('ProtocolName:                               %s\n' % 'ProtocolName not found in DCM header.')
            error.warn(self, 'ProtocolNameTag')

        if self._b_convertMiddleSlice:
            self._log('Converting middle slice in DICOM series:    %d\n' % self._sliceToConvert)

        l_rot90 = [ True, True, False ]
        misc.mkdir(self._str_outputDir)
        if not self._b_3D:
            str_outputFile = '%s/%s.%s' % (self._str_outputDir,
                                        self._str_outputFileStem,
                                        self._str_outputFileType)
            self.process_slice()
            self.slice_save(str_outputFile)
        if self._b_3D:
            rotCount = 0
            if self._b_reslice:
                for dim in ['x', 'y', 'z']:
                    self.dim_save(dimension = dim, makeSubDir = True, rot90 = l_rot90[rotCount], indexStart = 0, indexStop = -1)
                    rotCount += 1
            else:
                self.dim_save(dimension = 'z', makeSubDir = False, rot90 = False, indexStart = 0, indexStop = -1)

                
class med2image_nii(med2image):
    '''
    Sub class that handles NIfTI data.
    '''

    def __init__(self, **kwargs):
        med2image.__init__(self, **kwargs)
        nimg = nib.load(self._str_inputFile)
        data = nimg.get_data()
        if data.ndim == 4:
            self._Vnp_4DVol     = data
            self._b_4D          = True
        if data.ndim == 3:
            # Entra aqui
            self._Vnp_3DVol     = data
            self._b_3D          = True

    def run(self):
        '''
        Runs the NIfTI conversion based on internal state.
        '''

        self._log('About to perform NifTI to %s conversion...\n' %
                  self._str_outputFileType)

        frames     = 1
        frameStart = 0
        frameEnd   = 0

        sliceStart = 0
        sliceEnd   = 0

        if self._b_4D:
            self._log('4D volume detected.\n')
            frames = self._Vnp_4DVol.shape[3]
        if self._b_3D:
            # entra aqui
            self._log('3D volume detected.\n')

        if self._b_convertMiddleFrame:
            self._frameToConvert = int(frames/2)

        if self._frameToConvert == -1:
            frameEnd    = frames
        else:
            frameStart  = self._frameToConvert
            frameEnd    = self._frameToConvert + 1

        for f in range(frameStart, frameEnd):
            if self._b_4D:
                self._Vnp_3DVol = self._Vnp_4DVol[:,:,:,f]
            slices     = self._Vnp_3DVol.shape[2]
            if self._b_convertMiddleSlice:
                self._sliceToConvert = int(slices/2)

            if self._sliceToConvert == -1:
                sliceEnd    = -1
            else:
                sliceStart  = self._sliceToConvert
                sliceEnd    = self._sliceToConvert + 1

            misc.mkdir(self._str_outputDir)
            if self._b_reslice:
                for dim in ['x', 'y', 'z']:
                    self.dim_save(dimension = dim, makeSubDir = True, indexStart = sliceStart, indexStop = sliceEnd, rot90 = True)
            else:
                self.dim_save(dimension = 'z', makeSubDir = False, indexStart = sliceStart, indexStop = sliceEnd, rot90 = True)



