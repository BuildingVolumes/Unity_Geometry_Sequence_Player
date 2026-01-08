from enum import IntEnum
import json
from threading import Lock

class GeometryType(IntEnum):
    point = 0
    mesh = 1
    texturedMesh = 2

class TextureMode(IntEnum):
    none = 0
    single = 1
    perFrame = 2

class MetaData():
    geometryType = GeometryType.point
    textureMode = TextureMode.none
    DDS = False
    ASTC = False
    hasUVs = False
    hasNormals = False
    useCompression = False
    maxVertexCount = 0
    maxIndiceCount = 0
    boundsCenter = [0,0,0]
    boundsSize = [1,1,1]
    textureWidth = 0
    textureHeight = 0
    textureSizeDDS = 0
    textureSizeASTC = 0
    headerSizes = []
    verticeCounts = []
    indiceCounts = []

    #Ensure that this class can be called from multiple threads
    metaDataLock = Lock() 

    def get_as_dict(self):

        asDict = {
            "geometryType" : int(self.geometryType),
            "textureMode" : int(self.textureMode),
            "DDS" : self.DDS,
            "ASTC" : self.ASTC,
            "hasUVs" : self.hasUVs,
            "hasNormals" : self.hasNormals,
            "useCompression" : self.useCompression,
            "maxVertexCount": self.maxVertexCount,
            "maxIndiceCount" : self.maxIndiceCount,
            "boundsCenter" : { # Export bounds as dicts for easier JSON parsing to Vector3 in Unity
                "x" : self.boundsCenter[0],
                "y" : self.boundsCenter[1],
                "z" : self.boundsCenter[2]
            },
            "boundsSize" : {
                "x" : self.boundsSize[0],
                "y" : self.boundsSize[1],
                "z" : self.boundsSize[2]
            },
            "textureWidth" : self.textureWidth,
            "textureHeight" : self.textureHeight,
            "textureSizeDDS" : self.textureSizeDDS,
            "textureSizeASTC" : self.textureSizeASTC,
            "headerSizes" : self.headerSizes,
            "verticeCounts" : self.verticeCounts,
            "indiceCounts" : self.indiceCounts,
        }

        return asDict

    def set_metadata_Model(self, vertexCount, indiceCount, headerSize, geometryType, hasUV, hasNormals, useCompressions, listIndex):

        self.metaDataLock.acquire()

        self.geometryType = geometryType
        self.hasUVs = hasUV
        self.hasNormals = hasNormals
        self.useCompression = useCompressions

        if(vertexCount > self.maxVertexCount):
            self.maxVertexCount = vertexCount

        if(indiceCount > self.maxIndiceCount):
            self.maxIndiceCount = indiceCount

        self.headerSizes[listIndex] = headerSize
        self.verticeCounts[listIndex] = vertexCount
        self.indiceCounts[listIndex] = indiceCount

        self.metaDataLock.release()

    def set_metadata_maxbounds(self, newBoundsSize, newBoundsCenter):

        self.metaDataLock.acquire()

        self.boundsSize = [
            max(newBoundsSize[0], self.boundsSize[0]),
            max(newBoundsSize[1], self.boundsSize[1]),
            max(newBoundsSize[2], self.boundsSize[2])
        ]
        self.boundsCenter += newBoundsCenter

        self.metaDataLock.release()

    def set_metadata_texture(self, DDS, ASTC, width, height, sizeDDS, sizeASTC, textureMode):

        self.metaDataLock.acquire()

        if(height > self.textureHeight):
            self.textureHeight = height 

        if(width > self.textureWidth):
            self.textureWidth = width

        if(sizeDDS > self.textureSizeDDS):
            self.textureSizeDDS = sizeDDS

        if(sizeASTC > self.textureSizeASTC):
            self.textureSizeASTC = sizeASTC

        self.textureMode = textureMode
        self.DDS = DDS
        self.ASTC = ASTC

        self.metaDataLock.release()

    def write_metaData(self, outputDir):

        self.metaDataLock.acquire()
        if (not self.useCompression): # we already did that during the prepass
            # Flip bounds x axis, as we also flip the model's x axis to match Unity's coordinate system
            self.boundsCenter[0] *= -1 # Min X
            self.boundsCenter = [x / len(self.headerSizes) for x in self.boundsCenter] # Average the center over the number of frames/models

        outputPath = outputDir + "/sequence.json"
        content = self.get_as_dict()
        with open(outputPath, 'w') as f:
            json.dump(content, f)    

        self.metaDataLock.release()
