#!/usr/bin/env python3

from google.protobuf.descriptor_pb2 import \
    EnumDescriptorProto, DescriptorProto, FieldDescriptorProto

from generator import Generator

class KtDataGenerator(Generator):
    def __init__(self):
        super().__init__(baseName="ktdata")

    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        indent = "     " * indentationLevel
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
        return "    " * indentationLevel + ")"

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
            default = "False"
        elif typeName in ["Int", "Long", "Float", "Double"]:
            default = "0"
        elif typeName == "ByteArray":
            default = "ByteArray(size = 0)"
        elif field.type == FieldDescriptorProto.TYPE_ENUM:
            default = typeName + " from 0"
        else:
            default = "null"

        indent = "     " * indentationLevel
        return [indent + "val %s: %s = %s," % (field.name, typeName, default)]


def main():
    generator = KtDataGenerator()
    generator.runOnStdinAndStdout()

if __name__ == "__main__":
    main()
