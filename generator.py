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
    def __init__(self, baseName: str, swift = False):
        ''' baseName is the base name of the plugin eg protoc-gen-kmm-data has a
            base name of "kmm-data". '''
        self.baseName = baseName
        self.swift = swift
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
        response = CodeGeneratorResponse()
        self.process(req, response)
        output = response.SerializeToString()
        sys.stdout.buffer.write(output)
    
    def process(self, req: CodeGeneratorRequest,
                response: CodeGeneratorResponse):
        ''' Processes a CodeGeneratorRequest and adds to a
            CodeGeneratorResponse by calling self.processFile() for each proto
            file in req.
            It also parses the request's `parameter` field, generating a dict
            available in self.parameters.
            '''
        self.loadParameters(req)
        for f in req.proto_file:
            self.processProtoFile(f, response)
    
    def loadParameters(self, req: CodeGeneratorRequest):
        ''' Loads parameters from a request. '''
        if len(req.parameter) > 0:
            parameters = (p.split("=") for p in req.parameter.split(","))
            self.parameters = { p[0]: p[1] for p in parameters }
        else:
            self.parameters = {}
    
    def processProtoFile(self, protoFile: FileDescriptorProto,
                         response: CodeGeneratorResponse):
        ''' Processes each proto file, adding a new set of output files to the
            response. It first sets self.options to a dict of the options read
            from protoFile. '''
        self.loadOptions(protoFile)
        self.processMessagesAndEnums(protoFile, response)
        self.processServices(protoFile, response)
    
    def loadOptions(self, protoFile: FileDescriptorProto):
        ''' Assigns self.options etc read from protoFile . '''
        self.packageName = self.typeNameCase(protoFile.package)
        lines = str(protoFile.options).strip().split("\n")
        options = (l.split(": ") for l in lines)
        kvs = ((i[0], i[1].replace('"', "")) for i in options)
        self.options = dict(i for i in kvs)
        if not self.swift:
            self.javaPackage = self.options["java_package"]
            self.kmmPackage = self.parameters.get(
                "kmm_package",
                self.javaPackage + ".kmm"
            )

    def getOutputFilenameForClass(self, protoName: str,
                                  className: str) -> str:
        ''' Gets an output file name based on a qualified class (message or
            enum) name. In Swift, each proto package has one file for all
            messages and enums, so className should be "Data" or "Converters".
            In Kotlin className should already use typename case convention
            and include "Converter" for converter extensions. '''
        if self.swift:
            protoName = self.typeNameCase(protoName)
            return "%s_%s.swift" % (protoName, className)
        else:
            return "%s.kt" % className
    
    def getRole(self):
        ''' Return "Data" or "", "Converter" etc depending on which are being
            generated: message/enum definitions or converters. '''
        return ""

    def addResponseFile(self, protoName: str,
                        className: str, response: CodeGeneratorResponse,
                        content: list[str]):
        ''' Adds content to a new file in the response, named by
            getOutputFileNameForClass. '''
        file = response.file.add()
        file.name = self.getOutputFilenameForClass(protoName, className)
        file.content = "\n".join(content)
    
    def processMessagesAndEnums(self, protoFile: FileDescriptorProto,
                                response: CodeGeneratorResponse):
        ''' Processes messages and enums in protoFile. In Swift there is
            one output file, in Kotlin there is one per message/enum. '''
        protoName = self.typeNameCase(protoFile.name)
        if self.swift:
            content = self.getDataHeader(protoFile)
        indentationLevel = 0
        for enum in protoFile.enum_type:
            if not self.swift:
                content = self.getDataHeader(protoFile)
            e = self.processEnum(protoName, enum, indentationLevel)
            content.extend(e)
            if self.swift:
                content.append("")
            else:
                content.extend(self.getDataFooter(protoFile))
                self.addResponseFile(
                    protoFile.package,
                    self.convertTypeName(enum.name) + self.getRole(),
                    response,
                    content
                )
        for msg in protoFile.message_type:
            if not self.swift:
                content = self.getDataHeader(protoFile)
            m = self.processMessage(protoName, msg, indentationLevel)
            content.extend(m)
            if self.swift:
                content.append("")
            else:
                content.extend(self.getDataFooter(protoFile))
                self.addResponseFile(
                    protoFile.package,
                    self.convertTypeName(msg.name) + self.getRole(),
                    response,
                    content
                )
        if self.swift:
            content.extend(self.getDataFooter(protoFile))
            self.addResponseFile(
                protoFile.package,
                self.getRole(),
                response,
                content
            )

    def processServices(self, protoFile: FileDescriptorProto,
                        response: CodeGeneratorResponse):
        ''' Processes services in protoFile. There is one service per
            output file. '''
        for serv in protoFile.service:
            content = self.processService(protoFile, serv)
            self.addResponseFile(
                protoFile.package,
                self.typeNameCase(serv.name) + "Grpc" + self.getClientVariety(),
                response,
                content)
    
    def getDataHeader(self, protoFile: FileDescriptorProto) -> list[str]:
        ''' Gets the first few lines to start a file containing one or many
            messages/enums. '''
        if self.swift:
            shared = self.parameters.get("shared_module", "shared")
            return [
                "import " + str(shared),
                "",
            ]
        else:
            return ["package " + self.kmmPackage, ""]
    
    def getServiceImports(self, protoFile: FileDescriptorProto,
                          serv: ServiceDescriptorProto) -> list[str]:
        lines = self.getDataHeader(protoFile)
        if self.swift:
            lines = [
                "import Foundation",
                "import GRPC",
            ] + lines
        return lines
    
    def getDataFooter(self, protoFile: FileDescriptorProto) -> list[str]:
        ''' Gets the last few lines to add to the end of  a file containing one
            or many messages/enums.. '''
        return []
    
    def processEnum(self, prefix: str,
                    enum: EnumDescriptorProto,
                    indentationLevel: int) -> list[str]:
        ''' Returns a list of strings (one per line) for an enum definition.
            Each line is indented by an additional number of spaces multiplied
            by indentationLevel. prefix is derived from the proto package name,
            followed by parent messages when nested. '''
        raise NotImplementedError("processEnum not overridden in %s",
                self.baseName)
    
    def processMessage(self, prefix: str,
                       msg: DescriptorProto,
                       indentationLevel: int) -> list[str]:
        ''' Returns a representation of a protobuf message by calling
            messageOpening(), then messageField() repeatedly, then
            messageClosing(). Each line is indented by an additional number of
            spaces multiplied by indentationLevel. prefix is derived from the
            proto package name, followed by parent messages when nested. '''
        name = self.typeNameCase(msg.name)
        lines = self.messageOpening(prefix, msg, name, indentationLevel)
        indentationLevel += 1
        prefix += "." + name
        for enum in msg.enum_type:
            lines.extend(self.processEnum(prefix, enum, indentationLevel))
            lines.append("")
        for nested in msg.nested_type:
            lines.extend(self.processMessage(prefix + name,
                                             nested,
                                             indentationLevel))
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
                       serv: ServiceDescriptorProto) -> list[str]:
        ''' Processes a grpc service. '''
        lines = self.getServiceHeader(protoFile, serv)
        for method in serv.method:
            lines.extend(self.getServiceMethod(protoFile,
                                               serv,
                                               method))
        lines.extend(self.getServiceFooter(protoFile, serv))
        return lines

    def getServiceHeader(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto) -> list[str]:
        ''' Gets the start of a service definition eg a class. '''
        lines = self.getServiceImports(protoFile, serv)
        servName = self.getServiceName(protoFile, serv)
        lines.append("%s %sGrpc%s %s" % (
            self.getServiceEntity(),
            servName,
            self.getClientVariety(),
            self.getServiceOpenBracket(),
        ))
        return lines
    
    def getServiceEntity(self):
        ''' "class", "interface" etc for a service definition. '''
        return "class"
    
    def getServiceName(self, protoFile: FileDescriptorProto,
                       serv: ServiceDescriptorProto) -> str:
        ''' Gets the name of a service, which is qualified with the proto
            package in Swift. '''
        serviceName = self.typeNameCase(serv.name)
        if self.swift:
            packageName = self.typeNameCase(protoFile.package)
            return packageName + "_" + serviceName
        else:
            return serviceName

    def getServiceFooter(self, protoFile: FileDescriptorProto,
                         serv: ServiceDescriptorProto) -> list[str]:
        ''' Override to provide the end of a service definition eg a closing
            brace. '''
        return ["}"]

    def getServiceMethod(self, protoFile: FileDescriptorProto,
                        serv: ServiceDescriptorProto,
                        method: MethodDescriptorProto) -> list[str]:
        ''' Override to provide a method definition. It can simply forward
            to getMethodSignature for an interface.
        '''
        return []

    def getMethodSignature(self, protoFile: FileDescriptorProto,
                           serv: ServiceDescriptorProto,
                           method: MethodDescriptorProto,
                           withCallbacks = False) -> list[str]:
        ''' Gets a method signature (without opening brace). '''
        if self.swift:
            withCallbacks = True
        # Server streaming methods don't need to be suspending
        if method.server_streaming:
            suspend = ""
        else:
            suspend = self.getSuspendKeyword()
        inputType = self.convertTypeName(method.input_type)
        if method.client_streaming and withCallbacks:
            arg = self.getResultCallback(protoFile, method)
            arg = ["    " + l for l in arg]
            ret = [")%s%s" % (
                self.getReturnSymbol(),
                self.getStreamerInterfaceName(protoFile, serv, inputType)
            )]
        else:
            if method.client_streaming:
                inputType = self.convertClientStreamingInput(inputType)
            ret = self.getReturn(protoFile, method)
            arg = ["    request: %s%s" % (inputType, ret[0])]
            ret = ret[1:]
        lines = ["%s%s%s(" % (suspend,
                              self.getFuncKeyword(),
                              self.memberCase(method.name)
                              ),
        ]
        lines.extend(arg)
        lines.extend(ret)
        return ["    " + l for l in lines]
    
    def convertClientStreamingInput(self, typeName: str) -> str:
        ''' Converts the type of a request input to a client streaming version.
            N/A in swift. '''
        return "Flow<%s>" % typeName
    
    def getReturn(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' Gets a return clause for a method: the closing brace and return
        type. When using callbacks, override and forward to
        getResultCallbackInLieuOfReturn instead (this is automatic for Swift).
        Remember that closure types use "->" for return in both Kotlin and
        Swift, whereas in method/function definitions Kotlin uses ":".  The
        first line should be appended to the end of the parameters in case it's
        a comma separator for a result callback parameter. '''
        if self.swift:
            return self.getResultCallbackInLieuOfReturn(protoFile, method)
        typeName = self.convertTypeName(method.output_type)
        if method.server_streaming:
            typeName = "Flow<%s>" % typeName
        return [ "", ")" + self.getReturnSymbol() + typeName]
    
    def getResultCallbackInLieuOfReturn(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' For methods using callbacks, gets the final parameter used to
            return the result. If the callback receives success and failure
            both null, it means a server stream was closed without error. '''
        cb = self.getResultCallback(protoFile, method)
        cb = ["    " + l for l in cb]
        return [","] + cb + [")"]

    def getResultCallback(self, protoFile: FileDescriptorProto,
                  method: MethodDescriptorProto) -> list[str]:
        ''' For methods using callbacks, gets the final parameter used to
            return the result. If the callback receives success and failure
            both null, it means a server stream was closed without error. '''
        typeName = self.convertTypeName(method.output_type)
        if not typeName.endswith("?"):
            typeName += "?"
        escaping = "@escaping " if self.swift else ""
        return ["result: %s(%s, String?)%s" % \
                (escaping, typeName, self.getReturnVoid())
        ]
    
    def getFuncKeyword(self) -> str:
        ''' Gets the keyword for a function in the target language, including
            a trailing space. '''
        return "func " if self.swift else "fun "
    
    def getReturnSymbol(self) -> str:
        ''' Including any spaces. ": " for Kotlin, use " -> " for Swift. '''
        return " -> " if self.swift else ": "

    def getReturnVoid(self) -> str:
        ''' Gets the return clause (symbol and type) for a function that
            returns nothing (Void/Unit). This is used for closure type
            definitions, so the return symbol is -> for Kotlin as well as
            for Swift. '''
        t = "Void" if self.swift else "Unit"
        return "->" + t

    def getSuspendKeyword(self) -> str:
        ''' This is only useful for Kotlin, Swift should return "". '''
        return "" if self.swift else "suspend "
    
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
        ''' Strips any leading qualifier (includes aren't currently supported),
            applies self.typeNameCase. '''
        if name.startswith("."):
            name = name.split(".")
            if self.swift:
                prefix = name[1]
                name = "".join(name[2:])
                return self.typeNameCase(prefix) + self.typeNameCase(name)
            else:
                name = ".".join(name[2:])
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
    
    def messageOpening(self, prefix: str,
                       msg: DescriptorProto,
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

    def getStreamerInterfaceName(self, protoFile: FileDescriptorProto,
                                 serv: ServiceDescriptorProto,
                                 typeName: str) -> str:
        ''' Gets a name for the interface used to send client streaming 
            messages from Kotlin to Swift.  '''
        if typeName.endswith("?"):
            typeName = typeName[:-1]
        if self.swift:
            return "GrpcIosClientHelperClientStreamer"
        else:
            return "GrpcIosClientHelper.ClientStreamer<%s>" % typeName
    
    def getClientVariety(self):
        ''' "AndroidClient", "IosDelegate" etc. '''
        return "Client"
    
    def getServiceOpenBracket(self):
        ''' "(" or "{" depending on whether the class has constructor
            parameters.'''
        return "{"