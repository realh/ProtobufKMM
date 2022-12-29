#!/usr/bin/env python3

from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    FieldDescriptorProto

from generator import Generator

class ToJVMGenerator(Generator):
    ''' A helper class which makes it possible for the main generator to make
        two passes on each message using the super processMessage(); this
        handles the pass for converting the KMM data classes to their JVM
        implementations, using extensions on the data classes. '''
    def __init__(self, namespace: str, options: dict[str, str]):
        super().__init__(baseName="kmm-jvm-conv")
        self.namespace = namespace
        self.options = options
    
    def messageOpening(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        typeName = self.typeNameCase(name)
        camelName = self.memberCase(name)   # DSL builder
        return [
            "fun %s.%s.toProto(): %s {" % \
                    (self.namespace, typeName, typeName),
            "    val data = this",
            "    return %s {" % camelName,
        ]
    
    def messageClosing(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        return ["    }", "}"]

    def processField(self, msg: DescriptorProto,
                     field: FieldDescriptorProto,
                     indentationLevel: int) -> list[str]:
        fieldName = self.memberCase(field.name)
        typeName = self.getTypeName(field.type, field.type_name)
        builtIn = self.typeIsBuiltIn(field.type, field.type_name)
        isList = field.label == FieldDescriptorProto.LABEL_REPEATED
        if isList and not builtIn:
            conv = ".map { it.toProto() }"
        elif builtIn:
            conv = ""
        else:
            conv = ".toProto()"
        if isList:
            return ["        this.%s += data.%s%s" % \
                (fieldName, fieldName, conv)]
        elif not isList and typeName.endswith("?"):
            return ["        data.%s?.let { this.%s = it%s }" % \
                (fieldName, fieldName, conv)]
        else:
            return ["        this.%s = data.%s%s" % \
                (fieldName, fieldName, conv)]


class FromJVMGenerator(Generator):
    ''' A helper class which makes it possible for the main generator to make
        two passes on each message using the super processMessage(); this
        handles the pass for adding extensions to the JVM message classes to
        convert them to their KMM data counterparts. '''
    def __init__(self, namespace: str, options: dict[str, str]):
        super().__init__(baseName="kmm-jvm-conv")
        self.namespace = namespace
        self.options = options
    
    def messageOpening(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        typeName = self.typeNameCase(name)
        return [
            "fun %s.toData(): %s.%s {" % (typeName, self.namespace, typeName),
            "    val proto = this",
            "    return %s.%s(" % (self.namespace, typeName)
        ]
    
    def messageClosing(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        return ["    )", "}"]

    def processField(self, msg: DescriptorProto,
                     field: FieldDescriptorProto,
                     indentationLevel: int) -> list[str]:
        fieldName = self.memberCase(field.name)
        typeName = self.getTypeName(field.type, field.type_name)
        if typeName.endswith("?"):
            typeName = typeName[:-1]
            optional = "OrNull?"
        else:
            optional = ""
        builtIn = self.typeIsBuiltIn(field.type, field.type_name)
        isList = field.label == FieldDescriptorProto.LABEL_REPEATED
        if isList and not builtIn:
            expr = "proto.%sList.map { it.toData() }" % fieldName
        elif isList and builtIn:
            expr = "proto.%sList" % fieldName
        elif builtIn:
            expr = "proto.%s" % fieldName
        else:
            expr = "proto.%s%s.toData()" % (fieldName, optional)
        return ["        %s = %s," % (fieldName, expr)]


class JvmConvGenerator(Generator):
    def __init__(self):
        super().__init__(baseName="kmm-jvm-conv")
    
    def getOutputFileName(self, protoFileName: str, packageName: str) -> str:
        return self.typeNameCase(packageName) + "Converters.kt"

    def getContent(self, protoFile: FileDescriptorProto) -> str:
        # toJvm and fromJvm need to be initialised with data read from
        # protoFile, and this is a handy place to do it.
        self.namespace = self.getNamespace(protoFile)
        self.toJvm = ToJVMGenerator(self.namespace, self.options)
        self.fromJvm = FromJVMGenerator(self.namespace, self.options)
        return super().getContent(protoFile)

    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        typeName = self.typeNameCase(enum.name)
        lines = [
            "fun %s.toData(): %s.%s {" % (typeName, self.namespace, typeName),
            "    return %s.%s from number" % (self.namespace, typeName),
            "}",
            "",
            "fun %s.%s.toProto(): %s {" % \
                    (self.namespace, typeName, typeName),
            "    return %s.forNumber(this.value)" % typeName,
            "}"
        ]
        return lines

    def processMessage(self, msg: DescriptorProto,
                       indentationLevel: int) -> list[str]:
        return self.fromJvm.processMessage(msg, indentationLevel) + [""] + \
            self.toJvm.processMessage(msg, indentationLevel)

    def getHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        return [
            "package " + self.options["java_package"],
            "",
        ]
    
    def getFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        return []
    
    def getTopLevelIndentation(self, protoFile: FileDescriptorProto) -> int:
        return 1


def main():
    generator = JvmConvGenerator()
    generator.runOnStdinAndStdout()

if __name__ == "__main__":
    main()
