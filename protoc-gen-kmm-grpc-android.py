#!/usr/bin/env python3

from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    ServiceDescriptorProto, MethodDescriptorProto

from generator import Generator

class KMMGrpcAndroidGenerator(Generator):
    def __init__(self):
        super().__init__(baseName="kmm-grpc-android")
    
    def getOutputFileName(self, protoFileName: str, packageName: str) -> str:
        return self.typeNameCase(packageName) + "AndroidGrpcClient.kt"

    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        return []

    def processMessage(self, msg: DescriptorProto,
                       indentationLevel: int) -> list[str]:
        return []

    def getHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        pkg = self.options["java_package"]
        importFlow = "import kotlinx.coroutines.flow."
        lines = [
            "package " + pkg,
            "",
            importFlow + "Flow",
            importFlow + "map",
        ]
        for service in protoFile.service:
            # Not sure if service.name is the whole story, but it should be
            # an easy fix if not.
            lines.append("import %s.%sGrpcKt.%sCoroutineStub" % \
                    (pkg, service.name, service.name))
        return lines + [""]
    
    def getFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        return [""]
    
    def getTopLevelIndentation(self, protoFile: FileDescriptorProto) -> int:
        return 0

    def getServiceHeader(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        serviceName = self.getServiceName(protoFile, serv)
        indent = "    " * indentationLevel
        return [
            indent + "class %sAndroidGrpcClient (" % serviceName,
            indent + "    val stub: %sCoroutineStub" % serv.name,
            indent + "): %sGrpcClient {" % serviceName,
        ]

    def getServiceFooter(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        return ["}"]

    def getServiceMethod(self, protoFile: FileDescriptorProto,
                        serv: ServiceDescriptorProto,
                        method: MethodDescriptorProto,
                        indentationLevel: int) -> list[str]:
        indentationLevel += 1
        lines = self.getMethodSignature(protoFile,
                                        serv,
                                        method,
                                        indentationLevel)
        indent = "    " * indentationLevel
        lines[0] = indent + "override " + lines[0][4:]
        lines[-1] += " ="
        methodName = self.memberCase(method.name)
        if method.client_streaming:
            input = "map { it.toProto() }"
        else:
            input = "toProto()"
        if method.server_streaming:
            output = "map { it.toData() }"
        else:
            output = "toData()"
        lines.extend([
            indent + "    stub.%s(request.%s).%s" % \
                (methodName, input, output),
            ""
        ])
        return lines


def main():
    generator = KMMGrpcAndroidGenerator()
    generator.runOnStdinAndStdout()

if __name__ == "__main__":
    main()
