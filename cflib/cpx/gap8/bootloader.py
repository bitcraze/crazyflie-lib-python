# from cflib.cpx import CPXTarget, CPXFunction

class GAP8Bootloader:

    # target = CPXTarget.GAP8
    # function = CPXFunction.BOOTLOADER

    def __init__(self):
        print('GAP8 bootloader module init')

    # def getVersion(self):
    #   version = self._cpx.transaction(CPXPacket(destination=CPXTarget.GAP8,
    #                                             function=CPXFunction.BOOTLOADER,
    #                                             data=bytearray([0x00])))
    #   return version.data[1:]

    # def readFlash(self, start, count):
    #   cmd = struct.pack("<BII", 0x03, start, count)
    #   readPacket = CPXPacket(destination=CPXTarget.GAP8, function=CPXFunction.BOOTLOADER, data=cmd)

    #   self._cpx.send(readPacket)
    #   totalBytesRead = 0
    #   totalRead = bytearray()
    #   while (totalBytesRead < size):
    #     readAnswer = self._cpx.receive()
    #     totalRead.extend(readAnswer.data)
    #     totalBytesRead += readAnswer.length
    #   return totalRead

    # def MD5Flash(self, start, count):
    #   md5 = self._cpx.transaction(CPXPacket(destination=CPXTarget.GAP8,
    #                                         function=CPXFunction.BOOTLOADER,
    #                                         data=struct.pack("<BII", 0x04, start, count)))
    #   return md5.data[1:]

    # def startApplication(self):
    #   self._cpx.send(CPXPacket(destination=CPXTarget.GAP8,
    #                           function=CPXFunction.BOOTLOADER,
    #                           data=struct.pack("<B", 0x06)))

    # def writeFlash(self, start, data):
    #   cmd = struct.pack("<BII", 0x02, start, len(data))
    #   cmdPacket = CPXPacket(destination=CPXTarget.GAP8, function=CPXFunction.BOOTLOADER, data=cmd)

    #   self._cpx.send(cmdPacket)

    #   totalBytesWritten = 0
    #   maxChunkSize = 512
    #   while (totalBytesWritten < len(data)):
    #     nextChunk = min(maxChunkSize, len(data) - totalBytesWritten)
    #     print("We're at {}, next chunk is {} bytes".format(totalBytesWritten, nextChunk))
    #     fwWritePacket = CPXPacket(destination=CPXTarget.GAP8,
    #                               function=CPXFunction.BOOTLOADER,
    #                               data=data[totalBytesWritten:totalBytesWritten+nextChunk])
    #     self._cpx.send(fwWritePacket)
    #     totalBytesWritten += nextChunk
