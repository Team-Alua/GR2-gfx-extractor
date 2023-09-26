# Noesis Gravity Rush 2 GFX Extractor V2
# Written by 203Null
# Reverse Engineered by 203Null and FreezeCook
# Strcture Note: https://docs.google.com/document/d/1eW8BNMuE6chZebgClRnRoxRCEMDCAKPadYEhpK4AIV0/edit?usp=sharing

from inc_noesis import *
import noesis
import rapi
import os
import copy
import json
import math
from GravityRush_common import *

debug = False  # please change to False out when done.
print_CSV = False
seperate_sub_mesh = True
global_scale = 100
remove_loose_vertice = True
LOD_suffix = True
reverse_binding = True
export_normal_and_tangent = True #Experimental
print_material = False
print_vertice_csv = False
material_param_as_name = False
optimize_bone_name = False
export_material_json = False #Set it to False to disable, or as export location string (<export_material_json>/<modelName>.json)

def registerNoesisTypes():
    handle = noesis.register('Gravity Rush 2 GFX', '.gfx')
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadModel(handle, noepyLoadModel)
    if debug:
        noesis.logPopup()
    return 1


def noepyCheckType(data):
    file = NoeBitStream(data)
    if len(data) < 4:
        return 0
    header = file.readBytes(4).decode('ASCII').rstrip("\0")
    if header == 'GFX2':
        return 1
    return 0

def debugprint(message, end="\n"):
    if(debug):
        print(message, end=end)


class IndexChunk:
    def __init__(self, name, typeID, offset, length):
        self.name = name
        self.typeID = typeID
        self.offsetFromDataChunk = offset
        self.length = length

    def setCustomName(self, customName):
        self.customName = customName

class BoneInfo:
    def __init__(self, index, boneName, boneMatrix, scale, parentID, isBone, childList):
        self.index = index
        self.boneName = boneName
        self.boneMatrix = boneMatrix
        self.scale = scale
        self.globalMatrix = boneMatrix
        self.parentID = parentID
        self.isBone = isBone
        self.childList = childList
        self.reverseBindingMatrix = None
        self.hasRPB = False
    
    def setReverseBindingMatrix(self, reverseBindingMatrix):
        self.hasRPB = True
        self.reverseBindingMatrix = reverseBindingMatrix
        self.globalMatrix = reverseBindingMatrix

    def setGlobalMatrix(self, globalMatrix):
        self.globalMatrix = globalMatrix
    
    def setName(self, name):
        self.boneName = name

class MeshInfo:
    # Infomations from 0x0400 Chunk
    def __init__(self, index, name, numOfFaceChunk, parentID, indexOf0x0500Chunk, indexOf0x0600Chunk):
        self.index = index  # Global Index
        self.name = name
        self.numOfFaceChunk = numOfFaceChunk
        self.parentID = parentID
        self.indexOf0x0500Chunk = indexOf0x0500Chunk
        self.indexOf0x0600Chunk = indexOf0x0600Chunk
        self.initialize0x0600ChunkInfo()
        self.boneMap = None

    def initialize0x0600ChunkInfo(self):
        self.indexOf0x0800Chunk = []
        self.indexOf0x03000201Chunk = []
        self.faceCount = []
        self.faceIndex = []
        self.texture = []

    # Infomations from 0x0500 Chunk
    def loadVertexInfo(self, vertexCount, indexOf0x03000101Chunk, vertexStruct):
        self.vertexCount = vertexCount
        self.indexOf0x03000101Chunk = indexOf0x03000101Chunk
        self.vertexStruct = vertexStruct

    # Infomations from 0x0600 Chunk
    def loadFaceInfo(self, indexOf0x0800Chunk, indexOf0x03000201Chunk, faceCount, faceIndex):
        self.indexOf0x0800Chunk.append(indexOf0x0800Chunk)
        self.indexOf0x03000201Chunk.append(indexOf0x03000201Chunk)
        self.faceCount.append(faceCount)
        self.faceIndex.append(faceIndex)

    # Infomations from 0x1000 Chunk
    def loadBoneInfo(self, numOfBone, indexOf0x03001401Chunk, indexOf0x03000A01Chunk, boneMap):
        self.numOfBone = numOfBone
        self.indexOf0x03001401Chunk = indexOf0x03001401Chunk
        self.indexOf0x03000A01Chunk = indexOf0x03000A01Chunk
        self.boneMap = boneMap

    def load2BInfo(self, numOfDataInMeshChunk0x1500, numOfDataInMeshChunk0x1600, numOfDataInMeshChunk0x1700, indexOfMeshChunk0x1500, indexOfMeshChunk0x1600, indexOfMeshChunk0x1700):
        self.numOfDataInMeshChunk0x1500 = numOfDataInMeshChunk0x1500
        self.numOfDataInMeshChunk0x1600 = numOfDataInMeshChunk0x1600 
        self.numOfDataInMeshChunk0x1700 = numOfDataInMeshChunk0x1700 
        self.indexOfMeshChunk0x1500 = indexOfMeshChunk0x1500
        self.indexOfMeshChunk0x1600 = indexOfMeshChunk0x1600
        self.indexOfMeshChunk0x1700 = indexOfMeshChunk0x1700

    def loadTexture(self, texture):  # Infomations from list of child 0x1100 Chunk
        self.texture.append(texture)

    def setName(self, name):
        self.name = name

    def setIndexOf0x0600Chunk(self, indexOf0x0600Chunk):
        self.indexOf0x0600Chunk = indexOf0x0600Chunk

    def setVertexCount(self, vertexCount):
        self.vertexCount = vertexCount

class MaterialInfo:
    def __init__(self, index, chunkType, name, data = []):
        self.index = index
        self.chunkType = chunkType
        self.name = name.split("/")[-1]
        self.addMaterialData(data)
        self.textureList = []
    
    def addMaterialData(self, data):
        for i in range(len(data)):
            if type(data[i]) == float:
                data[i] = round(data[i], 3)
        self.data = data

    def addTextureData(self, index, data):
        for value in data:
            if type(value) == float:
                value = round(value, 3)
        self.textureList.append([index, data, "No Texture", None])

    def addTexture(self, filename):
        self.textureList[-1][2] = filename

    def addTextureAtlas(self, data):
        for i in range(len(data)):
            if type(data[i]) == float:
                data[i] = round(data[i], 3)
        self.textureList[-1][3] = data

def noepyLoadModel(data, mdlList):
    noeData = loadModel(data)

    model = NoeModel(noeData[0])
    model.setModelMaterials(NoeModelMaterials([], noeData[1]))
    model.setBones(noeData[2])
    mdlList.append(model)

    if print_CSV:
        printMeshCSV()

    if print_material:
        printMaterial()

    if export_material_json != False:
        exportMaterialJson()

    return 1

