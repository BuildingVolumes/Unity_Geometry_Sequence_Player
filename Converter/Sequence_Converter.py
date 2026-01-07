import os
import sys
import subprocess
import pymeshlab as ml
import numpy as np
from threading import Lock
from multiprocessing.pool import ThreadPool
import Sequence_Metadata
from PIL import Image

class SequenceConverterSettings:
    modelPaths = []
    imagePaths = []
    metaData = Sequence_Metadata.MetaData()
    inputPath = ""
    outputPath = ""
    resourcePath = ""

    isPointcloud = False
    hasUVs = False
    hasNormals = False
    saveNormals = False
    textureDimensions = []
    convertToDDS = False
    convertToASTC = False
    convertToSRGB = False

    decimatePointcloud = False
    decimatePercentage = 0
    saveNormals = False
    generateNormals = False
    mergePoints = False
    mergeDistance = 0

    maxThreads = 8

class SequenceConverter:

    convertSettings = SequenceConverterSettings()
    terminateProcessing = False
    debugMode = False
    
    modelPool = None
    texturePool = None

    processFinishedCB = None
    
    loadMeshLock = Lock()
    activeThreads = 0

    #Only used for pointcloud normal estimation
    lastAverageNormal = [0, 0, 0] 
    firstEstimation = True

    def start_conversion(self, convertSettings, processFinishedCB):       
        
        self.convertSettings = convertSettings
        self.terminateProcessing = False
        self.processFinishedCB = processFinishedCB
        self.debugMode = hasattr(sys, 'gettrace') and sys.gettrace() is not None

        modelCount = len(self.convertSettings.modelPaths)
        self.convertSettings.metaData.headerSizes = [None] * modelCount
        self.convertSettings.metaData.verticeCounts = [None] * modelCount
        self.convertSettings.metaData.indiceCounts = [None] * modelCount
    
        if(len(self.convertSettings.modelPaths) > 0):
            self.process_models()
        if(len(self.convertSettings.imagePaths) > 0):
            self.process_images()

    def terminate_conversion(self):
        self.terminateProcessing = True

    def finish_conversion(self, writeMetaData):
        if(self.modelPool is not None):
            waitOnClose = True
            while(waitOnClose):
                try:
                    waitOnClose = False
                    self.modelPool.close()
                except:
                    waitOnClose = True
            self.modelPool.join()

        if(self.texturePool is not None):
            waitOnClose = True
            while(waitOnClose):
                try:
                    waitOnClose = False
                    self.texturePool.close()
                except:
                    waitOnClose = True
            self.texturePool.close()

        if(writeMetaData):
            self.write_metadata()

    def write_metadata(self):
        self.convertSettings.metaData.write_metaData(self.convertSettings.outputPath)

    def process_models(self):

        if(len(self.convertSettings.modelPaths) < self.convertSettings.maxThreads):
            threads = len(self.convertSettings.modelPaths)
        elif self.convertSettings.generateNormals:
            threads = 1
        else:
            threads = self.convertSettings.maxThreads

        if self.debugMode:
            self.firstEstimation = True
            for model in self.convertSettings.modelPaths:
                self.convert_model(model)            
        else:
            # Process the first model to establish sequence attributes (Pointcloud or Mesh, has UVs? Normals?)
            self.convert_model(self.convertSettings.modelPaths[0]) 
            self.modelPool = ThreadPool(processes = threads)
            self.modelPool.map_async(self.convert_model, self.convertSettings.modelPaths)

    def convert_model(self, file):

        listIndex = self.convertSettings.modelPaths.index(file)

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            return

        splitted_file = file.split(".")
        splitted_file.pop() # We remove the last element, which is the file ending
        file_name = ''.join(splitted_file)

        inputfile = os.path.join(self.convertSettings.inputPath, file)
        outputfile = os.path.join(self.convertSettings.outputPath, file_name + ".ply")

        ms = ml.MeshSet()

        if not self.debugMode:
            self.loadMeshLock.acquire() # If we don't lock the mesh loading process, crashes might occur

        try:
            ms.load_new_mesh(inputfile)
        except:
            self.loadMeshLock.release()
            self.processFinishedCB(True, "Error opening file: " + inputfile)
            return    

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            self.loadMeshLock.release()
            return

        faceCount = len(ms.current_mesh().face_matrix())

        #Is the file a mesh or pointcloud?        
        if(faceCount > 0):
            pointcloud = False
        else:
            pointcloud = True

        if(ms.current_mesh().has_wedge_tex_coord() == True or ms.current_mesh().has_vertex_tex_coord() == True):
            uvs = True
        else:
            uvs = False

        if(listIndex == 0):
            self.convertSettings.isPointcloud = pointcloud
            self.convertSettings.hasUVs = uvs
        else:
            if(self.convertSettings.hasUVs != uvs):
                # The sequence has different attributes, which is not allowed
                self.processFinishedCB(True, "Error: Some frames with UVs, some without. All frames need to be consistent with this attribute!")
                self.loadMeshLock.release()
                return
            if(self.convertSettings.isPointcloud != pointcloud):
                self.processFinishedCB(True, "Error: Some frames are Pointclouds, some are meshes. Mixed sequences are not allowed!")
                self.loadMeshLock.release()
                return

        if(self.convertSettings.mergePoints):
            ms.apply_filter('meshing_merge_close_vertices', threshold= ml.PercentageValue (self.convertSettings.mergeDistance))


        normals = None
        normals = ms.current_mesh().vertex_normal_matrix().astype(np.float32)
        if(len(normals) > 0 and self.convertSettings.saveNormals):
            self.convertSettings.hasNormals = True
        else:
            self.convertSettings.hasNormals = False

        #There is a chance that the file might have wedge tex
        #coordinates which are unsupported in Unity, so we convert them
        #Also we need to ensure that our mesh contains only triangles!
        if(self.convertSettings.isPointcloud == False and ms.current_mesh().has_wedge_tex_coord() == True):
            ms.compute_texcoord_transfer_wedge_to_vertex()     


        # We'll later flip the x-Axis. For meshes, this also requires us to flip the face orientation 
        if(self.convertSettings.isPointcloud == False):
            ms.meshing_invert_face_orientation(forceflip = True)


        # For pointclouds, normals can be estimated
        if(self.convertSettings.generateNormals and self.convertSettings.isPointcloud):
            ms.compute_normal_for_point_clouds(k = 10, flipflag = False, smoothiter = 3)
            normals = ms.current_mesh().vertex_normal_matrix().astype(np.float32)

            #Pointcloud normal estimation leads to randomly flipped normals between frames

            #To counteract this, we calculate the average normal direction of the pointcloud, and then compare it to the
            #last frame's average normal
            averageNormal = [np.average(normals[:,0]), np.average(normals[:,1]), np.average(normals[:,2])]

            if not self.firstEstimation:

                # Normalize the vectors
                v1_norm = averageNormal / np.linalg.norm(averageNormal)
                v2_norm = self.lastAverageNormal / np.linalg.norm(self.lastAverageNormal)

                # The dot product let's us know how if the average normals point in the same direction
                # (-1 for opposite, 1 for same direction)
                dot_product = np.dot(v1_norm, v2_norm)
                
                #Flip normals if the average normal differs too much from the last frame
                if(dot_product < 0.5):
                    normals = normals * -1 
                    averageNormal = np.multiply(averageNormal, -1)

            self.lastAverageNormal = averageNormal
            self.firstEstimation = False

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            self.loadMeshLock.release()
            return

        vertices = None
        vertice_colors = None
        faces = None
        uvs = None

        #Load type specific attributes
        if(self.convertSettings.isPointcloud == True):
            vertices = ms.current_mesh().vertex_matrix().astype(np.float32)
            vertice_colors = ms.current_mesh().vertex_color_array()
        
        else:
            vertices = ms.current_mesh().vertex_matrix().astype(np.float32)
            faces = ms.current_mesh().face_matrix()

            if(self.convertSettings.hasUVs == True):     
                uvs = ms.current_mesh().vertex_tex_coord_matrix().astype(np.float32)

        #Check if the mesh has pre-existing normals
        
        vertexCount = len(vertices)

        if(faces is not None):
            indiceCount = len(faces) * 3
        else:
            indiceCount = 0

        bounds = ms.current_mesh().bounding_box()

        if(self.convertSettings.isPointcloud == True):
            geoType = Sequence_Metadata.GeometryType.point
        else:
            if(self.convertSettings.hasUVs == False):
                geoType = Sequence_Metadata.GeometryType.mesh
            else:
                geoType = Sequence_Metadata.GeometryType.texturedMesh

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            self.loadMeshLock.release()
            return

        if not self.debugMode:
            self.loadMeshLock.release()
        
        #The meshlab exporter doesn't support all the features we need, so we export the files manually
        #to PLY with our very stringent structure. This is needed because we want to keep the
        #work on the Unity side as low as possible, so we basically want to load the data from disk into the memory
        #without needing to change anything
        with open(outputfile, 'wb') as f:

            #If pointcloud decimation is enabled, calculate how many points were going to write
            if(self.convertSettings.decimatePointcloud):
                vertexCount = int(len(vertices) * (self.convertSettings.decimatePercentage / 100))

            #constructing the ascii header
            header = "ply" + "\n"
            header += "format binary_little_endian 1.0" + "\n"
            header += "comment Exported for use in Unity Geometry Streaming Plugin" + "\n"

            header += "element vertex " + str(vertexCount) + "\n"
            header += "property float x" + "\n" 
            header += "property float y" + "\n"
            header += "property float z" + "\n"

            if(self.convertSettings.hasNormals):
                header += "property float nx" + "\n"
                header += "property float ny" + "\n"
                header += "property float nz" + "\n"

            if(self.convertSettings.isPointcloud == True):
                header += "property uchar red" + "\n"
                header += "property uchar green" + "\n"
                header += "property uchar blue" + "\n"
                header += "property uchar alpha" + "\n"
            
            else:
                if(self.convertSettings.hasUVs == True):
                    header += "property float s" + "\n" 
                    header += "property float t" + "\n"
                header += "element face " + str(len(faces)) + "\n"
                header += "property list uchar uint vertex_indices" + "\n"

            header += "end_header\n"

            headerASCII = header.encode('ascii')
            headerSize = len(headerASCII)

            f.write(headerASCII)

            byteCombination = []

            #Flip vertice positions and normals to match Unity's coordinate system
            vertices[:,0] *= -1
            normals[:,0] *= -1

            verticePositionsBytes = np.frombuffer(vertices.tobytes(), dtype=np.uint8)
            verticePositionsBytes = np.reshape(verticePositionsBytes, (-1, 12))
            byteCombination.append(verticePositionsBytes)

            if(self.convertSettings.hasNormals):
                verticeNormalsBytes = np.frombuffer(normals.tobytes(), dtype=np.uint8)
                verticeNormalsBytes = np.reshape(verticeNormalsBytes, (-1, 12))
                byteCombination.append(verticeNormalsBytes)


            #Constructing the mesh data, as binary array
            if(self.convertSettings.isPointcloud == True):
                
                verticeColorsBytes = np.frombuffer(vertice_colors.tobytes(), dtype=np.uint8)

                #Reshape arrays into 2D array, so that the elements of one vertex each occupy one row
                verticeColorsBytes = np.reshape(verticeColorsBytes, (-1, 4))

                #Convert colors from BGRA to RGBA
                verticeColorsBytes = verticeColorsBytes[..., [2,1,0,3]]

                byteCombination.append(verticeColorsBytes)

                body = np.concatenate(byteCombination, axis = 1)

                #Decimate n random elements to reduce points (if enabled)
                if(self.convertSettings.decimatePointcloud):
                    np.random.shuffle(body)
                    body = body[0:vertexCount]

                #Flatten the array into a 1D array
                body = body.ravel()

            else:
                
                if(self.convertSettings.hasUVs == True):
                    uvsBytes = np.frombuffer(uvs.tobytes(), dtype=np.uint8)
                    uvsBytes = np.reshape(uvsBytes, (-1, 8))
                    byteCombination.append(uvsBytes)

                #Indices
                IndiceBytes = np.frombuffer(faces.tobytes(), dtype=np.uint8)
                IndiceBytes = np.reshape(IndiceBytes, (-1, 12)) # Convert to 2D array with 3 indices per line

                #For the vertices, we need to add one byte per line which indicates how much indices per face exist
                #We always have 3 indices, so we add a byte with value 3 to each indice row
                threes = np.full((len(faces), 1), 3, dtype= np.uint8)
                IndiceBytes = np.concatenate((threes, IndiceBytes), axis = 1)
                IndiceBytes = IndiceBytes.ravel()

                body = np.concatenate((byteCombination), axis = 1)
                body = body.ravel()

                body = np.concatenate((body, IndiceBytes), axis = 0)

            f.write(bytes(body))

        self.convertSettings.metaData.set_metadata_Model(vertexCount, indiceCount, headerSize, bounds, geoType, self.convertSettings.hasUVs, self.convertSettings.hasNormals, listIndex)

        self.processFinishedCB(False, "") 

        if self.debugMode:
            print("Processed file: " + str(listIndex))

    def process_images(self):

        if(len(self.convertSettings.imagePaths) < self.convertSettings.maxThreads):
            threads = len(self.convertSettings.imagePaths)
        else:
            threads = self.convertSettings.maxThreads

        self.convertSettings.texturePool = ThreadPool(processes= threads)

        #Read the first image to get the dimensions
        self.convert_image(self.convertSettings.imagePaths[0])
        self.convertSettings.imagePaths.pop(0)

        self.convertSettings.texturePool.map_async(self.convert_image, self.convertSettings.imagePaths)

    def convert_image(self, file):

        if(self.terminateProcessing):
            self.processFinishedCB(False, "")
            return

        listIndex = self.convertSettings.imagePaths.index(file)

        splitted_file = file.split(".")
        file_name = splitted_file[0]
        for x in range(1, len(splitted_file) - 1):
            file_name += "." + splitted_file[x]
        inputfile = os.path.join(self.convertSettings.inputPath, file)

        sizeDDS = 0
        sizeASTC = 0

        if(self.convertSettings.convertToDDS):
            outputfileDDS = os.path.join(self.convertSettings.outputPath, file_name + ".dds")
            cmd = self.convertSettings.resourcePath + "texconv " + "\"" + inputfile + "\"" + " -o " + "\"" + self.convertSettings.outputPath + "\"" +" -m 1 -f DXT1 -y -nologo"
            if(self.convertSettings.convertToSRGB):
                cmd += " -srgbo" 
            if(subprocess.run(cmd, stdout=open(os.devnull, 'wb')).returncode != 0):
                self.processFinishedCB(True, "Error converting DDS texture: " + inputfile)
                return
        
        if(self.convertSettings.convertToASTC):
            outputfileASCT = os.path.join(self.convertSettings.outputPath, file_name + ".astc")
            cmd = self.convertSettings.resourcePath + "astcenc -cl " + "\"" + inputfile + "\"" + " " + "\"" + outputfileASCT + "\"" + " 6x6 -medium -silent"
            if(subprocess.run(cmd, stdout=open(os.devnull, 'wb')).returncode != 0):
                self.processFinishedCB(True, "Error converting ASTC texture: " + inputfile)
                return

        # Write the metadata once per sequence
        if(listIndex == 0):
            if(self.convertSettings.convertToDDS):
                sizeDDS = os.path.getsize(outputfileDDS) - 128 #128 = DDS header size
            if(self.convertSettings.convertToASTC):
                sizeASTC = os.path.getsize(outputfileASCT) - 16 #20 = ASTC header size

            if(len(self.convertSettings.imagePaths) == 1):
                textureMode = Sequence_Metadata.TextureMode.single
            if(len(self.convertSettings.imagePaths) > 1):
                textureMode = Sequence_Metadata.TextureMode.perFrame

            self.convertSettings.textureDimensions = self.get_image_dimensions(inputfile)
            self.convertSettings.metaData.set_metadata_texture(self.convertSettings.convertToDDS, self.convertSettings.convertToASTC, self.convertSettings.textureDimensions[0], self.convertSettings.textureDimensions[1], sizeDDS, sizeASTC, textureMode)
        else:
            dimensions = self.get_image_dimensions(inputfile)
            if len(dimensions) < 2:
                self.processFinishedCB(True, "Could not get image dimensions!")
                return
            if(dimensions[0] != self.convertSettings.textureDimensions[0] or dimensions[1] != self.convertSettings.textureDimensions[1]):
                self.processFinishedCB(True, "All textures need to have the same resolution! Frame " + str(listIndex))
                return
        
        #print("Converted image file: " + file_name)
        #print()
        self.processFinishedCB(False, "")

    def get_image_dimensions(self, filePath):

            pilimg = Image.open(filePath) 
            pilimg.load()
            dimensions = [pilimg.width, pilimg.height]
            pilimg.close()
            return dimensions

    def get_image_gamme_encoded(self, filePath):

        gammaencoded = False

        pilimg = Image.open(filePath)
        pilimg.load()
        
        if("gamma" in pilimg.info):
            gamma = pilimg.info["gamma"]
            if(gamma >= 0.45 and gamma <= 0.46):
                gammaencoded = True

        pilimg.close()
        return gammaencoded

