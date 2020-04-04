# Noesis Gravity Rush 2 GFX Extractor V2
# Written by 203Null
# Reverse Engineered by 203Null and FreezeCook
# Strcture Note: https://docs.google.com/document/d/1eW8BNMuE6chZebgClRnRoxRCEMDCAKPadYEhpK4AIV0/edit?usp=sharing

from inc_noesis import *
import noesis
import rapi
import os
import copy

debug = True  # please change to False out when done.
print_CSV = False
seperate_sub_mesh = True
global_scale = 100
remove_loose_vertice = True


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


class MeshInfo:
    # Infomations from 0x0400 Chunk
    def __init__(self, index, name, numOfFaceChunk, parrentID, indexOf0x0500Chunk, indexOf0x0600Chunk):
        self.index = index  # Global Index
        self.name = name
        self.numOfFaceChunk = numOfFaceChunk
        self.parentID = parrentID
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
    global modelNameHash
    modelNameHash = getNameFromHash(bs.readUInt())
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

    global child0x0f00ChunkList
    child0x0f00ChunkList = []
    '''
    global indexOf0x2b00Chunk
    indexOf0x2b00Chunk = -1
    '''
    global numOfBone
    numOfBone = 0
    global numOfMesh
    numOfMesh = 0
    global currentMesh
    currentMesh = 0

    for i in range(numDataInIndexChunk):
        indexList.append(IndexChunk(getNameFromHash(
            bs.readUInt()), bs.readUInt(), bs.readUInt(), bs.readUInt()))
        if indexList[i].typeID % 0x10000 == 0x0002:
            numOfBone += 1
            if indexList[i].typeID == 0x010b0002:  # root
                rootBoneIndex = i
        if indexList[i].typeID == 0x00000004:
            numOfMesh += 1
        elif indexList[i].typeID == 0x0000000f:
            child0x0f00ChunkList.append(i)  # Assume this is linear
        elif indexList[i].typeID == 0x0000002b:
            indexOf0x2b00Chunk = i

    global bones
    bones = [None] * numOfBone

    # Load root 0x0200 Chunk
    loadChunk(rootBoneIndex)

    if remove_loose_vertice:
        cleanUpMesh()

    model = NoeModel(meshs)
    model.setBones(bones)
    mdlList.append(model)

    if print_CSV:
      printMeshCSV()

    return 1