def loadModel(data):
    # Initialization
    global bs
    bs = NoeBitStream(data)

    # Read header
    bs.seek(0x08, NOESEEK_ABS)
    global modelName
    modelName = getNameFromHash(bs.readUInt())
    bs.seek(0x0C, NOESEEK_ABS)
    global fileSize
    fileSize = bs.readUInt()
    bs.seek(0x10, NOESEEK_ABS)
    global numDataInIndexChunk
    numDataInIndexChunk = bs.readUInt() - 1
    bs.seek(0x14, NOESEEK_ABS)
    global pointerOfDataChunk
    pointerOfDataChunk = bs.readUInt()
    bs.seek(0x18, NOESEEK_ABS)
    global pointerOfMeshChunk
    pointerOfMeshChunk = bs.readUInt()
    bs.seek(0x1C, NOESEEK_ABS)
    global numMeshChunk
    numMeshChunk = bs.readUInt()

    # Scan Index Chunk
    bs.seek(0x30, NOESEEK_ABS)

    global indexList
    indexList = []
    global meshInfos
    meshInfos = []
    global meshs
    meshs = []
    global indexBoneIDLookUpTable
    indexBoneIDLookUpTable = [-1]*numDataInIndexChunk

    global child0x0f00ChunkList
    child0x0f00ChunkList = []

    global indexOf0x2b00Chunk
    indexOf0x2b00Chunk = []

    global numOfBone
    numOfBone = 0
    global numOfMesh
    numOfMesh = 0
    global currentMesh
    currentMesh = 0

    global materialList
    materialList = []
    global materialInfoList
    materialInfoList = []

    global textureList
    textureList = []

    materialIndexs = []

    global LOD
    LOD = ""

    if "lod2" in modelName:
        LOD = "_LOD3"

    rootBones = []

    for i in range(numDataInIndexChunk):
        indexList.append(IndexChunk(getNameFromHash(bs.readUInt()), bs.readUInt(), bs.readUInt(), bs.readUInt()))
        if indexList[i].typeID % 0x10000 == 0x0002:
            numOfBone += 1
            if indexList[i].typeID == 0x010b0002:  # root
                rootBones.append(i)
        elif indexList[i].typeID % 0x10000 == 0x0008:
            materialIndexs.append(i)
        elif indexList[i].typeID == 0x00000004:
            numOfMesh += 1
        elif indexList[i].typeID == 0x0000000f:
            child0x0f00ChunkList.append(i)  # Assume this is linear
        elif indexList[i].typeID == 0x0000002b:
            indexOf0x2b00Chunk.append(i)
    
    for materialIndex in materialIndexs:
        loadChunk(materialIndex)

    global boneInfos
    boneInfos = [None] * numOfBone

    # Load root 0x0200 Chunk
    for rootBone in rootBones:
        loadChunk(rootBone)

    for chunk2b in indexOf0x2b00Chunk:
        loadChunk(chunk2b)

    if remove_loose_vertice:
        cleanUpMesh()

    global bones
    bones = []

    for rootBone in rootBones:
        compileBones(rootBone)

    return [meshs, materialList, bones]

