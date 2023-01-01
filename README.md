# ProtobufKMM

This is (will be) a set of protoc plugins to generate code for using
[grpc](https://grpc.io) and
[protobuf](https://developers.google.com/protocol-buffers) in
[Kotlin Multiplatform Mobile](https://kotlinlang.org/lp/mobile/).

I couldn't get
[GRPC-Kotlin-Multiplatform](https://github.com/TimOrtel/GRPC-Kotlin-Multiplatform)
to work, so I decided to write an alternative. It's based on a set of
stand-alone protoc plugins to avoid the complexity of gradle which seems to be
the main cause of the problems in GRPC-Kotlin-Multiplatform.

For the sake of getting up and running quickly, this still relies on existing
implementations for Android and iOS, using
[grpc-swift](https://github.com/grpc/grpc-swift) on the latter. This is because
I don't know Objective-C, and because I don't want to have to use Cocoapods.

## Implementation

It's very simple, you just need python3 and the protobuf package, which is
available with pip or most package managers. Rather than install anything you
can include the path to the python scripts in your protoc invocations using the
`--plugin` option eg:
`--plugin="$HOME/Code/ProtobufKMM/protoc-gen-kmm-data"`.

## The protoc plugins

### protoc-gen-kmm-data

Generates Kotlin data classes and enum classes for the protobuf messages and
enums. Designed to be used in your shared module with minimum fuss. The output
file has the same Java/Kotlin package as the JVM implementation, read from the
proto file's `java_package` option.

The enum and data classes are all wrapped in an object called
`YourProtoPackageProtoData` where `YourProtoPackage` is the capitalised
version of the name of your protocol file as given in its `package` directive.
This is to help avoid name clashes when they're imported into Swift.

The output filename is `YourProtoPackageData.kt`.

### protoc-gen-kmm-jvm-conv

Generates Kotlin class extensions in the Android module which convert the
simple data classes and enums generated by the kmm-data plugin to and from
their Kotlin/JVM counterparts. Each class in the JVM implementation is extended
with a `toData` instance method and each portable data class and enum is
extended with a `toProto` instance method.

The output filename is `YourProtoPackageConverters.kt`.

### protoc-gen-kmm-swift-conv

Generates Swift class extensions in the Swift module which convert the
simple data classes and enums generated by the kmm-data plugin to and from
their Swift counterparts.

If your project's shared module is not called `shared`, its name must be passed
as an option in the protoc invocation, eg
`--kmm-swift-conv_opt=shared_module='MySharedModuleName'`.

The output filename is `YourProtoPackageConverters.swift`.

### protoc-gen-kmm-grpc-shared

Generates an interface for each service in the shared module which encapsulates
all the rpc methods in the proto file, using suspend functions, Flows and the
kmm-data types. Each interface is named `YourProtoPackageServiceNameGrpcClient`;
if there is only one service and it has the same name as the package, the name
is shortened to `ServiceNameGrpcClient`. The filename is
`YourProtoPackageGrpcClient.kt`.

### protoc-gen-kmm-grpc-android

Generates classes in the Android module implementing the above GrpClient
interfaces, converting the data types to and from their JVM implementation
counterparts. Where entity names have a suffix of `GrpcClient` above, the
Android implementations have a suffix of `AndroidGrpcClient`.

### protoc-gen-kmm-grpc-ios (TODO)

Will generate classes in the `iosMain` part of the shared module, implementing
the above interface. They will use Swift delegates and callbacks to interface
between Kotlin and grpc-swift.

### protoc-gen-kmm-grpc-swift (TODO)

Swift classes to act as the delegates for the above.

## Limitations

This set of plugins was written to support a specific app, which needs to be
completed ASAP. I don't have time to work on protobuf features it doesn't use,
which include:

* Nested messages and enums.
* Includes.
* Extensions.

So these plugins will generate incorrect code for them. However, this code is
sufficiently simple and well-documented that I think a third party wouldn't
find it too difficult to add those features if they need them.

### Adding Swift files to your XCode project

The first time you create any Swift files you will have to manually add them to
your XCode project by dragging them from Finder, even if they are created in
the correct location.

## Licence

ISC. See [LICENSE](LICENSE).
