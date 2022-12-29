#!/usr/bin/env python3

from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    ServiceDescriptorProto, MethodDescriptorProto

from generator import Generator

class KMMGrpcSharedGenerator(Generator):
    def __init__(self):
        super().__init__(baseName="kmm-grpc-shared")
    
    def getOutputFileName(self, protoFileName: str, packageName: str) -> str:
        return self.typeNameCase(packageName) + "GrpcClient.kt"

    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        return []

    def processMessage(self, msg: DescriptorProto,
                       indentationLevel: int) -> list[str]:
        return []

    def getHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        return [
            "package " + self.options["java_package"],
            ""
        ]
    
    def getFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        return [""]
    
    def getTopLevelIndentation(self, protoFile: FileDescriptorProto) -> int:
        return 1

    def getServiceHeader(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        serviceName = self.getServiceName(protoFile, serv)
        return [
            "class %sGrpcClient {" % serviceName
        ]

    def getServiceFooter(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        return ["}"]

    def getServiceMethod(self, protoFile: FileDescriptorProto,
                        serv: ServiceDescriptorProto,
                        method: MethodDescriptorProto,
                        indentationLevel: int) -> list[str]:
        return self.getMethodSignature(protoFile,
                                        serv,
                                        method,
                                        indentationLevel) + [""]


def main():
    generator = KMMGrpcSharedGenerator()
    generator.runOnStdinAndStdout()

if __name__ == "__main__":
    main()
