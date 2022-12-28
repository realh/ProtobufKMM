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
        implementations, using extensions on the JVM classes. '''
    def __init__(self, namespace: str, options: dict[str, str]):
        super().__init__(baseName="kmm-jvm-conv")
        self.namespace = namespace
        self.options = options
    
    def messageOpening(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        typeName = self.typeNameCase(name)
        camelName = self.memberCase(name)   # DSL builder
        return [
            "fun %s.Companion.fromData(data: %s.%s): %s {" % \
                    (typeName, self.namespace, typeName, typeName),
            "    return %s {" % camelName
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
            convOpen = ""
            convClose = ".map { it.fromData() }"
        elif builtIn:
            convOpen = ""
            convClose = ""
        else:
            convOpen = "%s.fromData(" % typeName
            convClose = ")"
        if not isList and typeName.endswith("?"):
            return ["        data.%s?.let { this.%s = %sit%s }" % \
                (fieldName, fieldName, convOpen, convClose)]
        else:
            return ["        this.%s = %sdata.%s%s" % \
                (fieldName, convOpen, fieldName, convClose)]


class FromJVMGenerator(Generator):
    ''' A helper class which makes it possible for the main generator to make
        two passes on each message using the super processMessage(); this
        handles the pass for adding extensions to the JVM implementations to
        convert them to the data classes. '''
    def __init__(self, namespace: str, options: dict[str, str]):
        super().__init__(baseName="kmm-jvm-conv")
        self.namespace = namespace
        self.options = options
    
    def messageOpening(self, msg: DescriptorProto,
                       name: str, indentationLevel: int) -> list[str]:
        typeName = self.typeNameCase(name)
        return [
            "fun %s.toData(): %s.%s {" % \
                    (typeName, self.namespace, typeName),
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
        builtIn = self.typeIsBuiltIn(field.type, field.type_name)
        isList = field.label == FieldDescriptorProto.LABEL_REPEATED
        if isList and not builtIn:
            conv = "map { it.toData() }"
        elif builtIn:
            conv = ""
        else:
            conv = ".toData()"
        orNull = "OrNull"
        if not isList and typeName.endswith("?"):
            orNull = "OrNull"
            if len(conv) > 0:
                conv = "?" + conv
        else:
            orNull = ""
        return ["        %s = this.%s%s%s" % \
            (fieldName, fieldName, orNull, conv)]


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
            "fun %s.Companion.fromData(data: %s.%s) {" % \
                    (typeName, self.namespace, typeName),
            "    return %s.forValue(data.value)" % typeName,
            "}",
            "",
            "fun %s.toData(): %s.%s {" % \
                    (typeName, self.namespace, typeName),
            "    return %s.%s from this.value" % (self.namespace, typeName),
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
