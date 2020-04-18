# Noesis Gravity Rush 2 GFX Extractor V2
# Written by 203Null
# Reverse Engineered by 203Null and FreezeCook
# Strcture Note: https://docs.google.com/document/d/1eW8BNMuE6chZebgClRnRoxRCEMDCAKPadYEhpK4AIV0/edit?usp=sharing

#THIS VERSION IS NOT WORKING. JUST LEAVE HERE FOR ARCHIVE

from inc_noesis import *
import noesis
import rapi
import os
import copy

debug = True # please change to False out when done.
global_scale = 100
mergeLOD = True

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
    ctx = rapi.rpgCreateContext()
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
    global textureList
    textureList = []
    global materialList
    materialList = []

    global LOD
    LOD = False
    global currentVertexOffset
    currentVertexOffset = 0

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

    materialIndexs = []

    for i in range(numDataInIndexChunk):
        indexList.append(IndexChunk(getNameFromHash(bs.readUInt()), bs.readUInt(), bs.readUInt(), bs.readUInt()))
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
        if indexList[i].typeID % 0x10000 == 0x0008:
            materialIndexs.append(i)

    global bones
    bones = [None] * numOfBone

    for materialIndex in materialIndexs:
        loadChunk(materialIndex)

    # Load root 0x0200 Chunk
    loadChunk(rootBoneIndex)

    model = rapi.rpgConstructModel()
    model.setModelMaterials(NoeModelMaterials(textureList, materialList))
    model.setBones(bones)
    mdlList.append(model)
    rapi.rpgClearBufferBinds() 
    return 1


