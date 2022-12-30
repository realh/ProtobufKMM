#!/usr/bin/env python3

from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    FieldDescriptorProto

from generator import Generator

class KtDataGenerator(Generator):
    def __init__(self):
        super().__init__(baseName="kmm-data")
    
    def getOutputFileName(self, protoFileName: str, packageName: str) -> str:
        return self.typeNameCase(packageName) + "Data.kt"

    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        indent = "    " * indentationLevel
        lines = [indent + \
                "enum class %s(val value: Int) {" % \
                self.typeNameCase(enum.name)]
        indent += "    "
        for member in enum.value:
            lines.append(indent + self.enumCase(member.name) + \
                "(%d)," % member.number)
        lines.append(indent + ";")
        lines.append(indent + "companion object {")
        indent += "    "
        for member in enum.value:
            lines.append(indent + "const val %s_VALUE = %d" %
                    (self.enumCase(member.name), member.number))
        lines.append("")
        lines.append(
            indent + "infix fun from(value: Int) = " +
                    "values().first { it.value == value }"
        )
        indent = indent[4:]
        lines.append(indent + "}")
        indent = indent[4:]
        lines.append(indent + "}")
        return lines

    def messageOpening(self, msg: DescriptorProto,
                       name: str,
                       indentationLevel: int) -> list[str]:
        return ["    " * indentationLevel + "data class %s(" % name]

    def messageClosing(self, msg: DescriptorProto,
                       name: str,
                       indentationLevel: int) -> list[str]:
        indent = "    " * indentationLevel
        return [ indent + ")" ]

    def processField(self, msg: DescriptorProto,
                     field: FieldDescriptorProto,
                     indentationLevel: int) -> list[str]:
        typeName = self.getTypeName(field.type, field.type_name)
        if field.label == FieldDescriptorProto.LABEL_REPEATED:
            if typeName.endswith("?"):
                typeName = typeName[:-1]
            typeName = "List<%s>" % typeName
            default = "emptyList()"
        elif len(field.default_value) != 0:
            default = field.default_value
            if typeName == "String":
                default = '"' + default + '"'
        elif typeName == "String":
            default = '""'
        elif typeName == "Boolean":
            default = "false"
        elif typeName == "Int":
            default = "0"
        elif typeName == "Long":
            default = "0L"
        elif typeName == "Double":
            default = "0.0"
        elif typeName == "Float":
            default = "0.0F"
        elif typeName == "ByteArray":
            default = "ByteArray(size = 0)"
        elif field.type == FieldDescriptorProto.TYPE_ENUM:
            default = typeName + " from 0"
        else:
            default = "null"

        indent = "    " * indentationLevel
        propName = self.memberCase(field.name)
        return [indent + "val %s: %s = %s," % (propName, typeName, default)]

    def getHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        return [
            "package " + self.options["java_package"],
            "",
            "object " + self.getNamespace(protoFile) + " {"
        ]
    
    def getFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        return ["}"]
    
    def getTopLevelIndentation(self, protoFile: FileDescriptorProto) -> int:
        return 1


def main():
    generator = KtDataGenerator()
    generator.runOnStdinAndStdout()

if __name__ == "__main__":
    main()
