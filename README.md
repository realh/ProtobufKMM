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
can just put simple wrapper scripts in your PATH, for example:

### protoc-gen-kmmdata
```
#!/bin/sh
exec /usr/bin/env python3 "$HOME/Code/ProtobufKMM/protoc-gen-kmmdata.py" "$@"
```
and invoke with:
```
protoc --kmmdata_out=/some/path /path/to/some_protobuf_file.proto
```

The bad news is that the first time you create any Swift files you will have
to manually add them to your XCode project by dragging them from Finder.

## The protoc plugins

### protoc-gen-kmmdata (WIP)

Generates Kotlin data classes and enum classes for the protobuf messages and
enums. Designed to be used in your shared module with minimum fuss.

The enum and data classes are all wrapped in an object called
`YourProtoPackageProtoData` where `YourProtoPackage` is the capitalised
version of the name of your protocol file as given in its `package` directive.
This is to help avoid name clashes when they're imported into Swift.

### protoc-gen-kmmjvmconv (TODO)

Will generate Kotlin class extensions in the Android module which convert the
simple data classes and enums from the kmmdata plugin to and from their
Kotlin/JVM counterparts.

### protoc-gen-kmmswiftconv (TODO)

Will generate Swift class extensions in the Swift module which convert the
simple data classes and enums from the kmmdata plugin to and from their Swift
counterparts.

### protoc-gen-kmmgrpc (TODO)

Will generate:

* An interface for the shared module which encapsulates all the rpc methods in
  the proto file, using suspend functions, Flows and the kmmdata types. 

* A class in the Android module implementing the above interface, converting
  the data types to and from the JVM implementation counterparts.

* A Kotlin class with the same interface in the shared iOS module which uses
  a Swift delegate and callbacks to interface between Kotlin and Swift.

* A Swift class to act as the delegate for the above.

## Licence

ISC. See [LICENSE](LICENSE).
