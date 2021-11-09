# This algorithm splits lines by points

# calling libraires
# doesn't mind about this piece of code below ;)

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingOutputMultipleLayers,
                       QgsProcessingParameterString,
                       QgsVectorLayer,
                       QgsProject,
                       QgsProcessingUtils,
                       QgsVectorDataProvider,
                       )
from qgis import processing
from qgis.processing import alg
from processing.tools.system import mkdir
import os

class SplitLinesByPoints(QgsProcessingAlgorithm):
    INPUT_NETWORK = 'INPUT_NETWORK'
    INPUT_POINTS = 'INPUT_POINTS'
    FIELD = 'FIELD'
    OUTPUT = 'OUTPUT'
    OUTPUT_MERGED = 'OUTPUT_MERGED'
    VALUE = 'VALUE'

    def __init__(self):
        super().__init__()
    
    # giving this script a cozy place in processing toolbox
    
    def name(self):
        return 'SplitLineByPoints'

    def displayName(self):
        return 'SplitLineByPoints'

    def group(self):
        return 'EGOR'

    def groupId(self):
        return 'egorbogautdinov'

    def createInstance(self):
        return type(self)()
    
    def shortHelpString(self, config=None):
        return "This algorithm splits line into several parts dividing it by points from point layer. \n It is rather rough, so there are several limitations. \n 0. if you want to split line, add points in the beginning and end of it \n 1. Your input point layer should have a field representing an order by which points should be connected with lines \n 2. Yet to work properly algorithm requires saving all the lines to a folder (I strongly recommend to create a 'trash' folder beforehead) \n 3. Moreover, you have to save a merged splitted line layer into a file \n 4. Finally, for some reason it will not add a merged output file automatically. So do it manually please \n UI currently unavailable;) \n Once I will fix all the problems..."

    def initAlgorithm(self, config=None):
        
        # configuring input, output and parameters
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_NETWORK, 'Input layer (network)',
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_POINTS, 'Input layer (points)',
                [QgsProcessing.TypeVectorPoint]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.FIELD,
                'Field (order)',
                'A field from point_layer representing an order of points along line',
                parentLayerParameterName=self.INPUT_POINTS
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.VALUE,
                'Value',
                'A field from point_layer representing value',
                parentLayerParameterName=self.INPUT_POINTS,
                optional = True
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT, 'Output layer (lines)'
            )
        )
        '''
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_MERGED, 'Output layer (merged lines)'
            )
        )
        '''
        
    def processAlgorithm(self, parameters, context, feedback):
        '''
        algorithm itself
        '''
        
        # getting name of a field representing an order
        
        fName = self.parameterAsString(
            parameters,
            self.FIELD,
            context
        )
        
        # gettin name of a field with values
        
        fValue = self.parameterAsString(
            parameters,
            self.VALUE,
            context
        )
        
        values = []
        
        # getting info from point layer
        
        source = self.parameterAsSource(
            parameters,
            self.INPUT_POINTS,
            context
        )
        fields = source.fields()
        crs = source.sourceCrs()
        geomType = source.wkbType()

        # directory

        directory = self.parameterAsString(parameters, self.OUTPUT, context)
        mkdir(directory)
        
        # getting the lowest number from order field
        
        counter = 0
        flag = True
        for f in source.getFeatures():
            counter += 1
            if flag:
                min_id = f.attribute(fName)
                flag = False
            if f.attribute(fName) < min_id:
                min_id = f.attribute(fName)
        
        # loooooooooop
        # creating lines from one point to another by graph
        
        for i in range(min_id, counter + min_id - 1):
            
            # getting coordinates of start and end points
            
            for f in source.getFeatures():
                if f.attribute(fName) == i:
                    start = str(f.geometry().asPoint().x()) + ',' + str(f.geometry().asPoint().y())
                    values.append(f.attribute(fValue))
                else:
                    continue
            for f in source.getFeatures():
                if f.attribute(fName) == i + 1:
                    end = str(f.geometry().asPoint().x()) + ',' + str(f.geometry().asPoint().y())
                    values.append(f.attribute(fValue))
                else:
                    continue
                    
            # making lines (routes) and saving them to a folder
            
            splitted_lines = processing.run("qgis:shortestpathpointtopoint", {
                'INPUT': parameters[self.INPUT_NETWORK],
                'START_POINT': start,
                'END_POINT': end,
                'OUTPUT': '{0}\{1}_{2}.{3}'.format(directory, 'splitted_lines', str(i).strip(), 'gpkg')
            }, context=context, feedback=feedback, is_child_algorithm=True)
            i += 1

        # putting together directories of single line layers in one list
        
        source_files = []
        for i in range(counter - 2):
            source_files.append('{0}/{1}_{2}.{3}'.format(directory, 'splitted_lines', str(i).strip(), 'gpkg'))
            
        #merging layers    
            
        params = {
            'LAYERS': source_files,
            'CRS': 'ProjectCrs',
            'OUTPUT': '{0}\{1}.{2}'.format(directory, '1_merged', 'shp')
        }
        merged_layers = processing.run("native:mergevectorlayers", params, context = context)
        
        merged_with = processing.run("qgis:addfieldtoattributestable", {
            'INPUT': '{0}\{1}.{2}'.format(directory, '1_merged', 'shp'),
            'FIELD_NAME': 'StartValue',
            'FIELD_TYPE': 1,
            'FIELD_PRECISION': 2,
            'OUTPUT': '{0}\{1}.{2}'.format(directory, '2_merged', 'shp')
            }
        )
        
        merged_with = processing.run("qgis:addfieldtoattributestable", {
            'INPUT': '{0}\{1}.{2}'.format(directory, '2_merged', 'shp'),
            'FIELD_NAME': 'EndValue',
            'FIELD_TYPE': 1,
            'FIELD_PRECISION': 2,
            'OUTPUT': '{0}\{1}.{2}'.format(directory, '3_merged', 'shp')
            }
        )
        
        
        layer = QgsVectorLayer('{0}\{1}.{2}'.format(directory, '3_merged', 'shp'), 'merged', 'ogr')
        caps = layer.dataProvider().capabilities()
        for i in range(counter - 1):
            if caps & QgsVectorDataProvider.ChangeAttributeValues:
                attrs = {6: values[2 * i], 7: values[2 * i + 1]}
                layer.dataProvider().changeAttributeValues({ i : attrs })
            print('hello')
        print(*values)
        
        # Trying to load merged layer... but it doesn't so I just comment it and you do it manually
        
        # merged = QgsVectorLayer('{0}\{1}.{2}'.format(directory, '3_merged', 'shp'), "wtf_merged", "ogr")
        # QgsProject.instance().addMapLayer(merged)
        
        return {self.OUTPUT: directory}