def loadChunk(index):
    origonalOffset = bs.tell()
    result = None
    print("Loading Chunk index %i :" % index)
    if index > -1:
        bs.seek(indexList[index].offsetFromDataChunk + pointerOfDataChunk, NOESEEK_ABS)
        if indexList[index].typeID % 0x10000 == 0x0002:
            print()
            print("Chunk 0x0200xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0200Chunk(
                index, indexList[index].name, indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0003:
            print("Chunk 0x0300xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0300Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0004:
            print("Chunk 0x0400xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0400Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0005:
            print("Chunk 0x0500xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0500Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0006:
            print("Chunk 0x0600xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0600Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02010008:
            print("Chunk 0x08000102 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08000102Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02200008:
            print("Chunk 0x08002002 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002002Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02220008:
            print("Chunk 0x08002202 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002202Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02230008:
            print("Chunk 0x08002302 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002302Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID == 0x02240008:
            print("Chunk 0x08002402 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002402Chunk(index, indexList[index].name,  indexList[index].length)      
        elif indexList[index].typeID == 0x02290008:
            print("Chunk 0x08002902 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002902Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022B0008:
            print("Chunk 0x08002B02 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002B02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x022C0008:
            print("Chunk 0x08002C02 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08002C02Chunk(index, indexList[index].name,  indexList[index].length)    
        elif indexList[index].typeID == 0x02330008:
            print("Chunk 0x08003302 - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x08003302Chunk(index, indexList[index].name,  indexList[index].length)              
        elif indexList[index].typeID % 0x10000 == 0x0009:
            print("Chunk 0x0900xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0900Chunk(index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0011:
            print("Chunk 0x1100xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x1100Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x000f:
            print("Chunk 0x0f00xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x0f00Chunk(
                index, indexList[index].name,  indexList[index].length)
        elif indexList[index].typeID % 0x10000 == 0x0010:
            print("Chunk 0x1000xxxx - Index: %s - Name: %s - Address: %s - Length: %s" % (hex(index), indexList[index].name, hex(indexList[index].offsetFromDataChunk + pointerOfDataChunk), hex(indexList[index].length)))
            result = load0x1000Chunk(
                index, indexList[index].name,  indexList[index].length)
        bs.seek(origonalOffset, NOESEEK_ABS)
    return result


def load0x0200Chunk(index, name, length):  # Object/Bone tree
    # Load Translation
    z = bs.readFloat() * global_scale #I don't really know what each of them repensent
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

    global

    if mergeLOD:
        if name == "low":
            LOD = True
            rapi.rpgSetName(modelName + "_LOD2")
        elif name == "middle":
            LOD = True
            rapi.rpgSetName(modelName + "_LOD1")
        elif name == "near":
            LOD = True
            rapi.rpgSetName(modelName + "_LOD0")


    for childIndex in childList:
        loadChunk(childIndex)
    
    LOD = False
    currentVertexOffset = 0l

    return


def load0x0300Chunk(index, name, length):  # Mesh Data Pointer
    bs.seek(4, NOESEEK_REL)
    typeID = bs.readUInt()
    offsetFromMeshChunk = bs.readUInt()
    length = bs.readUInt()
    bs.seek(offsetFromMeshChunk + pointerOfMeshChunk, NOESEEK_ABS)
    if typeID == 0x01010000:  # VertexData
        loadMeshVertex(meshInfos[-1].vertexCount, meshInfos[-1].vertexStruct)
    elif typeID == 0x01020000:  # FaceData
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
    if LOD == False:
        rapi.rpgSetName(name)
    meshInfos.append(MeshInfo(index, name, numOfFaceChunk, parrentID, indexOf0x0500Chunk, indexOf0x0600Chunk[i]))

    loadChunk(indexOf0x0500Chunk)  # Load Vertex Chain

    if len(child0x0f00ChunkList) > 0:
        loadChunk(child0x0f00ChunkList[currentMesh])

    for i in range(numOfFaceChunk):  #Load Face Chain
        if i > 0:
            meshInfos.append(copy.deepcopy(meshInfos[-1]))
        meshInfos[-1].initialize0x0600ChunkInfo()
        meshInfos[-1].setIndexOf0x0600Chunk(indexOf0x0600Chunk[i])
        loadChunk(indexOf0x0600Chunk[i])
    
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
    #loadChunk(indexOf0x08002202Chunk)
    rapi.rpgSetMaterial(indexList[indexOf0x08002202Chunk].name[1:])

    loadChunk(indexOf0x03000201Chunk)

def load0x08000102Chunk(index, name, length):
    material = NoeMaterial("01|"+name[1:], "")
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
    materialList.append(material)

def load0x08002002Chunk(index, name, length):
    material = NoeMaterial("20|"+name[1:], "")
    materialList.append(material)

def load0x08002202Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    header = bs.readUInt()
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    eye_refelection = loadChunk(bs.readUInt() - 1)
    detail = loadChunk(bs.readUInt() - 1)
    eye = loadChunk(bs.readUInt() - 1)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    #material.setUserData("eye refl", eye_refelection)
    #material.setUserData("detail  ", detail)
    #material.setUserData("eye     ", eye)
    material.name = "22|%s|%s|%s|%s" % (texture, eye_refelection, detail, eye)
    materialList.append(material)

def load0x08002302Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    materialType = getNameFromHash(bs.readUInt())
    material.setUserData("material",  materialType)
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    specular = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    normal2 = loadChunk(bs.readUInt() - 1)
    material.setTexture(texture)
    material.setNormalTexture(normal)
    material.setSpecularTexture(specular)
    #material.setUserData("color2  ", texture2)
    #material.setUserData("normal2 ", normal2)
    material.name = "23|%s|%s|%s|%s" % (materialType, texture, texture2, specular)
    materialList.append(material)

def load0x08002402Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    data = []
    data.append("Data Chunk 1")
    for i in range(17):
        data.append(bs.readFloat())
    material.setUserData("effect  ", loadChunk(bs.readUInt() - 1))
    data.append("Data Chunk 2")
    for i in range(16):
        data.append(bs.readFloat())
    material.setTexture(loadChunk(bs.readUInt() - 1))
    material.setUserData("unknown1 ", loadChunk(bs.readUInt() - 1))
    material.setUserData("unknown2 ", loadChunk(bs.readUInt() - 1))
    material.setUserData("unknown3 ", loadChunk(bs.readUInt() - 1))
    data.append("Data Chunk 3")
    for i in range(16):
        data.append(bs.readFloat())
    
    materialList.append(material)

def load0x08002902Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    data = []
    data.append("Data Chunk 1")
    for i in range(7):
        data.append(bs.readFloat())
    subchunkID = []
    texture = loadChunk(bs.readUInt() - 1)
    material.setTexture(texture)
    data.append("Data Chunk 2")
    for i in range(12):
        data.append(bs.readFloat())
    normal = loadChunk(bs.readUInt() - 1)
    material.setNormalTexture(normal)
    data.append("Data Chunk 3")
    for i in range(3):
        data.append(bs.readFloat())
    material.name = "29|%s" % texture
    materialList.append(material)

def load0x08002B02Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    header1 = bs.readUInt()
    header2 = bs.readUInt()
    texture = loadChunk(bs.readUInt() - 1)
    texture2 = loadChunk(bs.readUInt() - 1)
    texture3 = loadChunk(bs.readUInt() - 1)
    texture4 = loadChunk(bs.readUInt() - 1)
    material.setTexture(texture)
    #material.setUserData("color2  ", texture2)
    #material.setUserData("color3  ", texture3)
    #material.setUserData("color4  ", texture4)
    normal = loadChunk(bs.readUInt() - 1)
    normal2 = loadChunk(bs.readUInt() - 1)
    normal3 = loadChunk(bs.readUInt() - 1)
    normal4 = loadChunk(bs.readUInt() - 1)
    material.setNormalTexture(loadChunk(bs.readUInt() - 1))
    #material.setUserData("normal2 ", loadChunk(bs.readUInt() - 1))
    #material.setUserData("normal3 ", loadChunk(bs.readUInt() - 1))
    #material.setUserData("normal4 ", loadChunk(bs.readUInt() - 1))
    material.name = "2B|%s|%s|%s|%s" % (texture,texture2,texture3,texture4)
    materialList.append(material)

def load0x08002C02Chunk(index, name, length):
    texture = loadChunk(bs.readUInt() - 1)
    normal = loadChunk(bs.readUInt() - 1)
    interior = loadChunk(bs.readUInt() - 1)
    unknown = loadChunk(bs.readUInt() - 1)
    material.setTexture(texture)
    material.name = "2C|%s|%s" % (texture,interior)
    materialList.append(material)


def load0x08003302Chunk(index, name, length):
    material = NoeMaterial(name[1:], "")
    '''
        header1 = bs.readUInt()
    subchunkID = []
    for i in range(4):
        subchunkID.append(bs.readUInt() - 1)
    data = []
    for i in range(7):
        data.append(bs.readFloat())
    '''
    materialList.append(material)

def load0x0900Chunk(index, name, length):
    indexOf0x1100Chunk = bs.readUInt() - 1
    if indexOf0x1100Chunk != 0:
        return loadChunk(indexOf0x1100Chunk)
    return ""


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
    textureString = bs.readBytes(lengthOfTextureString).decode('ASCII').rstrip("\0")
    return textureString

def load0x3400Chunk(index, name, length):
    return None


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

    structLength = 0
    for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex
                structLength += 8
            elif dataType == 0xA1:  # Unknown, skip
                structLength += 4
            elif dataType == 0x9C:  # Unknown, skip
                structLength += 4
            elif dataType == 0x9E:  # UV
                structLength += 4
            elif dataType == 0x88:  # Unknown, skip
                structLength += 8
            elif dataType == 0x87:  # Unknown, skip
                structLength += 8

        for dataType in vertexStruct:
            if dataType == 0x83:  # Vertex
                z = bs.readFloat() * global_scale
                y = bs.readFloat() * global_scale
                x = bs.readFloat() * global_scale
                rapi.rpgBindPositionBufferOfs(noePack("<fff", z, y, x), noesis.RPGEODATA_FLOAT, 12)
                
            elif dataType == 0xA1:  # Unknown, skip
                bs.seek(4, NOESEEK_REL)
            elif dataType == 0x9C:  # Unknown, skip
                bs.seek(4, NOESEEK_REL)
            elif dataType == 0x9E:  # UV
                u = bs.readShort()/1024  
                v = bs.readShort()/1024
                rapi.rpgBindUVXBuffer(noePack("<ff", u, v), noesis.RPGEODATA_FLOAT, 8, uvLoaded, 2)
                uvLoaded += 1
            elif dataType == 0x88:  # Unknown, skip
                bs.seek(8, NOESEEK_REL)
            elif dataType == 0x87:  # Unknown, skip
                bs.seek(8, NOESEEK_REL)


def loadMeshFace(faceCount):
    print("Reading Face, face count: %i" % faceCount)
    for face in range(faceCount):
        rapi.rpgCommitTriangles(bs.readBytes(6), noesis.RPGEODATA_USHORT, 3, noesis.RPGEO_TRIANGLE, 1)



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
        rapi.rpgBindBoneIndexBuffer(linkedBone, noesis.RPGEODATA_INT, 4 * len(linkedBone), len(linkedBone))
        rapi.rpgBindBoneWeightBuffer(weight, noesis.RPGEODATA_FLOA, 4 * len(linkedBone), len(linkedBone))

def typeOf0x0800Chunk(index):
    origonalOffset = bs.tell()
    bs.seek(index*0x10 + 0x36, NOESEEK_ABS)
    chunkType = hex(bs.readUShort()+ 0x10000)
    bs.seek(origonalOffset, NOESEEK_ABS)
    return chunkType[5:]+chunkType[3:5]
