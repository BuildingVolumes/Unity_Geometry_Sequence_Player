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
    maxVertexCount = 0
    maxIndiceCount = 0
    minMaxBounds = [0,0,0,0,0,0]
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
            "maxVertexCount": self.maxVertexCount,
            "maxIndiceCount" : self.maxIndiceCount,
            "maxBounds" : self.minMaxBounds,
            "textureWidth" : self.textureWidth,
            "textureHeight" : self.textureHeight,
            "textureSizeDDS" : self.textureSizeDDS,
            "textureSizeASTC" : self.textureSizeASTC,
            "headerSizes" : self.headerSizes,
            "verticeCounts" : self.verticeCounts,
            "indiceCounts" : self.indiceCounts,
        }

        return asDict
        
    def set_metadata_Model(self, vertexCount, indiceCount, headerSize, bounds, geometryType, hasUV, hasNormals, listIndex):
        
        self.metaDataLock.acquire()

        self.geometryType = geometryType
        self.hasUVs = hasUV
        self.hasNormals = hasNormals

        if(vertexCount > self.maxVertexCount):
            self.maxVertexCount = vertexCount

        if(indiceCount > self.maxIndiceCount):
            self.maxIndiceCount = indiceCount

        for maxBound in range(3):
            if abs(self.minMaxBounds[maxBound]) < abs(bounds.max()[maxBound]):
                self.minMaxBounds[maxBound] = bounds.max()[maxBound]

        for minBound in range(3):
            if abs(self.minMaxBounds[minBound + 3]) < abs(bounds.min()[minBound]):
                self.minMaxBounds[minBound + 3] = bounds.min()[minBound]

        # Flip bounds x axis, as we also flip the model's x axis to match Unity's coordinate system
        self.minMaxBounds[0] *= -1 # Min X
        self.minMaxBounds[3] *= -1 # Max X

        self.headerSizes[listIndex] = headerSize
        self.verticeCounts[listIndex] = vertexCount
        self.indiceCounts[listIndex] = indiceCount

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

        outputPath = outputDir + "/sequence.json"
        content = self.get_as_dict()
        with open(outputPath, 'w') as f:
            json.dump(content, f)    

        self.metaDataLock.release()
