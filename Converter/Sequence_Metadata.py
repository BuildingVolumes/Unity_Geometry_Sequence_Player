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
    boundsMin = [float('inf'),float('inf'),float('inf')]
    boundsMax = [float('-inf'),float('-inf'),float('-inf')]
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
        boundsCenter, boundsSize = self._get_metadata_bounds()

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
                "x" : boundsCenter[0],
                "y" : boundsCenter[1],
                "z" : boundsCenter[2]
            },
            "boundsSize" : {
                "x" : boundsSize[0],
                "y" : boundsSize[1],
                "z" : boundsSize[2]
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

    def update_metadata_maxbounds(self, newBoundsMin, newBoundsMax):

        self.metaDataLock.acquire()

        self.boundsMin = [
            min(self.boundsMin[0], newBoundsMin[0]),
            min(self.boundsMin[1], newBoundsMin[1]),
            min(self.boundsMin[2], newBoundsMin[2]),
        ]
        self.boundsMax = [
            max(self.boundsMax[0], newBoundsMax[0]),
            max(self.boundsMax[1], newBoundsMax[1]),
            max(self.boundsMax[2], newBoundsMax[2]),
        ]

        self.metaDataLock.release()

    def get_metadata_bounds(self):
        
        self.metaDataLock.acquire()

        boundsCenter, boundsSize = self._get_metadata_bounds()

        self.metaDataLock.release()

        return boundsCenter, boundsSize
    
    def _get_metadata_bounds(self):

        boundsCenter = [
            (self.boundsMax[0] + self.boundsMin[0]) / 2,
            (self.boundsMax[1] + self.boundsMin[1]) / 2,
            (self.boundsMax[2] + self.boundsMin[2]) / 2,
        ]
        # Flip bounds x axis, as we also flip the model's x axis to match Unity's coordinate system
        boundsCenter[0] *= -1

        boundsSize = [
            self.boundsMax[0] - self.boundsMin[0],
            self.boundsMax[1] - self.boundsMin[1],
            self.boundsMax[2] - self.boundsMin[2],
        ]

        return boundsCenter, boundsSize


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
