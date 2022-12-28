import re
import sys

from google.protobuf.compiler.plugin_pb2 import \
    CodeGeneratorRequest, CodeGeneratorResponse
from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    FieldDescriptorProto

import log

class Generator:
    ''' A Generator loads a .proto file and generates some source code from it.
        It must be overridden to provide ?? methods. '''
    def __init__(self, baseName: str):
        ''' baseName is the base name of the plugin eg protoc-gen-ktdata has a
            base name of "ktdata". '''
        self.baseName = baseName
        self.log = log.getLogger("protoc-gen-" + baseName)
        self.log.debug("sys.argv = %s" % str(sys.argv))
        self.knownTypes = (
            None,
            "Double", "Float", "Long", "Long", "Int",
            "Long", "Int", "Boolean", "String",
            None, # Group
            None, # Message
            "ByteArray", "Int",
            None, # Enum
            "Int", "Long",
            "Int", "Long"
        )
        self.knownTypesByName = {
            "double": "Double",
            "float": "Float",
            "int32": "Int",
            "int64": "Long",
            "uint32": "Int",
            "uint64": "Long",
            "sint32": "Int",
            "sint64": "Long",
            "fixed32": "Int",
            "fixed64": "Long",
            "sfixed32": "Int",
            "sfixed64": "Long",
            "bool": "Boolean",
            "string": "String",
            "bytes": "ByteArray"
        }

    def runOnStdinAndStdout(self):
        ''' This can be used as the entry point to load the
            CodeGeneratorRequest from stdin, process it and write the
            CodeGeneratorResponse to stdout.
        '''
        input = sys.stdin.buffer.read()
        req = CodeGeneratorRequest.FromString(input)
        response = self.process(req)
        output = response.SerializeToString()
        sys.stdout.buffer.write(output)
    
    def process(self, req: CodeGeneratorRequest) -> CodeGeneratorResponse:
        ''' Processes a CodeGeneratorRequest and generates a
            CodeGeneratorResponse by calling self.processFile() for each proto
            file in req. '''
        response = CodeGeneratorResponse()
        for f in req.proto_file:
            self.processFile(f, response)
        return response
    
    def processFile(self, protoFile: FileDescriptorProto,
                    response: CodeGeneratorResponse):
        ''' Processes each proto file, adding a new output file to the response.
            It sets self.options to a dict of the options read from protoFile.
        '''
        self.options = self.getOptions(protoFile)
        fileName = self.getOutputFileName(protoFile.name,
                protoFile.package)
        file = response.file.add()
        file.name = fileName
        file.content = self.getContent(protoFile)
    
    def getOptions(self, protoFile: FileDescriptorProto) -> dict[str, str]:
        ''' Returns a dict of options read from protoFile. '''
        lines = str(protoFile.options).strip().split("\n")
        options = (l.split(": ") for l in lines)
        kvs = ((i[0], i[1].replace('"', "")) for i in options)
        optsDict = dict(i for i in kvs)
        return optsDict

    def getOutputFileName(self, protoFileName: str, packageName: str) -> str:
        ''' Gets an output file name based on the input proto filename and its
            package name. '''
        return protoFileName + ".kt"

    def getContent(self, protoFile: FileDescriptorProto) -> str:
        ''' Generates the content for an output file as a string. '''
        lines = self.getHeader(protoFile)
        indentationLevel = self.getTopLevelIndentation(protoFile)
        for enum in protoFile.enum_type:
            e = self.processEnum(enum, indentationLevel)
            if len(e) > 0:
                lines.extend(e)
                lines.append("")
        for msg in protoFile.message_type:
            m = self.processMessage(msg, indentationLevel)
            if len(m) > 0:
                lines.extend(m)
                lines.append("")
        lines.extend(self.getFooter(protoFile))
        return "\n".join(lines) + "\n"
    
    def getHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        ''' Gets the first few lines to start the output file. '''
        return []
    
    def getFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        ''' Gets the last few lines to add to the end of the output file. '''
        return []
    
    def getTopLevelIndentation(self, protoFile: FileDescriptorProto) -> int:
        ''' Gets the indentation to use for the top-level classes. '''
        return 0
    
    def processEnum(self, enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        ''' Returns a list of strings (one per line) for an enum definition.
            Each line is indented by an additional number of spaces multiplied
            by indentationLevel. '''
        raise NotImplementedError("processEnum not overridden in %s",
                self.baseName)
    
    def processMessage(self, msg: DescriptorProto,
                       indentationLevel: int) -> list[str]:
        ''' Returns a representation of a protobuf message by calling
            messageOpening(), then messageField() repeatedly, then
            messageClosing(). Each line is indented by an additional number of
            spaces multiplied by indentationLevel. '''
        name = self.typeNameCase(msg.name)
        lines = self.messageOpening(msg, name, indentationLevel)
        indentationLevel += 1
        for enum in msg.enum_type:
            lines.extend(self.processEnum(enum, indentationLevel))
            lines.append("")
        for nested in msg.nested_type:
            lines.extend(self.processMessage(nested, indentationLevel))
            lines.append("")
        for field in msg.field:
            lines.extend(self.processField(msg, field, indentationLevel))
        indentationLevel -= 1
        lines.extend(self.messageClosing(msg, name, indentationLevel))
        return lines
    
    def processField(self, msg: DescriptorProto,
                     field: FieldDescriptorProto,
                     indentationLevel: int) -> list[str]:
        ''' Processes a field of a message. '''
        raise NotImplementedError("processField not overridden in %s",
                self.baseName)

    def getTypeName(self, number: int, typeName: str | None) -> str:
        ''' Gets the typename in the target language (here, Kotlin). '''
        if number == FieldDescriptorProto.TYPE_MESSAGE:
            return self.convertTypeName(typeName) + "?"
        elif number == FieldDescriptorProto.TYPE_ENUM:
            return self.convertTypeName(typeName)
        elif number != 0:
            n = self.getBuiltInTypeByNumber(number)
            if n is not None:
                return n
        if typeName is None:
            return "Any?"
        n = self.getBuiltInTypeByName(typeName)
        if n is not None:
            return n
        return self.convertTypeName(typeName) + "?"
    
    def convertTypeName(self, name: str) -> str:
        ''' Strips any leading qualifier (includes aren't currently supported).
            and applies self.typeNameCase. '''
        if name.startswith("."):
            name = re.sub(r"^\.[a-zA-Z0-9_]*\.", "", name)
        return self.typeNameCase(name)

    def getBuiltInTypeByNumber(self, number: int) -> str | None:
        ''' Looks up a built-in type by its FieldDescriptorProto.Type value,
            using self.knownTypes, which can be replaced in a sub-class'
            constructor if not Kotlin. '''
        if number >= len(self.knownTypes):
            return None
        return self.knownTypes[number]
    
    def getBuiltInTypeByName(self, name: str) -> str | None:
        ''' Looks up a built-in type by its FieldDescriptorProto.type_name,
            using self.knownTypesByName, which can be replaced in a sub-class'
            constructor if not Kotlin. '''
        return self.knownTypesByName(name)
    
    def messageOpening(self, msg: DescriptorProto,
                       name: str,
                       indentationLevel: int) -> list[str]:
        ''' Returns the opening line(s) of a class etc representing a protobuf
            message. '''
        raise NotImplementedError("messageOpening not overridden in %s",
                self.baseName)

    def messageClosing(self, msg: DescriptorProto,
                       name: str,
                       indentationLevel: int) -> list[str]:
        ''' Returns the closing line(s) of a class etc representing a protobuf,
            eg ')' for a Kotlin data class. '''
        raise NotImplementedError("messageClosing not overridden in %s",
                self.baseName)

    def typeNameCase(self, name: str) -> str:
        ''' Converts the case of a name to the appropriate convention for a type
            name, here "foo_bar" -> "FooBar". '''
        if "_" not in name:
            return name[0].upper() + name[1:]
        elements = name.split("_")
        elements = list(e.capitalize() for e in elements)
        return "".join(elements)

    def enumCase(self, name: str) -> str:
        ''' Converts the case of a name to the appropriate convention for an
            enum member name, here "foo_bar" -> "FOO_BAR". '''
        return name.upper()

    def memberCase(self, name: str) -> str:
        ''' Converts the case of a name to the appropriate convention for a
            method or message field, here camelCase ("foo_bar" -> "fooBar"). '''
        if "_" not in name:
            return name[0].lower() + name[1:]
        elements = name.split("_")
        elements = list(e.capitalize() for e in elements)
        elements[0] = elements[0][0].lower() + elements[0][1:]
        return "".join(elements)

    def getNamespace(self, protoFile: FileDescriptorProto) -> str:
        ''' The Kotlin message and enum classes should be members of an object
            to provide them with a namespace to help avoid clashes when accessed
            from Swift. This returns a suitable name for it. '''
        return self.typeNameCase(protoFile.package) + "ProtoData"