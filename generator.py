import re
import sys

from google.protobuf.compiler.plugin_pb2 import \
    CodeGeneratorRequest, CodeGeneratorResponse
from google.protobuf.descriptor_pb2 import \
    FileDescriptorProto, \
    EnumDescriptorProto, DescriptorProto, \
    FieldDescriptorProto, \
    ServiceDescriptorProto, MethodDescriptorProto

import log

class Generator:
    ''' A Generator loads a .proto file and generates some source code from it.
        It must be overridden to provide certain methods. '''
    def __init__(self, baseName: str):
        ''' baseName is the base name of the plugin eg protoc-gen-kmm-data has a
            base name of "kmm-data". '''
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
            file in req.
            It also parses the request's `parameter` field, generating a dict
            available in self.parameters.
            '''
        response = CodeGeneratorResponse()
        if len(req.parameter) > 0:
            parameters = (p.split("=") for p in req.parameter.split(","))
            self.parameters = { p[0]: p[1] for p in parameters }
        else:
            self.parameters = {}
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
        for serv in protoFile.service:
            s = self.processService(protoFile, serv, indentationLevel)
            if len(s) > 0:
                lines.extend(s)
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
        # If the last field has a trailing comma, that's optional in Kotlin
        # but forbidden in Swift, so remove it.
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]
        indentationLevel -= 1
        lines.extend(self.messageClosing(msg, name, indentationLevel))
        return lines
    
    def processField(self, msg: DescriptorProto,
                     field: FieldDescriptorProto,
                     indentationLevel: int) -> list[str]:
        ''' Processes a field of a message. '''
        raise NotImplementedError("processField not overridden in %s",
                self.baseName)
    
    def processService(self, protoFile: FileDescriptorProto,
                       serv: ServiceDescriptorProto,
                       indentationLevel: int) -> list[str]:
        ''' Processes a grpc service. '''
        lines = self.getServiceHeader(protoFile, serv, indentationLevel)
        for method in serv.method:
            lines.extend(self.getServiceMethod(protoFile,
                                               serv,
                                               method,
                                               indentationLevel))
        lines.extend(self.getServiceFooter(protoFile, serv, indentationLevel))
        return lines

    def getServiceHeader(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        ''' Override to provide the start of a service definition eg a class.
        '''
        return []
    
    def getServiceName(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto) -> str:
        packageName = self.typeNameCase(protoFile.package)
        serviceName = self.typeNameCase(serv.name)
        if len(protoFile.service) == 1 and packageName == serviceName:
            return serviceName
        else:
            return packageName + serviceName

    def getServiceFooter(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto,
                         indentationLevel: int) -> list[str]:
        ''' Override to provide the end of a service definition eg a closing
            brace. '''
        return []

    def getServiceMethod(self, protoFile: FileDescriptorProto,
                        serv: ServiceDescriptorProto,
                        method: MethodDescriptorProto,
                        indentationLevel: int) -> list[str]:
        ''' Override to provide a method definition. It can simply forward
            to getMethodSignature for an interface.
        '''
        return []

    def getMethodSignature(self, protoFile: FileDescriptorProto,
                           serv: ServiceDescriptorProto,
                           method: MethodDescriptorProto,
                           indentationLevel: int) -> list[str]:
        ''' Gets a method signature (without opening brace). '''
        indent = "    " * indentationLevel
        # Server streaming methods don't need to be suspending
        if method.server_streaming:
            suspend = ""
        else:
            suspend = self.getSuspendKeyword()
        inputType = self.getNamespace(protoFile) + "." + \
            self.convertTypeName(method.input_type)
        if method.client_streaming:
            inputType = self.convertClientStreamingInput(inputType)
        ret = self.getReturn(protoFile, method)
        return ["%s%s%s%s(" % (indent,
                               suspend,
                               self.getFuncKeyword(),
                               self.memberCase(method.name)
                               ),
                "%s    request: %s%s" % (indent, inputType, ret[0]),
               ] + [indent + r for r in ret[1:]]
    
    def convertClientStreamingInput(self, typeName: str) -> str:
        ''' Converts the type of a request input to a client streaming version.
        '''
        return "Flow<%s>" % typeName
    
    def getReturn(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' Gets a return clause for a method: the closing brace and return
            type. When using callbacks, override and forward to
            getResultCallbackInLieuOfReturn instead. The first line should be
            appended to the end of the parameters in case it's a comma separator
            for a result callback parameter. '''
        typeName = self.getNamespace(protoFile) + "." + \
            self.convertTypeName(method.output_type)
        if method.server_streaming:
            typeName = "Flow<%s>" % typeName
        return [ "", ")" + self.getReturnSymbol() + typeName]
    
    def getResultCallbackInLieuOfReturn(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' For methods using callbacks, gets the final parameter used to
            return the result. If the callback receives success and failure
            both null, it means a server stream was closed without error. '''
        return [","] + self.getResultCallback(protoFile, method)

    def getResultCallback(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' For methods using callbacks, gets the final parameter used to
            return the result. If the callback receives success and failure
            both null, it means a server stream was closed without error. '''
        typeName = self.getNamespace(protoFile) + "." + \
            self.convertTypeName(method.output_type)
        if not typeName.endswith("?"):
            typeName += "?"
        return ["    result: (",
                "        success: %s," % typeName,
                "        failure: String?" % typeName,
                "    )" + self.getReturnVoid(),
                ]
    
    def getFuncKeyword(self) -> str:
        ''' Gets the keyword for a function in the target language, including
            a trailing space. '''
        return "fun "
    
    def getReturnSymbol(self) -> str:
        ''' Including any spaces. ": " for Kotlin, use " -> " for Swift. '''
        return ": "

    def getReturnVoid(self) -> str:
        ''' Gets the return clause (symbol and type) for a function that
            returns nothing (Void/Unit). '''
        return self.getReturnSymbol() + "Unit"

    def getSuspendKeyword(self) -> str:
        ''' This is only useful for Kotlin, Swift should return "". '''
        return "suspend "
    
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
    
    def typeIsBuiltIn(self, number: int, typeName: str | None) -> bool:
        ''' Works out whether the type of a field is built-in/primitive. '''
        if number == FieldDescriptorProto.TYPE_MESSAGE:
            return False
        elif number == FieldDescriptorProto.TYPE_ENUM:
            return False
        elif number != 0:
            n = self.getBuiltInTypeByNumber(number)
            if n is not None:
                return True
        if typeName is None:
            # This would be Any?, so it shouldn't be converted
            return True
        n = self.getBuiltInTypeByName(typeName)
        if n is not None:
            return True
        return False
    
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

    def swiftMemberCase(self, name: str) -> str:
        ''' Like memberCase but deals with a quirk in the upstream Swift
            output which has trailing 'Id' replaced by 'ID'. I assume
            "foo_id_bar" also becomes "FooIDBar" but I haven't checked, nor
            whether there are any similar quirks that can be dealt with by
            pattern matching. Nor what should happen to "id_foo_bar". Please
            report any issues, PRs welcome. '''
        if "_" not in name:
            name = name[0].lower() + name[1:]
            if name.endswith("Id"):
                name = name[:-1] + "D"
        elements = name.split("_")
        elements = list(e.capitalize() for e in elements)
        elements[0] = elements[0][0].lower() + elements[0][1:]
        elements = [elements[0]] + ["ID" if e == "Id" else e \
                                    for e in elements[1:]]
        return "".join(elements)

    def getNamespace(self, protoFile: FileDescriptorProto) -> str:
        ''' The Kotlin message and enum classes should be members of an object
            to provide them with a namespace to help avoid clashes when accessed
            from Swift. This returns a suitable name for it. '''
        return self.typeNameCase(protoFile.package) + "ProtoData"