# Noesis Gravity Rush 2 GFX Extractor V2
# Written by 203Null
# Reverse Engineered by 203Null and FreezeCook
# Strcture Note: https://docs.google.com/document/d/1eW8BNMuE6chZebgClRnRoxRCEMDCAKPadYEhpK4AIV0/edit?usp=sharing

from inc_noesis import *
import noesis
import rapi
import os
import copy

debug = False  # please change to False out when done.
print_CSV = False
seperate_sub_mesh = True
global_scale = 100
remove_loose_vertice = True
LOD_suffix = False
reverse_binding = True


def registerNoesisTypes():
    handle = noesis.register('Gravity Rush 2 GFX', '.gfx')
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadModel(handle, noepyLoadModel)
    if debug:
        noesis.logPopup()
    loadNameHashDict()
    return 1


def noepyCheckType(data):
    file = NoeBitStream(data)
    if len(data) < 4:
        return 0
    header = file.readBytes(4).decode('ASCII').rstrip("\0")
    if header == 'GFX2':
        return 1
    return 0


FNV1A_32_OFFSET = 0x811c9dc5
FNV1A_32_PRIME = 0x01000193


def fnv1a_32_str(string):
    # Set the offset basis
    hash = FNV1A_32_OFFSET

    # For each character
    for character in string:
        # Xor with the current character
        hash ^= ord(character)

        # Multiply by prime
        hash *= FNV1A_32_PRIME

        # Clamp
        hash &= 0xffffffff

    # Return the final hash as a number
    hash = hex(hash)[2:]
    if len(hash) == 7:
        hash = '0' + hash
    hash = hash[6:8]+hash[4:6]+hash[2:4]+hash[0:2]
    return hash


def loadNameHashDict():
    if not "gr_namehash" in globals():
        global gr_namehash
        gr_namehash = {}
        print(os.getcwd())
        count = 0
        for r, d, f in os.walk(os.getcwd()+'\GR_Hash_Dict'):
            for file in f:
                print("Scaning directory: %s" % file)
                if '.txt' in file:
                    txt = open(os.getcwd()+'\GR_Hash_Dict\\'+file, mode='r')
                    for line in txt:
                        line = line.split('\n')[0]
                        try:
                            gr_namehash[line.split('\t')[1]] = line.split('\t')[0]
                            #print("Dictionary loaded: %s with name %s" % (line.split('\t')[1], line.split('\t')[0]))
                        except:
                            gr_namehash[line.split('\t')[0]] = fnv1a_32_str(
                                line.split('\t')[0])
                            print("Dictionary calculated: %s %s" % (line.split('\t')[0], gr_namehash[line.split('\t')[0]]))
                        count += 1
        print("Dictionary loaded with %i strings" % count)
    else:
        print("Dictionary alread loaded")


def getNameFromHash(nameHash):
    nameHash = hex(nameHash)[2:]
    if len(nameHash) == 7:
        nameHash = '0' + nameHash
    nameHash = nameHash[6:8]+nameHash[4:6]+nameHash[2:4]+nameHash[0:2]
    try:
        return gr_namehash[nameHash]
    except:
        print("Can't find string of hash %s" % nameHash)
        return nameHash


class IndexChunk:
    def __init__(self, name, typeID, offset, length):
        self.name = name
        self.typeID = typeID
        self.offsetFromDataChunk = offset
        self.length = length

    def setCustomName(self, customName):
        self.customName = customName

class BoneInfo:
    def __init__(self, index, boneName, boneMatrix, parentID, isBone, childList):
        self.index = index
        self.boneName = boneName
        self.boneMatrix = boneMatrix
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

    def loadTexture(self, texture):  # Infomations from list of child 0x1100 Chunk
        self.texture.append(texture)

    def setName(self, name):
        self.name = name

    def setIndexOf0x0600Chunk(self, indexOf0x0600Chunk):
        self.indexOf0x0600Chunk = indexOf0x0600Chunk

    def setVertexCount(self, vertexCount):
        self.vertexCount = vertexCount