call_history = []
def loadChunk(index):
    call_history.append(index)
    origonalOffset = bs.tell()
    result = None
    if index > -1:
        typeID = indexList[index].typeID 
        name = indexList[index].name
        address = indexList[index].offsetFromDataChunk + pointerOfDataChunk
        length = indexList[index].length
        debugprint("Loading %s - " % hex(index), end="")
        bs.seek(address, NOESEEK_ABS)
        if typeID % 0x10000 == 0x0002:
            debugprint("Chunk 0x0200xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0200Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0003:
            debugprint("Chunk 0x0300xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0300Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0004:
            debugprint("Chunk 0x0400xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0400Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0005:
            debugprint("Chunk 0x0500xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0500Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0006:
            debugprint("Chunk 0x0600xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0600Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0008:
            if "G2_" in name:
                name = "G2_" + name.split("G2_")[-1] + " " + fnv1a_32_str(name)
            if len(name) > 40:
                name = name[:40] + ' ' + fnv1a_32_str(name)
            if typeID == 0x02010008:
                debugprint("Chunk 0x08000102 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08000102Chunk(index, name, length)
            elif typeID == 0x02200008:
                debugprint("Chunk 0x08002002 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002002Chunk(index, name, length)
            elif typeID == 0x02220008:
                debugprint("Chunk 0x08002202 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002202Chunk(index, name, length)
            elif typeID == 0x02230008:
                debugprint("Chunk 0x08002302 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002302Chunk(index, name, length)
            elif typeID == 0x02240008:
                debugprint("Chunk 0x08002402 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002402Chunk(index, name, length)  
            elif typeID == 0x02250008:
                debugprint("Chunk 0x08002502 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002502Chunk(index, name, length) 
            elif typeID == 0x02280008:
                debugprint("Chunk 0x08002802 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002802Chunk(index, name, length)        
            elif typeID == 0x02290008:
                debugprint("Chunk 0x08002902 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002902Chunk(index, name, length)    
            elif typeID == 0x022A0008:
                debugprint("Chunk 0x08002A02 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002A02Chunk(index, name, length)    
            elif typeID == 0x022B0008:
                debugprint("Chunk 0x08002B02 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002B02Chunk(index, name, length)    
            elif typeID == 0x022C0008:
                debugprint("Chunk 0x08002C02 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002C02Chunk(index, name, length)    
            elif typeID == 0x022D0008:
                debugprint("Chunk 0x08002D02 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002D02Chunk(index, name, length)    
            elif typeID == 0x022E0008:
                debugprint("Chunk 0x08002E02 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08002E02Chunk(index, name, length)    
            elif typeID == 0x02300008:
                debugprint("Chunk 0x08003002 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08003002Chunk(index, name, length)
            elif typeID == 0x02310008:
                debugprint("Chunk 0x08003102 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08003102Chunk(index, name, length) 
            elif typeID == 0x02320008:
                debugprint("Chunk 0x08003202 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08003202Chunk(index, name, length) 
            elif typeID == 0x02330008:
                debugprint("Chunk 0x08003302 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
                result = load0x08003302Chunk(index, name, length)      
            else:
                chunkType = hex(typeID)[2:]
                while len(chunkType) != 8:
                    chunkType = "0" + chunkType
                debugprint("\n------ Error: Unknown Material Chunk: 0x%s ------" % (chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2]))
                result = loadUnknownMaterialChunk(index, name, length)
        elif typeID % 0x10000 == 0x0009:
            debugprint("Chunk 0x0900xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0900Chunk(index, name, length)
        elif typeID % 0x10000 == 0x000f:
            debugprint("Chunk 0x0f00xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x0f00Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0010:
            debugprint("Chunk 0x1000xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x1000Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0011:
            debugprint("Chunk 0x1100xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x1100Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0012:
            debugprint("Chunk 0x1200xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x1200Chunk(index, name, length)
        elif typeID % 0x10000 == 0x0019:
            debugprint("Chunk 0x1900xxxx - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            debugprint("Skip reading")
            # result = load0x1900Chunk(index, name, length)
        elif typeID == 0x03030014:
            debugprint("Chunk 0x14000303 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x14000303Chunk(index, name, length)
        elif typeID == 0x0000002b:
            debugprint("Chunk 0x2b000000 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x2b00Chunk(index, name, length)
        elif typeID == 0x0000002d:
            debugprint("Chunk 0x2d000000 - Name: %s - Address: %s - Length: %s" % (name, hex(address), hex(length)))
            result = load0x2d00Chunk(index, name, length)
        else:
            chunkType = hex(typeID)[2:]
            while len(chunkType) != 8:
                chunkType = "0" + chunkType
            debugprint("\n------ Error: Unknown Chunk type 0x%s ------" % (chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2]))
            loadUnknownChunk(index, name, length)
            # raise Exception("unknown_chunk")
            #noesis.doException("Unknown Chunk, skipped 0x %s" % chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2])
        bs.seek(origonalOffset, NOESEEK_ABS)
    else:
        debugprint("Negative Index, skipped %i" % index)
    return result


def load0x0200Chunk(index, name, length):  # Object/Bone tree
    # Load Translation
    z = bs.readFloat() * global_scale
    y = bs.readFloat() * global_scale
    x = bs.readFloat() * global_scale
    translation = NoeVec3((z, y, x))
    bs.seek(4, NOESEEK_REL)
    rotation = NoeQuat.fromBytes(bs.readBytes(16))
    scale = NoeVec3.fromBytes(bs.readBytes(12))
    bs.seek(4, NOESEEK_REL)

    # Load Extra Infomation
    parentID = bs.readUInt() - 1
    isBone = bs.readUShort() == 0x100

    numOfChild = bs.readUShort()
    bs.seek(4, NOESEEK_REL)
    boneName = getNameFromHash(bs.readUInt())
    if optimize_bone_name:
        boneName = optimizeBoneName(boneName)
    childList = []
    for i in range(numOfChild):
        childList.append(bs.readUInt() - 1)

    boneMatrix = rotation.toMat43(transposed=1)
    boneMatrix[3] = translation

    boneInfos[index] = BoneInfo(index, boneName, boneMatrix, scale, parentID, isBone, childList)

    if debug:
        debugprint("Bone %i %s" % (index, boneName))
        debugprint("Parent Bone: %i" % (parentID))
        debugprint("Child Bone: ", end='')
        debugprint(childList)
        debugprint("Is Bone? %s" % str(isBone))
        debugprint("Scale: %f, %f, %f" % (scale.getStorage()[0], scale.getStorage()[1], scale.getStorage()[2]))

    if "G2PointLight" in boneName or "G2DecalLocator" in boneName:
        boneName = loadChunk(childList[0]) #Pretty sure there's only gonna be 1
        parentID = -1
        isBone = True
        boneInfos[index] = BoneInfo(index, boneName, boneMatrix, scale, parentID, isBone, childList) #Reload data bc decal need the scale info
    else:
        global LOD
        LOD_Triggered = False
        if LOD_suffix and LOD == "":
            if boneName == "low":
                LOD = "_LOD2"
                LOD_Triggered = True
            elif boneName == "middle":
                LOD = "_LOD1"
                LOD_Triggered = True
            elif boneName == "near":
                LOD = "_LOD0"
                LOD_Triggered = True
            elif boneName == "grass":
                LOD = "_GRASS"
                LOD_Triggered = True
            if LOD_Triggered:
                debugprint("LOD Flag set")
        
        if parentID != -1:
            debugprint("Globalizing Bone %i x %i " % (index, parentID))
            boneInfos[index].setGlobalMatrix(boneMatrix * boneInfos[parentID].globalMatrix) #Globalize

        for childIndex in childList:
            result = loadChunk(childIndex)
            if(type(result) == str):
                boneName = result
                boneInfos[index].setName(boneName)

        if LOD_Triggered == True:
            debugprint("Cleared LOD Flag")
            LOD = ""

    return


def load0x0300Chunk(index, name, length):  # Mesh Data Pointer
    bs.seek(4, NOESEEK_REL)
    typeID = bs.readUInt()
    offsetFromMeshChunk = bs.readUInt()
    length = bs.readUInt()
    bs.seek(offsetFromMeshChunk + pointerOfMeshChunk, NOESEEK_ABS)
    if typeID == 0x01010000:  # VertexData
        debugprint("Loading Mesh Vertex - Index: %s - Name: %s - Address: %s" %(len(meshInfos), name, hex(bs.tell())))
        loadMeshVertex(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    elif typeID == 0x01020000:  # FaceData
        debugprint("Loading Mesh Face - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        loadMeshFace(meshInfos[-1].faceCount[-1])
    elif typeID == 0x01140000:  # WeightData
        debugprint("Loading Vertex Weight - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        if meshInfos[-1].boneMap != None:
            loadMeshWeight(meshInfos[-1].vertexCount, meshInfos[-1].boneMap)
        else:
            debugprint("Bone map doesn't exist, skip")
    elif typeID == 0x010A0000:  # Reverse Binding
        debugprint("Loading Reverse Binding - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        loadReverseBinding(meshInfos[-1].boneMap)
    elif typeID == 0x011A0000: #Tree Leaves
        debugprint("Loading Leaves Vertex - Index: %s - Name: %s - Address: %s" %(len(meshInfos), name, hex(bs.tell())))
        loadLeaves(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    elif typeID == 0x011B0000: #Grass
        debugprint("Loading Grass Vertex - Index: %s - Name: %s - Address: %s" %(len(meshInfos), name, hex(bs.tell())))
        loadGrass(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    else:
        chunkType = hex(typeID)[2:]
        debugprint("Unknown Data Chunk: 0x%s" % (chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2]))

#skiped_0x0f00_count = 0

def load0x0400Chunk(index, name, length):  # Mesh Info
    global currentMesh
    global skiped_0x0f00_count
    # Header
    numOfFaceChunk = bs.readUShort()
    bs.seek(6, NOESEEK_REL)
    parentID = bs.readUInt() - 1
    scale = boneInfos[parentID].scale
    bs.seek(4, NOESEEK_REL)
    # Subchunk 1
    indexOf0x0500Chunk = bs.readUInt() - 1
    bs.seek(28, NOESEEK_REL)
    # List of child index of 0x0600
    indexOf0x0600Chunk = []
    for i in range(numOfFaceChunk):
        indexOf0x0600Chunk.append(bs.readUInt() - 1)
    # bs.seek() TODO - seek to Subchunk 2
    name = name.split('/')[-1].split("Shape")[0]
    debugprint("Mesh detected - Name: %s Mesh Index: %i Global Index: %i Submesh count: %i Scale: %s " % (name, currentMesh, index, numOfFaceChunk, str(scale)), end="")
    if LOD == "":
        debugprint("LOD Level: None")
    else:
        debugprint("LOD Level: " + LOD[1:])
    debugprint("Index Of 0x0500 Chunk: %s" % hex(indexOf0x0500Chunk))
    debugprint("Index Of 0x0600 Chunk: ", end='')
    debugprint([hex(x) for x in indexOf0x0600Chunk])
    meshs.append(NoeMesh([], [], name + LOD))
    meshInfos.append(MeshInfo(index, name + LOD, numOfFaceChunk, parentID, indexOf0x0500Chunk, indexOf0x0600Chunk[i]))

    loadChunk(indexOf0x0500Chunk)  # Load Vertex Chain

    if len(child0x0f00ChunkList) > 0:
        if currentMesh >= len(child0x0f00ChunkList) or loadChunk(child0x0f00ChunkList[currentMesh]) == False:
            debugprint("Enumerating all 0x0f00 chunks")
            for chunk in child0x0f00ChunkList:
                if loadChunk(chunk):
                    break
            debugprint("Can't find bonemap")

    if seperate_sub_mesh:
        meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
        loadChunk(indexOf0x0600Chunk[0]) #Load First Chain
        if numOfFaceChunk > 1:
            meshs[-1].setName(name + "_0" + LOD)
            meshInfos[-1].setName(meshs[-1].name)

            for i in range(1, numOfFaceChunk):  #Load Face Chain
                meshs.append(copy.copy(meshs[-1]))
                meshs[-1].setName(name + '_' + str(i) + LOD)
                meshs[-1].setIndices([])
                meshInfos.append(copy.copy(meshInfos[-1]))
                meshInfos[-1].initialize0x0600ChunkInfo()
                meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
                meshInfos[-1].setName(meshs[-1].name)
                debugprint("Loading sub mesh %s" % meshs[-1].name)
                loadChunk(indexOf0x0600Chunk[i])    
    else:
        meshs[-1].setName(name + LOD)
        meshInfos.append(MeshInfo(index, meshs[-1].name, numOfFaceChunk, parentID, indexOf0x0500Chunk, indexOf0x0600Chunk))
        for i in indexOf0x0600Chunk:  # Load Face Chain
            loadChunk(i)
    
    currentMesh += 1



def load0x0500Chunk(index, name, length):
    # Header
    vertexCount = bs.readUInt()
    numOfElementInStruct = bs.readUInt()
    indexOf0x03000101Chunk = bs.readUInt() - 1
    bs.seek(4, NOESEEK_REL)
    # Reading struct
    vertexStruct = []
    for i in range(numOfElementInStruct):
        vertexStruct.append(bs.readUByte())
    debugprint("Vertex Struct Loaded: ", end='')
    debugprint([hex(x) for x in vertexStruct])
    # Log data and to vertex pointer
    meshInfos[-1].loadVertexInfo(vertexCount, indexOf0x03000101Chunk, vertexStruct)
    loadChunk(indexOf0x03000101Chunk)


def load0x0600Chunk(index, name, length):
    indexOf0x0800Chunk = bs.readUInt() - 1
    indexOf0x03000201Chunk = bs.readUInt() - 1
    faceCount = bs.readUShort()
    # Just gonna ignore those unknown data in between rn
    bs.seek(12, NOESEEK_REL)
    faceIndex = bs.readUShort()
    meshInfos[-1].loadFaceInfo(indexOf0x0800Chunk,indexOf0x03000201Chunk, faceCount, faceIndex)
    meshs[-1].setMaterial(indexList[indexOf0x0800Chunk].customName)

    # Load material
    #loadChunk(indexOf0x0800Chunk)

    loadChunk(indexOf0x03000201Chunk)


def load0x08000102Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "01", name))
    if material_param_as_name:
        material = NoeMaterial("01-" + name[1:], "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    '''
    header = bs.readUInt()
    subchunkID = []
    for i in range(3):
        subchunkID.append(bs.readUInt() - 1)

    debugprint("0x08000102 Chunk, %s, " % hex(header), end = '')
    [debugprint(hex(x)+', ', end = '') for x in subchunkID]
    debugprint()

    for i in range(2):
        loadChunk(subchunkID[i])
    '''
    addMaterial(material)

def load0x08002002Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "20", name))
    if material_param_as_name:
        material = NoeMaterial("20-" + name[1:], "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    addMaterial(material)

def load0x08002202Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "22", name))
    header = bs.readUInt()
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    eye_refelection = loadChunk(bs.readUInt() - 1)
    detail = loadChunk(bs.readUInt() - 1)
    eye = loadChunk(bs.readUInt() - 1)
    data = [header]
    for i in range(64):
        data.append(bs.readFloat())
    materialInfoList[-1].addMaterialData(data)
    if material_param_as_name:
        material = NoeMaterial("22-%s-%s-%s-%s" % (texture, eye_refelection, detail, eye), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    #material.setUserData(b"eye refl", eye_refelection)
    #material.setUserData(b"detail  ", detail)
    #material.setUserData(b"eye     ", eye)
    addMaterial(material)

def load0x08002302Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "23", name))
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    materialType = getNameFromHash(bs.readUInt())
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    specular = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    normal2 = loadChunk(bs.readUInt() - 1)

    data = [header1, header2, materialType]
    for i in range(20):
        data.append(bs.readFloat())
    
    materialInfoList[-1].addMaterialData(data)
    if material_param_as_name:
        material = NoeMaterial("23-%s-%s-%s-%s" % (materialType, texture, texture2, specular), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    #material.setUserData(b"material",  materialType)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    material.setSpecularTexture(specular)
    #material.setUserData(b"color2  ", texture2)
    #material.setUserData(b"normal2 ", normal2)
    addMaterial(material)

def load0x08002402Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "24", name))
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    data = [header1, header2]
    data.append("Data Chunk 1")
    for i in range(17):
        data.append(bs.readFloat())
    effect = loadChunk(bs.readUInt() - 1)
    data.append("Data Chunk 2")
    for i in range(16):
        data.append(bs.readFloat()) 
    texture = loadChunk(bs.readUInt() - 1)
    unknown1 = loadChunk(bs.readUInt() - 1)
    unknown2 = loadChunk(bs.readUInt() - 1)
    unknown3 = loadChunk(bs.readUInt() - 1)
    data.append("Data Chunk 3")
    for i in range(16):
        data.append(bs.readFloat())
    
    materialInfoList[-1].addMaterialData(data)
    if material_param_as_name:
        material = NoeMaterial("24-%s-%s-%s-%s-%s" % (texture, effect, unknown1, unknown2, unknown3), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    #material.setUserData(b'effect  ', effect)
    #material.setUserData(b'unknown1 ', unknown1)
    #material.setUserData(b'unknown2 ', unknown2)
    #material.setUserData(b'unknown3 ', unknown3)
    addMaterial(material)

def load0x08002502Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "26", name))
    bs.seek(16, NOESEEK_REL)
    unknown1 = loadChunk(bs.readUInt() - 1)
    unknown2 = loadChunk(bs.readUInt() - 1)
    unknown3 = loadChunk(bs.readUInt() - 1)
    unknown4 = loadChunk(bs.readUInt() - 1)
    unknown5 = loadChunk(bs.readUInt() - 1)
    unknown6 = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("25-%s-%s-%s-%s-%s-%s" % (unknown1, unknown2, unknown3, unknown4, unknown5, unknown6), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(unknown1)
    #material.setUserData(b'effect  ', effect)
    #material.setUserData(b'unknown1 ', unknown1)
    #material.setUserData(b'unknown2 ', unknown2)
    #material.setUserData(b'unknown3 ', unknown3)
    addMaterial(material)

def load0x08002802Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "28", name))
    bs.seek(0x64, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("28-%s" % texture, "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08002902Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "29", name))
    data = []
    data.append("Data Chunk 1")
    for i in range(7):
        data.append(bs.readFloat())
    subchunkID = []
    texture = loadChunk(bs.readUInt() - 1)
    data.append("Data Chunk 2")
    for i in range(12):
        data.append(bs.readFloat())
    normal = loadChunk(bs.readUInt() - 1)
    data.append("Data Chunk 3")
    for i in range(3):
        data.append(bs.readFloat())
    materialInfoList[-1].addMaterialData(data) 
    if material_param_as_name:
        material = NoeMaterial("29-%s" % (texture), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08002A02Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "2A", name))
    if material_param_as_name:
        material = NoeMaterial("2A-" + name[1:], "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    addMaterial(material)

def load0x08002B02Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "2B", name))
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    texture = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    texture3 = loadChunk(bs.readUInt() - 1)
    texture4 = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    normal2 = loadChunk(bs.readUInt() - 1)
    normal3 = loadChunk(bs.readUInt() - 1)
    normal4 = loadChunk(bs.readUInt() - 1)

    materialInfoList[-1].addMaterialData([header1, header2])
    if material_param_as_name:
        material = NoeMaterial("2B-%s-%s-%s-%s" % (texture,texture2,texture3,texture4), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    # material.setUserData(b'color2  ', loadChunk(bs.readUInt() - 1))
    # material.setUserData(b'color3  ', loadChunk(bs.readUInt() - 1))
    # material.setUserData(b'color4  ', loadChunk(bs.readUInt() - 1))
    # material.setUserData(b'normal2 ', loadChunk(bs.readUInt() - 1))
    # material.setUserData(b'normal3 ', loadChunk(bs.readUInt() - 1))
    # material.setUserData(b'normal4 ', loadChunk(bs.readUInt() - 1))
    addMaterial(material)

def load0x08002C02Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "2C", name))
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    interior = loadChunk(bs.readUInt() - 1)
    overlay = loadChunk(bs.readUInt() - 1)

    data = []
    for i in range(18):
        data.append(bs.readFloat())
    materialInfoList[-1].addMaterialData(data)

    if material_param_as_name:
        material = NoeMaterial("2C-%s-%s" % (texture,interior), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08002D02Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "2D", name))
    bs.seek(0x30, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    bs.seek(0x48, NOESEEK_REL)
    texture3 = loadChunk(bs.readUInt() - 1)
    texture4 = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("2D-%s-%s-%s-%s" % (texture,texture2,texture3,texture4), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08002E02Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "2E", name))
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    data = []
    for i in range(9):
        data.append(bs.readFloat())
        
    materialInfoList[-1].addMaterialData(data)
    if material_param_as_name:
        material = NoeMaterial("2E-%s" % texture, "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08003002Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "30", name))
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("30-%s" % texture, "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08003102Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "31", name))
    bs.seek(0x8, NOESEEK_REL)
    texture1 = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    texture3 = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("31-%s-%s-%s" % (texture1, texture2, texture3), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture1)
    addMaterial(material)

def load0x08003202Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "32", name))
    bs.seek(0x8, NOESEEK_REL)
    texture1 = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    if material_param_as_name:
        material = NoeMaterial("32-%s-%s" % (texture1, texture2), "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture1)
    addMaterial(material)

def load0x08003302Chunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "33", name))
    if material_param_as_name:
        material = NoeMaterial("33-" + name[1:], "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    '''
        header1 = bs.readUInt()
    subchunkID = []
    for i in range(4):
        subchunkID.append(bs.readUInt() - 1)
    data = []
    for i in range(7):
        data.append(bs.readFloat())
    '''
    addMaterial(material)

def loadUnknownMaterialChunk(index, name, length):
    materialInfoList.append(MaterialInfo(index, "Unknown", name))
    if material_param_as_name:
        material = NoeMaterial("Unknown-" + name[1:], "")
    else:
        material = NoeMaterial(name.split("/")[-1], "")
    indexList[index].setCustomName(material.name)
    '''
        header1 = bs.readUInt()
    subchunkID = []
    for i in range(4):
        subchunkID.append(bs.readUInt() - 1)
    data = []
    for i in range(7):
        data.append(bs.readFloat())
    '''
    addMaterial(material)

def load0x0900Chunk(index, name, length):
    indexOf0x1100Chunk = bs.readUInt() - 1
    data = [bs.readUInt(), bs.readUInt(), bs.readUInt()]
    materialInfoList[-1].addTextureData(index, data)
    if length == 0x30: #Atlas
        atlas = []
        for i in range(4):
            atlas.append(bs.readFloat())
        materialInfoList[-1].addTextureAtlas(atlas)
    if indexOf0x1100Chunk != -1:
        return loadChunk(indexOf0x1100Chunk)
    return ''

def load0x1100Chunk(index, name, length):
    bs.seek(12, NOESEEK_REL)
    lengthOfTextureString = bs.readUInt()
    textureString = bs.readBytes(lengthOfTextureString).decode('ASCII').rstrip("\0")
    materialInfoList[-1].addTexture(textureString)
    return textureString

def load0x1200Chunk(index, name, length):
    bs.seek(14, NOESEEK_REL)
    lengthOfModelString = bs.readUByte()
    bs.seek(1, NOESEEK_REL)
    modelString = "ext_" + bs.readBytes(lengthOfModelString).decode('ASCII').rstrip("\0")
    return "%s_%i" % (modelString, boneNameCount(modelString, call_history[-2]) + 1)

def boneNameCount(string, boneIndex):
    count = 0
    boneParentIndex = boneInfos[boneIndex].parentID
    for boneInfo in boneInfos:
        if boneInfo != None and string in boneInfo.boneName and boneInfo.parentID == boneParentIndex:
            count += 1
    return count


def load0x1000Chunk(index, name, length):
    numOfBone = bs.readUInt()  # weighted bone of the mesh
    vertexCount = bs.readUInt()
    # We assumed file strcture here is linear so don't use this, reverse search is a lot more work
    parent0x0400ID = bs.readUInt() - 1
    indexOf0x03001401Chunk = bs.readUInt() - 1
    indexOf0x03000A01Chunk = bs.readUInt() - 1
    boneMap = []
    for i in range(numOfBone):
        boneMap.append(bs.readUInt())

    #meshInfos[-1].loadBoneInfo(numOfBone, indexOf0x03001401Chunk, indexOf0x03000A01Chunk, boneMap)

    if parent0x0400ID == meshInfos[-1].index:
        meshInfos[-1].loadBoneInfo(numOfBone, indexOf0x03001401Chunk, indexOf0x03000A01Chunk, boneMap)
    else:
        debugprint(hex(parent0x0400ID))
        for meshInfo in meshInfos:
            if parent0x0400ID == meshInfo.index:
                meshInfo.loadBoneInfo(numOfBone, indexOf0x03001401Chunk, indexOf0x03000A01Chunk, boneMap)
                break
        return False
        #noesis.doException("0x1000 Chunk Out Of Order!!!! %s %s" % (hex(parent0x0400ID), hex(meshInfos[-1].index)))

    # if "obj_hair" in meshInfos[-1].name:
    loadChunk(indexOf0x03000A01Chunk)

    loadChunk(indexOf0x03001401Chunk)

    return True


def load0x0f00Chunk(index, name, length):
    bs.seek(8, NOESEEK_REL)
    indexOf0x1000Chunk = bs.readUInt() - 1
    return loadChunk(indexOf0x1000Chunk)

def load0x14000303Chunk(index, name, length):
    parentID = call_history[-2]
    scale = boneInfos[parentID].scale.getStorage()
    intensity = bs.readFloat()
    R = bs.readFloat()
    G = bs.readFloat()
    B = bs.readFloat()
    bs.seek(4, NOESEEK_REL)
    falloff = bs.readFloat()
    return "PL%i-%s-%s-%s-%s-%s-%s-%s-%s" % (index, str(round(intensity, 3)), str(round(R, 3)), str(round(G, 3)), str(round(B, 3)), str(round(falloff, 3)), str(round(scale[0], 3)), str(round(scale[1], 3)), str(round(scale[2], 3)))

def load0x2d00Chunk(index, name, length):
    parentID = call_history[-2]
    name = indexList[parentID].name.split('/')[-1] 
    materialInfoList.append(MaterialInfo(index, "DC", name))
    bs.seek(4, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1) 
    debugprint(parentID)
    data = list(boneInfos[parentID].scale.getStorage())
    for i in range(13):
        data.append(bs.readFloat())
    materialInfoList[-1].addMaterialData(data)
    #return "DC%i-%s" % (index, texture)
    return name

def load0x2b00Chunk(index, name, length):
    numOfDataInMeshChunk0x1500 = bs.readUInt()
    numOfDataInMeshChunk0x1600 = bs.readUInt()
    numOfDataInMeshChunk0x1700 = bs.readUInt()
    unknown1 = bs.readFloat()
    bs.seek(4, NOESEEK_REL)
    unknown2 = bs.readFloat()
    bs.seek(4, NOESEEK_REL)
    unknown3 = bs.readFloat()
    bs.seek(4, NOESEEK_REL)
    unknown4 = bs.readFloat()
    parent0x0400ID = bs.readUInt()
    indexOfMeshChunk0x1500 = bs.readUInt() - 1
    indexOfMeshChunk0x1600 = bs.readUInt() - 1
    indexOfMeshChunk0x1700 = bs.readUInt() - 1

    debugprint("%i, %i, %i, %i, %i, %i, %f, %f, %f, %f" % (numOfDataInMeshChunk0x1500, numOfDataInMeshChunk0x1600, numOfDataInMeshChunk0x1700, indexOfMeshChunk0x1500, indexOfMeshChunk0x1600, indexOfMeshChunk0x1700, unknown1, unknown2, unknown3, unknown4))

    for meshInfo in meshInfos:
        if parent0x0400ID == meshInfo.index:
            debugprint("Parent - %s" % meshInfo.name)
            meshInfo.load2BInfo(numOfDataInMeshChunk0x1500, numOfDataInMeshChunk0x1600, numOfDataInMeshChunk0x1700, indexOfMeshChunk0x1500, indexOfMeshChunk0x1600, indexOfMeshChunk0x1700)
            break
        debugprint("Can't find parent %i" % parent0x0400ID)
        return False
    
def loadUnknownChunk(index, name, length):
    parentID = call_history[-2]
    name = indexList[parentID].name.split('/')[-1] 
    materialInfoList.append(MaterialInfo(index, "Unknown", name))
    materialInfoList[-1].addMaterialData([])
    #return "DC%i-%s" % (index, texture)
    return name

def loadMeshVertex(vertexCount, vertexStruct):
    vertexs = []
    uvCount = vertexStruct.count(0x9E)
    # debugprint("Vertex Count: %i" % vertexCount)
    # debugprint("UV Map Count: %i" % uvCount)
    uvs = []
    colors = []
    normals = []
    tangents = []
    if print_vertice_csv:
        for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex Ruler XYZ
                debugprint("Vertex 1, Vertex 2, Vertex 3, ", end = "")
            elif dataType == 0x84:  # Vertex Quaternion
                debugprint("Vertex 1, Vertex 2, Vertex 3, Vertex 4, ", end = "")
            elif dataType == 0xA1:  # Normal
                debugprint("Normal X, Normal Y, Normal Z, ", end = "")
            elif dataType == 0x9C:  # Texture weight
                debugprint("Vertex color R, Vertex color G, Vertex color B, Vertex color A, ", end = "")
            elif dataType == 0x9E:  # UV
                for i in range (uvCount):
                    debugprint("UV%i 1, UV%i 2, " % (i, i), end = "")
            elif dataType == 0x88:  # Tangent
                debugprint("Tangent X, Tangent Y, Tangent Z, Tangent W, ", end = "")
            elif dataType == 0x87:  # BitTangent
                debugprint("BitTangent X, BitTangent Y, BitTangent Z, BitTangent W, ", end = "")
        debugprint()

    for vertex in range(vertexCount):
        uvLoaded = 0
        for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex XYZ
                rawTransform = NoeVec3((bs.readFloat(), bs.readFloat(), bs.readFloat())) #Read XYZ
                if print_vertice_csv:
                    debugprint("%f, %f, %f,\t" % (rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2]), end = "")
                rawTransform *= NoeVec3((global_scale, global_scale, global_scale)) #GlobalScale
                rawTransform *= boneInfos[meshInfos[-1].parentID].scale #LocalScale
                rawTransform *= boneInfos[meshInfos[-1].parentID].globalMatrix #Globalization
                transform = NoeVec3((rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2])) #Get NoeVec3 From Mat43
                vertexs.append(transform)

            elif dataType == 0x84:  # Vertex XYZ?
                rawTransform = NoeVec4((bs.readFloat(), bs.readFloat(), bs.readFloat(), bs.readFloat())) #Read XYZ?
                if print_vertice_csv:
                    debugprint("%f, %f, %f, %f,\t" % (rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2], rawTransform.getStorage()[3]), end = "")
                rawTransform = rawTransform.toVec3() #Reduce it to XYZ
                rawTransform *= NoeVec3((global_scale, global_scale, global_scale)) #Scale
                rawTransform *= boneInfos[meshInfos[-1].parentID].globalMatrix #Globalization
                transform = NoeVec3((rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2])) #Get NoeVec3 From Mat43
                vertexs.append(transform)
            elif dataType == 0xA1:  # Normal?
                normalbytes = bs.readBytes(4) 
                normal = read101111vec(normalbytes)
                normals.append(normal)
                if print_vertice_csv:
                    debugprint("%f, %f, %f, \t" % (normal.getStorage()[0], normal.getStorage()[1], normal.getStorage()[2]), end = "")
            elif dataType == 0x9C:  # Texture weight
                r = bs.readUByte() / 255
                g = bs.readUByte() / 255
                b = bs.readUByte() / 255
                a = bs.readUByte() / 255
                colors.append(NoeVec4([r,g,b,a]))
                if print_vertice_csv:
                    debugprint("%f, %f, %f, %f,\t" % (r,g,b,a), end = "")
            elif dataType == 0x9E:  # UV
                u = bs.readShort()/1024  
                v = bs.readShort()/1024
                if print_vertice_csv:
                    debugprint("%f, %f,\t" % (u, v), end = "")
                if(len(uvs) <= uvLoaded):
                    uvs.append([])
                uvs[uvLoaded].append(NoeVec3((u, v, 0)))
                uvLoaded += 1
            elif dataType == 0x88:  # Tangent
                tangent = NoeVec3([bs.readHalfFloat(), bs.readHalfFloat(), bs.readHalfFloat()]).normalize()
                bitTangentSign = bs.readHalfFloat()
                bitTangent = (normal.cross(tangent) * NoeVec3([bitTangentSign, bitTangentSign, bitTangentSign])).normalize()
                if print_vertice_csv:
                    debugprint("%f, %f, %f, %f,\t" % (tangent.getStorage()[0], tangent.getStorage()[1], tangent.getStorage()[2], bitTangentSign), end = "")
                tangentMat = NoeMat43([normal, tangent, bitTangent, NoeVec3((0,0,0))])
                tangents.append(tangentMat)
            elif dataType == 0x87:  # Bit tangent - Not gonna use this because we can calculate it above
                x = bs.readHalfFloat()
                y = bs.readHalfFloat()
                z = bs.readHalfFloat()
                w = bs.readHalfFloat()
                bitTangent = NoeVec3((x, y, z)).normalize()
                if print_vertice_csv:
                    debugprint("%f, %f, %f, %f, \t" % (bitTangent.getStorage()[0], bitTangent.getStorage()[1], bitTangent.getStorage()[2], w), end = "")
        if print_vertice_csv:
            debugprint()

    meshs[-1].setPositions(vertexs)
    if export_normal_and_tangent:
        meshs[-1].setNormals(normals)
        meshs[-1].setTangents(tangents)

    if len(uvs) > 0:
        meshs[-1].setUVs(uvs[0], 0)
        for i in range(1, uvCount):
            meshs[-1].setUVs(uvs[i], i+1)
    
    meshs[-1].setColors(colors)

def loadLeaves(vertexCount, vertexStruct):
    if print_vertice_csv:
        for dataType in vertexStruct:
            if dataType == 0x84:  # Vertex XYZW
                debugprint("Vertex 1, Vertex 2, Vertex 3, Vertex 4, ", end = "")
        debugprint()

    vertexs = []
    for vertex in range(vertexCount):
        uvLoaded = 0
        for dataType in vertexStruct:
            if dataType == 0x84:  # Vertex XYZW
                rawTransform = NoeVec4((bs.readFloat(), bs.readFloat(), bs.readFloat(), bs.readFloat())) #Read XYZW
                if print_vertice_csv:
                    debugprint("%f, %f, %f, %f, " % (rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2], rawTransform.getStorage()[3]), end = "")
                rawTransform = rawTransform.toVec3() #Reduce it to XYZ
                rawTransform *= NoeVec3((global_scale, global_scale, global_scale)) #Scale
                rawTransform *= boneInfos[meshInfos[-1].parentID].globalMatrix #Globalization
                transform = NoeVec3((rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2])) #Get NoeVec3 From Mat43
                vertexs.append(transform)
        if print_vertice_csv:
            debugprint()

    meshs[-1].setPositions(vertexs)

def loadGrass(vertexCount, vertexStruct):
    vertexs = []
    for vertex in range(vertexCount):
        uvLoaded = 0
        for dataType in vertexStruct:
            if dataType == 0x84:  # Vertex Quaternion
                rawTransform = NoeVec4((bs.readFloat(), bs.readFloat(), bs.readFloat(), bs.readFloat())).toVec3() #Read Quad and convert it to Ruler XYZ
                rawTransform *= NoeVec3((global_scale, global_scale, global_scale)) #Scale
                rawTransform *= boneInfos[meshInfos[-1].parentID].globalMatrix #Globalization
                transform = NoeVec3((rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2])) #Get NoeVec3 From Mat43
                vertexs.append(transform)

    meshs[-1].setPositions(vertexs)



def loadMeshFace(faceCount):
    debugprint("Reading Face, face count: %i" % faceCount)
    faces = []
    for face in range(faceCount):
        faces.append(bs.readUShort())
        faces.append(bs.readUShort())
        faces.append(bs.readUShort())
    meshs[-1].setIndices(meshs[-1].indices + faces)


def loadMeshWeight(vertexCount, boneMap):
    weightList = []
    for vertex in range(vertexCount):
        weight = []
        linkedBone = []
        for i in range(4):
            weight.append(bs.readHalfFloat())
        for i in range(4):
            linkedBone.append(bs.readUShort())

        try:
            weight.remove(0)
        except:
            pass

        linkedBone = linkedBone[:len(weight)]
        if len(weight) != len(linkedBone):
            noesis.doException("Error. NoeVertWeight mismatch. %s   %s" % (str(linkedBone), str(weight)))

        linkedBone = [boneMap[x]-1 for x in linkedBone]  # Globlize bone Index
        weightList.append(NoeVertWeight(linkedBone, weight))
    meshs[-1].setWeights(weightList)

def loadReverseBinding(boneMap):
    #debugprint(hex(bs.tell()))
    if reverse_binding:
        for index in boneMap:
            reverse_binding_matrix = NoeMat44.fromBytes(bs.readBytes(64)).inverse().toMat43()
            reverse_binding_matrix[3][0] *= global_scale
            reverse_binding_matrix[3][1] *= global_scale
            reverse_binding_matrix[3][2] *= global_scale
            boneInfos[index-1].setReverseBindingMatrix(reverse_binding_matrix)
    #debugprint(hex(bs.tell()))
            

def printMeshCSV():
    debugprint("Mesh CSV List ----------------------------------------")
    debugprint("Name|Index|Vertex Count|Submesh Count|Face Count|Texture|Type Of Material|Vertex Struct|Index Of 0x0500Chunk|Index Of 0x0600Chunk|Index Of 0x0800Chunk")
    for meshInfo in meshInfos:
        debugprint(meshInfo.name, hex(meshInfo.index), meshInfo.vertexCount, meshInfo.numOfFaceChunk, meshInfo.faceCount, meshInfo.texture, [typeOf0x0800Chunk(x) for x in meshInfo.indexOf0x0800Chunk], [hex(x) for x in meshInfo.vertexStruct], hex(meshInfo.indexOf0x0500Chunk), [hex(x) for x in meshInfo.indexOf0x0600Chunk], [hex(x) for x in meshInfo.indexOf0x0800Chunk], sep="|")

def typeOf0x0800Chunk(index):
    origonalOffset = bs.tell()
    bs.seek(index*0x10 + 0x36, NOESEEK_ABS)
    chunkType = hex(bs.readUShort()+ 0x10000)
    bs.seek(origonalOffset, NOESEEK_ABS)
    return chunkType[5:]+chunkType[3:5]

def cleanUpMesh():
    for i in range(0, len(meshs)):
        debugprint("Cleaning up mesh " + meshs[i].name)
        if len(meshs[i].indices) == 0: #Don't clean up tree leaves, they are vertex cloud
            continue

        debugprint("Vertice Count: %i"  % len(meshs[i].positions))
        vertice_used = [False] * len(meshs[i].positions)
        for x in meshs[i].indices:
            vertice_used[x] = True

        lookUpTable = []
        current_index = 0
        #Generate look up table
        for x in range(0, len(meshs[i].positions)):
            lookUpTable.append(-1)
            if vertice_used[x]:
                lookUpTable[-1] = current_index
                current_index += 1
        
        #Regenerate face with look up table
        new_indice = []
        for indices in meshs[i].indices:
            new_indice.append(lookUpTable[indices])
        meshs[i].setIndices(new_indice)

        new_vertice = []
        #generate new vertice list
        for x in range(len(meshs[i].positions)):
            if vertice_used[x]:
                new_vertice.append(meshs[i].positions[x])
        meshs[i].setPositions(new_vertice)

        #generate new uv list 
        new_uv = []
        # debugprint("UV Count: %i" % len(meshs[i].uvs))
        for x in range(len(meshs[i].uvs)):
            if vertice_used[x]:
                new_uv.append(meshs[i].uvs[x])
        meshs[i].setUVs(new_uv)

        #generate new additional uv list 
        for current_uv in range(len(meshs[i].uvxList)):
            new_uv = []
            for x in range(len(meshs[i].uvxList[current_uv])):
                if vertice_used[x]:
                    new_uv.append(meshs[i].uvxList[current_uv][x])
            meshs[i].setUVs(new_uv, current_uv+2)

        if export_normal_and_tangent:
            #generate new normal list
            new_normal = []
            for x in range(len(meshs[i].normals)):
                if vertice_used[x]:
                    new_normal.append(meshs[i].normals[x])
            meshs[i].setNormals(new_normal)

            #generate new tangent list
            new_tangent = []
            for x in range(len(meshs[i].tangents)):
                if vertice_used[x]:
                    new_tangent.append(meshs[i].tangents[x])
            meshs[i].setTangents(new_tangent)

        #generate new vertex color list
        if len(meshs[i].colors) != 0:
            new_colors = []
            for x in range(0, len(meshs[i].colors)):
                if vertice_used[x]:
                    new_colors.append(meshs[i].colors[x])
            meshs[i].setColors(new_colors)

        #generate new weight list
        if len(meshs[i].weights) != 0:
            new_weights = []
            for x in range(0, len(meshs[i].weights)):
                if vertice_used[x]:
                    new_weights.append(meshs[i].weights[x])
            meshs[i].setWeights(new_weights)

        #Update mesh info
            meshInfos[i].setVertexCount(current_index + 1)

def addMaterial(material):
    for mat in materialList:
        if material.name == mat.name:
            return False
    materialList.append(material)
    return True

def compileBones(index):
    if index < numOfBone:
        bone = boneInfos[index]
        # if bone.isBone:
        if bone.hasRPB == False and bone.parentID != -1:
            bone.setGlobalMatrix(bone.boneMatrix * boneInfos[bone.parentID].globalMatrix) #Globalize

        bones.append(NoeBone(bone.index, bone.boneName, bone.globalMatrix, None, bone.parentID))
        for child in bone.childList:
            compileBones(child)

def printMaterial():
    debugprint("MATERIAL INFO--------------------------------------------")
    readed_material = []
    for material in materialInfoList:
        if material.index not in readed_material:
            debugprint("Material#%s - %s - Type %s" % (hex(material.index), material.name, material.chunkType))
            readed_material.append(material.index) #DC will cause duplicated info be recorded
            if len(material.data) != 0:
                debugprint("Parameters: ", end = '')
                [debugprint(str(x)+', ', end = '') for x in material.data]
                debugprint()
            for texture in material.textureList:
                debugprint(texture[2] + ", ", end = '')
                [debugprint(hex(x)+', ', end = '') for x in texture[1]]
                if texture[3] != None:
                    debugprint("Atlas: ", end = '')
                    [debugprint(str(x)+', ', end = '') for x in texture[3]]
                debugprint()
            debugprint()

def exportMaterialJson():
    debugprint("Exporting Material Json")
    exportJsonData = {}
    readed_material = []
    for material in materialInfoList:
        if material.index not in readed_material:
            readed_material.append(material.index) #DC will cause duplicated info be recorded, this is a cheesy way to fix it
            exportJsonData[material.name] = {}
            exportJsonData[material.name]["Type"] = material.chunkType
            exportJsonData[material.name]["Index"] = material.index

            if len(material.data) != 0:
                exportJsonData[material.name]["Parameters"] = material.data

            if len(material.textureList) != 0:
                textureData = {}
                for texture in material.textureList:
                    currentTexture = {}
                    currentTexture["Name"] = texture[2]
                    currentTexture["Parameters"] = texture[1]
                    if texture[3] != None:
                        currentTexture["Atlas"] = texture[3]
                    textureData["Texture%i" % (len(textureData) + 1)] = currentTexture
                exportJsonData[material.name]["Textures"] = textureData

    os.makedirs(os.path.dirname(export_material_json), exist_ok=True)
    with open("%s\%s.json" % (export_material_json, modelName), 'w') as outfile:
        json.dump(exportJsonData, outfile, indent=4, separators=(',', ': '), sort_keys=True)

def read101111vec(input):
    value = int.from_bytes(input, "little", signed = False)
    z = NoeBitStream(((value >> 17) & 0x7FE0).to_bytes(2, byteorder='little'))
    z = z.readHalfFloat() * 2 - 1.0
    y = NoeBitStream(((value >> 7) & 0x7FF0).to_bytes(2, byteorder='little'))
    y = y.readHalfFloat() * 2 - 1.0
    x = NoeBitStream(((value << 4) & 0x7FF0).to_bytes(2, byteorder='little'))
    x = x.readHalfFloat() * 2 - 1.0
    return NoeVec3((x, y, z)).normalize()

def optimizeBoneName(origonal_name):
    nameList = [
        ("bn_pelvis_end", "Hips"),
        ("bn_spine0", "Spine"),
        ("bn_spine2", "Chest"),
        ("bn_neck", "Neck"),
        ("bn_head", "Head"),
        ("bn_l_thigh", "Left Leg"),
        ("bn_r_thigh", "Right Leg"),
        ("bn_l_leg", "Left Knee"),
        ("bn_r_leg", "Right Knee"),
        ("bn_l_foot", "Left Ankle"),
        ("bn_r_foot", "Right Ankle"),
        ("bn_l_toe", "Left Toe"),
        ("bn_r_toe", "Right Toe"),
        ("bn_l_clavicle", "Left Shoulder"),
        ("bn_r_clavicle", "Right Shoulder"),
        ("bn_l_arm", "Left Arm"),
        ("bn_r_arm", "Right Arm"), 
        ("bn_l_forearm", "Left Elbow"),
        ("bn_r_forearm", "Right Elbow"),
        ("bn_l_hand", "Left Wrist"),
        ("bn_r_hand", "Right Wrist"),
        ("bn_l_fingerB0", "Left Index 1"),
        ("bn_l_fingerB1", "Left Index 2"),
        ("bn_l_fingerB2", "Left Index 3"),
        ("bn_l_fingerC0", "Left Middle 1"),
        ("bn_l_fingerC1", "Left Middle 2"),
        ("bn_l_fingerC2", "Left Middle 3"),
        ("bn_l_fingerD0", "Left Ring 1"),
        ("bn_l_fingerD1", "Left Ring 2"),
        ("bn_l_fingerD2", "Left Ring 3"),
        ("bn_l_fingerE0", "Left Pinky 1"),
        ("bn_l_fingerE1", "Left Pinky 2"),
        ("bn_l_fingerE2", "Left Pinky 3"),
        ("bn_l_fingerA0", "Left Thumb 1"),
        ("bn_l_fingerA1", "Left Thumb 2"),
        ("bn_l_fingerA2", "Left Thumb 3"),
        ("bn_r_fingerB0", "Right Index 1"),
        ("bn_r_fingerB1", "Right Index 2"),
        ("bn_r_fingerB2", "Right Index 3"),
        ("bn_r_fingerC0", "Right Middle 1"),
        ("bn_r_fingerC1", "Right Middle 2"),
        ("bn_r_fingerC2", "Right Middle 3"), 
        ("bn_r_fingerD0", "Right Ring 1"),
        ("bn_r_fingerD1", "Right Ring 2"),
        ("bn_r_fingerD2", "Right Ring 3"), 
        ("bn_r_fingerE0", "Right Pinky 1"), 
        ("bn_r_fingerE1", "Right Pinky 2"), 
        ("bn_r_fingerE2", "Right Pinky 3"), 
        ("bn_r_fingerA0", "Right Thumb 1"), 
        ("bn_r_fingerA1", "Right Thumb 2"), 
        ("bn_r_fingerA2", "Right Thumb 3")]

    for name in nameList:
        if name[0] == origonal_name:
            return name[1]
        
    return origonal_name