def loadChunk(index):
    origonalOffset = bs.tell()
    result = None
    bs.seek(indexList[index].offsetFromDataChunk + pointerOfDataChunk, NOESEEK_ABS)
    if indexList[index].typeID % 0x10000 == 0x0002:
        print()
        print("Load Chunk 0x0200xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0200Chunk(
            index, indexList[index].name, indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0003:
        print("Load Chunk 0x0300xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0300Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0004:
        print("Load Chunk 0x0400xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0400Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0005:
        print("Load Chunk 0x0500xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0500Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0006:
        print("Load Chunk 0x0600xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0600Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID == 0x02220008:
        print("Load Chunk 0x08002202 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x08002202Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID == 0x02230008:
        print("Load Chunk 0x08002302 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x08002302Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID == 0x02240008:
        print("Load Chunk 0x08002402 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x08002402Chunk(index, indexList[index].name,  indexList[index].length)      
    elif indexList[index].typeID == 0x02330008:
        print("Load Chunk 0x08003302 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x08003302Chunk(index, indexList[index].name,  indexList[index].length)                
    elif indexList[index].typeID % 0x10000 == 0x0009:
        print("Load Chunk 0x0900xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0900Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0011:
        print("Load Chunk 0x1100xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x1100Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x000f:
        print("Load Chunk 0x0f00xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x0f00Chunk(
            index, indexList[index].name,  indexList[index].length)
    elif indexList[index].typeID % 0x10000 == 0x0010:
        print("Load Chunk 0x1000xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
        result = load0x1000Chunk(
            index, indexList[index].name,  indexList[index].length)
    else:
        print("Unknown Chunk, skipped %s" % hex(indexList[index].typeID))
    bs.seek(origonalOffset, NOESEEK_ABS)
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
    isBone = bs.readUShort()

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
        '''
      print("Rotation: %f %f %f %f" % (rotation[0],rotation[1],rotation[2],rotation[3]))
      print("%f \t %f \t %f" % (bones[index].getMatrix()[0][0],bones[index].getMatrix()[0][1],bones[index].getMatrix()[0][2]))
      print("%f \t %f \t %f" % (bones[index].getMatrix()[1][0],bones[index].getMatrix()[1][1],bones[index].getMatrix()[1][2]))
      print("%f \t %f \t %f" % (bones[index].getMatrix()[2][0],bones[index].getMatrix()[2][1],bones[index].getMatrix()[2][2]))
      print("%f \t %f \t %f" % (bones[index].getMatrix()[3][0],bones[index].getMatrix()[3][1],bones[index].getMatrix()[3][2]))
      '''

    if parentID != -1:
        print("Globalizing Bone %i x %i " % (index, parentID))
        boneMatrix *= bones[parentID].getMatrix()  # Globalization

    bones[index] = NoeBone(index, boneName, boneMatrix, None, parentID)

    for childIndex in childList:
        loadChunk(childIndex)

    return


def load0x0300Chunk(index, name, length):  # Mesh Data Pointer
    bs.seek(4, NOESEEK_REL)
    typeID = bs.readUInt()
    offsetFromMeshChunk = bs.readUInt()
    length = bs.readUInt()
    bs.seek(offsetFromMeshChunk + pointerOfMeshChunk, NOESEEK_ABS)
    if typeID == 0x01010000:  # VertexData
        print("Loading Mesh Vertex - Index: %s - Name: %s - Address: %s" %
              (len(meshInfos), name, hex(bs.tell())))
        loadMeshVertex(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    elif typeID == 0x01020000:  # FaceData
        print("Loading Mesh Face - Index: %s - Name: %s - Address: %s" %
              (len(meshInfos), name, hex(bs.tell())))
        loadMeshFace(meshInfos[-1].faceCount[-1])
    elif typeID == 0x01140000:  # WeightData
        loadMeshWeight(meshInfos[-1].vertexCount, meshInfos[-1].boneMap)

def load0x0400Chunk(index, name, length):  # Mesh Info
    global currentMesh
    # Header
    numOfFaceChunk = bs.readUShort()
    bs.seek(6, NOESEEK_REL)
    parrentID = bs.readUInt() - 1
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
    print("Mesh detected - Name: %s Mesh Index: %i Global Index: %i Submesh count: %i" % (name, currentMesh, index, numOfFaceChunk))
    print("Index Of 0x0500 Chunk: %s" % hex(indexOf0x0500Chunk))
    print("Index Of 0x0600 Chunk: ", end='')
    print([hex(x) for x in indexOf0x0600Chunk])
    meshs.append(NoeMesh([], [], name))
    meshInfos.append(MeshInfo(index, name, numOfFaceChunk, parrentID, indexOf0x0500Chunk, indexOf0x0600Chunk[i]))

    loadChunk(indexOf0x0500Chunk)  # Load Vertex Chain

    if len(child0x0f00ChunkList) > 0:
        loadChunk(child0x0f00ChunkList[currentMesh])

    if seperate_sub_mesh:
        meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
        loadChunk(indexOf0x0600Chunk[0]) #Load First Chain
        if numOfFaceChunk > 1:
            meshs[-1].setName(name + "_0")
            meshInfos[-1].setName(meshs[-1].name)

            for i in range(1, numOfFaceChunk):  #Load Face Chain
                meshs.append(copy.deepcopy(meshs[-1]))
                meshs[-1].setName(name + '_' + str(i))
                meshs[-1].setIndices([])
                meshInfos.append(copy.deepcopy(meshInfos[-1]))
                meshInfos[-1].initialize0x0600ChunkInfo()
                meshInfos[-1].setIndexOf0x0600Chunk([indexOf0x0600Chunk[0]])
                meshInfos[-1].setName(meshs[-1].name)
                print("Loading sub mesh %s" % meshs[-1].name)
                loadChunk(indexOf0x0600Chunk[i])
    else:
        meshInfos.append(MeshInfo(index, name, numOfFaceChunk, parrentID, indexOf0x0500Chunk, indexOf0x0600Chunk))
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
    indexOf0x08002202Chunk = bs.readUInt() - 1
    indexOf0x03000201Chunk = bs.readUInt() - 1
    faceCount = bs.readUShort()
    # Just gonna ignore those unknown data in between rn
    bs.seek(12, NOESEEK_REL)
    faceIndex = bs.readUShort()
    meshInfos[-1].loadFaceInfo(indexOf0x08002202Chunk,indexOf0x03000201Chunk, faceCount, faceIndex)

    # Load material
    loadChunk(indexOf0x08002202Chunk)

    loadChunk(indexOf0x03000201Chunk)


def load0x08002202Chunk(index, name, length):
    bs.seek(4, NOESEEK_REL)
    # We only load 1, the main texture for now
    indexOf0x0900Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x0900Chunk)

def load0x08002302Chunk(index, name, length):
    bs.seek(12, NOESEEK_REL)
    # We only load 1, the main texture for now
    indexOf0x0900Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x0900Chunk)

def load0x08002402Chunk(index, name, length):
    bs.seek(144, NOESEEK_REL)
    # We only load 1, the main texture for now
    indexOf0x0900Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x0900Chunk)

def load0x08003302Chunk(index, name, length):
    bs.seek(12, NOESEEK_REL)
    # We only load 1, the main texture for now
    indexOf0x0900Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x0900Chunk)


def load0x0900Chunk(index, name, length):
    indexOf0x1100Chunk = bs.readUInt() - 1
    if indexOf0x1100Chunk != 0:
        loadChunk(indexOf0x1100Chunk)


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

    # I don't know what 0x03001401 does for now, let just load 0x3001401

    loadChunk(indexOf0x03001401Chunk)


def load0x1100Chunk(index, name, length):
    bs.seek(12, NOESEEK_REL)
    lengthOfTextureString = bs.readUInt()
    textureString = bs.readBytes(
        lengthOfTextureString).decode('ASCII').rstrip("\0")
    print("Texture loaded: %s" % textureString)
    if meshs[-1].matName == "default" or seperate_sub_mesh:
        meshs[-1].setMaterial(textureString)
    elif (textureString in meshs[-1].matName) == False:
        meshs[-1].setMaterial(meshs[-1].matName + " + " + textureString)
    meshInfos[-1].loadTexture(textureString)


def load0x0f00Chunk(index, name, length):
    bs.seek(8, NOESEEK_REL)
    indexOf0x1000Chunk = bs.readUInt() - 1
    loadChunk(indexOf0x1000Chunk)

# def load0x2b00Chunk(index, name, length):

# def load0x3100Chunk(index, name, length):


def loadMeshVertex(vertexCount, vertexStruct):
    vertexs = []
    uvCount = vertexStruct.count(0x9E)
    print("UV Count: %i" % uvCount)
    uvs = [[]]*uvCount
    for vertex in range(vertexCount):
        uvLoaded = 0
        for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex
                z = bs.readFloat() * global_scale
                y = bs.readFloat() * global_scale
                x = bs.readFloat() * global_scale
                vertexs.append(NoeVec3((z, y, x)))
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
            elif dataType == 0x88:  # Unknown, skip
                bs.seek(8, NOESEEK_REL)
            elif dataType == 0x87:  # Unknown, skip
                bs.seek(8, NOESEEK_REL)
    meshs[-1].setPositions(vertexs)
    meshs[-1].setUVs(uvs[0])
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

def printMeshCSV():
  print("Mesh CSV List ----------------------------------------")
  print("Name\tIndex\tVertex Count\tSubmesh Count\tFace Count\tTexture\tType Of Material\tVertex Struct\tIndex Of 0x0500Chunk\tIndex Of 0x0600Chunk\tIndex Of 0x0800Chunk")
  for meshInfo in meshInfos:
    print(meshInfo.name, hex(meshInfo.index), meshInfo.vertexCount, meshInfo.numOfFaceChunk, meshInfo.faceCount, meshInfo.texture, [typeOf0x0800Chunk(x) for x in meshInfo.indexOf0x0800Chunk], [hex(x) for x in meshInfo.vertexStruct], hex(meshInfo.indexOf0x0500Chunk), [hex(x) for x in meshInfo.indexOf0x0600Chunk], [hex(x) for x in meshInfo.indexOf0x0800Chunk], sep="\t")
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


                
    