def noepyLoadModel(data, mdlList):
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

    if remove_loose_vertice:
        cleanUpMesh()

    global bones
    bones = []

    for rootBone in rootBones:
        compileBones(rootBone)

    model = NoeModel(meshs)
    model.setModelMaterials(NoeModelMaterials([], materialList))
    model.setBones(bones)
    mdlList.append(model)

    if print_CSV:
        printMeshCSV()

    return 1


def loadChunk(index):
    origonalOffset = bs.tell()
    result = None
    if index > -1:
        print("Loading %s - " % hex(index), end="")
        bs.seek(indexList[index].offsetFromDataChunk + pointerOfDataChunk, NOESEEK_ABS)
        if indexList[index].typeID % 0x10000 == 0x0002:
            print("Chunk 0x0200xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0200Chunk(index, indexList[index].name, indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0003:
            print("Chunk 0x0300xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0300Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0004:
            print("Chunk 0x0400xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0400Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0005:
            print("Chunk 0x0500xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0500Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0006:
            print("Chunk 0x0600xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0600Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02010008:
            print("Chunk 0x08000102 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08000102Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02200008:
            print("Chunk 0x08002002 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002002Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02220008:
            print("Chunk 0x08002202 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002202Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02230008:
            print("Chunk 0x08002302 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002302Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02240008:
            print("Chunk 0x08002402 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002402Chunk(index, indexList[index].name,  indexList[index].length)  
        elif indexList[index].typeID == 0x02250008:
            print("Chunk 0x08002502 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002502Chunk(index, indexList[index].name,  indexList[index].length) 
        elif indexList[index].typeID == 0x02280008:
            print("Chunk 0x08002802 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002802Chunk(index, indexList[index].name,  indexList[index].length)        
        elif indexList[index].typeID == 0x02290008:
            print("Chunk 0x08002902 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002902Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022A0008:
            print("Chunk 0x08002A02 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002A02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022B0008:
            print("Chunk 0x08002B02 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002B02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022C0008:
            print("Chunk 0x08002C02 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002C02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022D0008:
            print("Chunk 0x08002D02 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002D02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022E0008:
            print("Chunk 0x08002E02 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002E02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x02300008:
            print("Chunk 0x08003002 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08003002Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02320008:
            print("Chunk 0x08003202 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08003202Chunk(index, indexList[index].name,  indexList[index].length) 
        elif indexList[index].typeID == 0x02330008:
            print("Chunk 0x08003302 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08003302Chunk(index, indexList[index].name,  indexList[index].length)                 
        elif indexList[index].typeID % 0x10000 == 0x0009:
            print("Chunk 0x0900xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0900Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0011:
            print("Chunk 0x1100xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x1100Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0012:
            print("Chunk 0x1200xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            print("External LOD reference, unneeded, skip")
        elif indexList[index].typeID % 0x10000 == 0x000f:
            print("Chunk 0x0f00xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0f00Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0010:
            print("Chunk 0x1000xxxx - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x1000Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x03030014:
            print("Chunk 0x14000303 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x14000303Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x0000002d:
            print("Chunk 0x2d000000 - Name: %s - Address: %s - Length: %s" % (indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x2d00Chunk(index, indexList[index].name,  indexList[index].length)
        else:
            chunkType = hex(indexList[index].typeID)[2:]
            while len(chunkType) != 8:
                chunkType = "0" + chunkType
            print("\n------ Warning: Unknown Chunk, skipped 0x%s ------" % (chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2]))
            #noesis.doException("Unknown Chunk, skipped 0x %s" % chunkType[6:8]+chunkType[4:6]+chunkType[2:4]+chunkType[0:2])
        bs.seek(origonalOffset, NOESEEK_ABS)
    else:
        print("Negative Index, skipped %i" % index)
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
    childList = []
    for i in range(numOfChild):
        childList.append(bs.readUInt() - 1)

    boneMatrix = rotation.toMat43(transposed=1)
    boneMatrix[3] = translation

    if debug:
        print("Bone %i %s" % (index, boneName))
        print("Parent Bone: %i" % (parentID))
        print("Child Bone: ", end='')
        print(childList)
        print("Is Bone? %s" % str(isBone))

    if "G2PointLight" in boneName or "G2DecalLocator" in boneName:
        boneName = loadChunk(childList[0]) #Pretty sure there's only gonna be 1
        parentID = -1
        isBone = True
    # elif "atg" in name:
    #     isBone = True

    boneInfos[index] = BoneInfo(index, boneName, boneMatrix, parentID, isBone, childList)
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
            print("LOD Flag set")
    
    if parentID != -1:
        print("Globalizing Bone %i x %i " % (index, parentID))
        boneInfos[index].setGlobalMatrix(boneMatrix * boneInfos[parentID].globalMatrix) #Globalize

    for childIndex in childList:
        loadChunk(childIndex)

    if LOD_Triggered == True:
        print("Cleared LOD Flag")
        LOD = ""

    return


def load0x0300Chunk(index, name, length):  # Mesh Data Pointer
    bs.seek(4, NOESEEK_REL)
    typeID = bs.readUInt()
    offsetFromMeshChunk = bs.readUInt()
    length = bs.readUInt()
    bs.seek(offsetFromMeshChunk + pointerOfMeshChunk, NOESEEK_ABS)
    if typeID == 0x01010000:  # VertexData
        print("Loading Mesh Vertex - Index: %s - Name: %s - Address: %s" %(len(meshInfos), name, hex(bs.tell())))
        loadMeshVertex(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    elif typeID == 0x01020000:  # FaceData
        print("Loading Mesh Face - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        loadMeshFace(meshInfos[-1].faceCount[-1])
    elif typeID == 0x01140000:  # WeightData
        print("Loading Vertex Weight - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        loadMeshWeight(meshInfos[-1].vertexCount, meshInfos[-1].boneMap)
    elif typeID == 0x010A0000:  # Reverse Binding
        print("Loading Reverse Binding - Index: %s - Name: %s - Address: %s" % (len(meshInfos), name, hex(bs.tell())))
        loadReverseBinding(meshInfos[-1].boneMap)

def load0x0400Chunk(index, name, length):  # Mesh Info
    global currentMesh
    # Header
    numOfFaceChunk = bs.readUShort()
    bs.seek(6, NOESEEK_REL)
    parentID = bs.readUInt() - 1
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
    print("Mesh detected - Name: %s Mesh Index: %i Global Index: %i Submesh count: %i " % (name, currentMesh, index, numOfFaceChunk), end="")
    if LOD == "":
        print("LOD Level: None")
    else:
        print("LOD Level: " + LOD[1:])
    print("Index Of 0x0500 Chunk: %s" % hex(indexOf0x0500Chunk))
    print("Index Of 0x0600 Chunk: ", end='')
    print([hex(x) for x in indexOf0x0600Chunk])
    meshs.append(NoeMesh([], [], name + LOD))
    meshInfos.append(MeshInfo(index, name + LOD, numOfFaceChunk, parentID, indexOf0x0500Chunk, indexOf0x0600Chunk[i]))

    loadChunk(indexOf0x0500Chunk)  # Load Vertex Chain

    if len(child0x0f00ChunkList) > 0:
        loadChunk(child0x0f00ChunkList[currentMesh])

    if seperate_sub_mesh:
        meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
        loadChunk(indexOf0x0600Chunk[0]) #Load First Chain
        if numOfFaceChunk > 1:
            meshs[-1].setName(name + "_0" + LOD)
            meshInfos[-1].setName(meshs[-1].name)

            for i in range(1, numOfFaceChunk):  #Load Face Chain
                meshs.append(copy.deepcopy(meshs[-1]))
                meshs[-1].setName(name + '_' + str(i) + LOD)
                meshs[-1].setIndices([])
                meshInfos.append(copy.deepcopy(meshInfos[-1]))
                meshInfos[-1].initialize0x0600ChunkInfo()
                meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
                meshInfos[-1].setName(meshs[-1].name)
                print("Loading sub mesh %s" % meshs[-1].name)
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
    print("Vertex Struck Loaded: ", end='')
    print([hex(x) for x in vertexStruct])
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
    material = NoeMaterial("01-" + name[1:], "")
    indexList[index].setCustomName(material.name)
    '''
    header = bs.readUInt()
    subchunkID = []
    for i in range(3):
        subchunkID.append(bs.readUInt() - 1)

    print("0x08000102 Chunk, %s, " % hex(header), end = '')
    [print(hex(x)+', ', end = '') for x in subchunkID]
    print()

    for i in range(2):
        loadChunk(subchunkID[i])
    '''
    addMaterial(material)

def load0x08002002Chunk(index, name, length):
    material = NoeMaterial("20-" + name[1:], "")
    indexList[index].setCustomName(material.name)
    addMaterial(material)

def load0x08002202Chunk(index, name, length):
    header = bs.readUInt()
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    eye_refelection = loadChunk(bs.readUInt() - 1)
    detail = loadChunk(bs.readUInt() - 1)
    eye = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("22-%s-%s-%s-%s" % (texture, eye_refelection, detail, eye), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    #material.setUserData(b"eye refl", eye_refelection)
    #material.setUserData(b"detail  ", detail)
    #material.setUserData(b"eye     ", eye)
    addMaterial(material)

def load0x08002302Chunk(index, name, length):
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    materialType = getNameFromHash(bs.readUInt())
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    specular = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    normal2 = loadChunk(bs.readUInt() - 1)
    #print("Material Loaded - %s - %s - %s - %s - %s - %s" % (materialType, texture, normal, specular, texture2, normal2))
    material = NoeMaterial("23-%s-%s-%s-%s" % (materialType, texture, texture2, specular), "")
    indexList[index].setCustomName(material.name)
    #material.setUserData(b"material",  materialType)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    material.setSpecularTexture(specular)
    #material.setUserData(b"color2  ", texture2)
    #material.setUserData(b"normal2 ", normal2)
    addMaterial(material)

def load0x08002402Chunk(index, name, length):
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    data = []
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
    material = NoeMaterial("24-%s-%s-%s-%s-%s" % (texture, effect, unknown1, unknown2, unknown3), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    #material.setUserData(b'effect  ', effect)
    #material.setUserData(b'unknown1 ', unknown1)
    #material.setUserData(b'unknown2 ', unknown2)
    #material.setUserData(b'unknown3 ', unknown3)
    addMaterial(material)

def load0x08002502Chunk(index, name, length):
    bs.seek(16, NOESEEK_REL)
    unknown1 = loadChunk(bs.readUInt() - 1)
    unknown2 = loadChunk(bs.readUInt() - 1)
    unknown3 = loadChunk(bs.readUInt() - 1)
    unknown4 = loadChunk(bs.readUInt() - 1)
    unknown5 = loadChunk(bs.readUInt() - 1)
    unknown6 = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("25-%s-%s-%s-%s-%s-%s" % (unknown1, unknown2, unknown3, unknown4, unknown5, unknown6), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(unknown1)
    #material.setUserData(b'effect  ', effect)
    #material.setUserData(b'unknown1 ', unknown1)
    #material.setUserData(b'unknown2 ', unknown2)
    #material.setUserData(b'unknown3 ', unknown3)
    addMaterial(material)

def load0x08002802Chunk(index, name, length):
    bs.seek(0x64, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("30-%s" % texture, "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08002902Chunk(index, name, length):
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
    material = NoeMaterial("29-%s" % (texture), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08002A02Chunk(index, name, length):
    material = NoeMaterial("2A-" + name[1:], "")
    indexList[index].setCustomName(material.name)
    addMaterial(material)

def load0x08002B02Chunk(index, name, length):
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
    material = NoeMaterial("2B-%s-%s-%s-%s" % (texture,texture2,texture3,texture4), "")
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
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    interior = loadChunk(bs.readUInt() - 1)
    unknown = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("2C-%s-%s" % (texture,interior), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08002D02Chunk(index, name, length):
    bs.seek(0x30, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    bs.seek(0x48, NOESEEK_REL)
    texture3 = loadChunk(bs.readUInt() - 1)
    texture4 = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("2D-%s-%s-%s-%s" % (texture,texture2,texture3,texture4), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08002E02Chunk(index, name, length):
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("2E-%s" % texture, "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    addMaterial(material)

def load0x08003002Chunk(index, name, length):
    bs.seek(0x8, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("30-%s" % texture, "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    addMaterial(material)

def load0x08003202Chunk(index, name, length):
    bs.seek(0x8, NOESEEK_REL)
    texture1 = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    material = NoeMaterial("32-%s-%s" % (texture1, texture2), "")
    indexList[index].setCustomName(material.name)
    material.setTexture(texture1)
    addMaterial(material)

def load0x08003302Chunk(index, name, length):
    material = NoeMaterial("33-" + name[1:], "")
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
    if indexOf0x1100Chunk != -1:
        return loadChunk(indexOf0x1100Chunk)
    return ''

def load0x1100Chunk(index, name, length):
    bs.seek(12, NOESEEK_REL)
    lengthOfTextureString = bs.readUInt()
    textureString = bs.readBytes(lengthOfTextureString).decode('ASCII').rstrip("\0")
    return textureString

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
        print("0x1000 Chunk Out Of Order!!!! %s %s" % (hex(parent0x0400ID), hex(meshInfos[-1].index)))
        input()

    # if "obj_hair" in meshInfos[-1].name:
    loadChunk(indexOf0x03000A01Chunk)

    loadChunk(indexOf0x03001401Chunk)


def load0x0f00Chunk(index, name, length):
    bs.seek(8, NOESEEK_REL)
    indexOf0x1000Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x1000Chunk)

def load0x14000303Chunk(index, name, length):
    intensity = bs.readFloat()
    R = bs.readFloat()
    G = bs.readFloat()
    B = bs.readFloat()
    return "PL%i-%s-%s-%s-%s" % (index, str(round(intensity, 4)), str(round(R, 4)), str(round(G, 4)), str(round(B, 4)))

def load0x2d00Chunk(index, name, length):
    bs.seek(4, NOESEEK_REL)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1) 
    return "DC%i-%s" % (index, texture)
# def load0x2b00Chunk(index, name, length):

# def load0x3100Chunk(index, name, length):


def loadMeshVertex(vertexCount, vertexStruct):
    vertexs = []
    uvCount = vertexStruct.count(0x9E)
    print("UV Count: %i" % uvCount)
    uvs = [[]]*uvCount
    normals = []
    tangents = []
    for vertex in range(vertexCount):
        uvLoaded = 0
        for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex
                z = bs.readFloat() * global_scale
                y = bs.readFloat() * global_scale
                x = bs.readFloat() * global_scale
                rawTransform = NoeVec3((z, y, x)) * boneInfos[meshInfos[-1].parentID].globalMatrix
                transform = NoeVec3((rawTransform.getStorage()[0], rawTransform.getStorage()[1], rawTransform.getStorage()[2]))
                #transform = NoeVec3((x, y, z))
                vertexs.append(transform)
            elif dataType == 0xA1:  # Unknown, skip
                bs.seek(4, NOESEEK_REL)
            elif dataType == 0x9C:  # Unknown, skip
                bs.seek(4, NOESEEK_REL)
            elif dataType == 0x9E:  # UV
                u = bs.readShort()/1024  
                v = bs.readShort()/1024
                if uvLoaded < 1: #Only load the first UV
                    uvs[uvLoaded].append(NoeVec3((u, v, 0)))
                uvLoaded += 1
                '''
                if u > 1 or u < -1 or v > 1 or v < -1:
                    print("UV out of bound %f %f %i at %s" % (u, v, uvCount, hex(bs.tell()-4)))
                '''
            elif dataType == 0x88:  # Normal
                # normals.append(NoeVec3((bs.readHalfFloat(), bs.readHalfFloat(), bs.readHalfFloat())))
                # bs.seek(2, NOESEEK_REL)
                bs.seek(8, NOESEEK_REL)
            elif dataType == 0x87:  # Tangent
                # tangents.append(NoeVec3((bs.readHalfFloat(), bs.readHalfFloat(), bs.readHalfFloat())))
                # bs.seek(2, NOESEEK_REL)
                bs.seek(8, NOESEEK_REL)
    meshs[-1].setPositions(vertexs)
    meshs[-1].setUVs(uvs[0])
    #meshs[-1].setNormals(normals)
    #meshs[-1].setTangents(tangents)
    '''
    for i in range(uvCount):
        meshs[-1].setUVs(uvs[i], i)
    '''


def loadMeshFace(faceCount):
    print("Reading Face, face count: %i" % faceCount)
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
            print("Error. NoeVertWeight mismatch.")
            print(linkedBone)
            print(weight)
            input()

        linkedBone = [boneMap[x]-1 for x in linkedBone]  # Globlize bone Index
        weightList.append(NoeVertWeight(linkedBone, weight))
    meshs[-1].setWeights(weightList)

def loadReverseBinding(boneMap):
    #print(hex(bs.tell()))
    if reverse_binding:
        for index in boneMap:
            reverse_binding_matrix = NoeMat44.fromBytes(bs.readBytes(64)).inverse().toMat43()
            reverse_binding_matrix[3][0] *= global_scale
            reverse_binding_matrix[3][1] *= global_scale
            reverse_binding_matrix[3][2] *= global_scale
            boneInfos[index-1].setReverseBindingMatrix(reverse_binding_matrix)
    #print(hex(bs.tell()))
            

def printMeshCSV():
    print("Mesh CSV List ----------------------------------------")
    print("Name|Index|Vertex Count|Submesh Count|Face Count|Texture|Type Of Material|Vertex Struct|Index Of 0x0500Chunk|Index Of 0x0600Chunk|Index Of 0x0800Chunk")
    for meshInfo in meshInfos:
        print(meshInfo.name, hex(meshInfo.index), meshInfo.vertexCount, meshInfo.numOfFaceChunk, meshInfo.faceCount, meshInfo.texture, [typeOf0x0800Chunk(x) for x in meshInfo.indexOf0x0800Chunk], [hex(x) for x in meshInfo.vertexStruct], hex(meshInfo.indexOf0x0500Chunk), [hex(x) for x in meshInfo.indexOf0x0600Chunk], [hex(x) for x in meshInfo.indexOf0x0800Chunk], sep="|")
    print("End of Mesh CSV List ----------------------------------------")

def typeOf0x0800Chunk(index):
    origonalOffset = bs.tell()
    bs.seek(index*0x10 + 0x36, NOESEEK_ABS)
    chunkType = hex(bs.readUShort()+ 0x10000)
    bs.seek(origonalOffset, NOESEEK_ABS)
    return chunkType[5:]+chunkType[3:5]

def cleanUpMesh():
    for i in range(0, len(meshs)):
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
        for x in range(0, len(meshs[i].positions)):
            if vertice_used[x]:
                new_vertice.append(meshs[i].positions[x])
        meshs[i].setPositions(new_vertice)

        #generate new uv list 
        new_uv = []
        for x in range(0, len(meshs[i].uvs)):
            if vertice_used[x]:
                new_uv.append(meshs[i].uvs[x])
        meshs[i].setUVs(new_uv)

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

                
    
