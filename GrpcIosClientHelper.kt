package org.example.proto

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.*
import kotlin.coroutines.*

/**
 * Helper functions for calling grpc-swift methods from Kotlin and getting
 * results via callbacks.
 */
object GrpcIosClientHelper {
    /**
     * Wrapper for a gRPC unary call.
     *
     * @param R type of result (a ProtobufKMM data class).
     * @param closure calls a method in a GrpcIosDelegate implementation and
     *        calls the callback supplied as its parameter with the result.
     * @return the response from the server.
     */
    suspend fun<R> unaryCall(
        closure: ((R?, String?) -> Unit) -> Unit
    ): R {
        return suspendCoroutine { continuation ->
            closure { success, failure ->
                if (failure != null) {
                    continuation.resumeWithException(Exception(failure))
                } else if (success == null) {
                    continuation.resumeWithException(Exception("null result"))
                } else {
                    continuation.resume(success)
                }
            }
        }
    }

    /**
     * Wrapper for a gRPC server-streaming call.
     *
     * @param R type of each message in the returned flow (a ProtobufKMM data
              class).
     * @param closure calls a method in a GrpcIosDelegate implementation and
     *        calls the callback supplied as its parameter with each response
     *        message.
     * @return a flow of responses from the server.
     */
    fun<R> serverStreamingCall(
        closure: ((R?, String?) -> Unit) -> Unit
    ): Flow<R> {
        return callbackFlow {
            closure { success, failure ->
                if (failure != null) {
                    cancel("GRPC stream error: $failure")
                } else if (success == null) {
                    cancel("GRPC server stream closed")
                } else {
                    trySend(success)
                }
            }
            awaitClose {}
        }
    }

    /**
     * Wrapper for a gRPC client-streaming call.
     * 
     * The [start] closure is similar to [unaryCall]'s closure but also returns
     * a [ClientStreamer] provided by the Swift GrpcIosDelegate implementation.
     * This function uses the streamer to feed each message from the input flow
     * to grpc-swift.
     *
     * @param T type of each message in the request (input) flow (a ProtobufKMM
              data class).
     * @param R type of result (a ProtobufKMM data class).
     * @param start see above.
     * @return a flow of responses from the server.
     */
    suspend fun<T, R> clientStreamingCall(
        request: Flow<T>,
        start: ((R?, String?)->Unit)->ClientStreamer<T>,
    ): R {
        val stopStream = MutableStateFlow(false)
        val context = coroutineContext
        val result = suspendCoroutine { continuation ->
            val sender = start { success, failure ->
                if (failure != null) {
                    continuation.resumeWithException(Exception(failure))
                } else if (success == null) {
                    continuation.resumeWithException(Exception("null result"))
                } else {
                    continuation.resume(success)
                }
            }
            CoroutineScope(context).launch {
                request.combine(stopStream) { req, stop -> req to stop }
                    .takeWhile { !it.second }
                    .collect {
                        sender.send(it.first)
                    }
                sender.finish()
            }
        }
        stopStream.update { true }
        return result
    }

    /**
     * Wrapper for a gRPC bidirectional-streaming call.
     *
     * @param T type of each message in the request (input) flow (a ProtobufKMM
              data class).
     * @param R type of each message in the returned flow (a ProtobufKMM data
              class).
     * @param start see the explanation for [clientStreamingCall].
     * @return the response from the server, sent after the input stream is
               closed.
     */
    fun<T, R> bidirectionalStreamingCall(
        request: Flow<T>,
        start: ((R?, String?)->Unit)->ClientStreamer<T>,
    ): Flow<R> {
        return callbackFlow {
            val sender = start { success, failure ->
                if (failure != null) {
                    cancel("GRPC stream error: $failure")
                } else if (success == null) {
                    cancel("Received null from GRPC stream")
                } else {
                    trySend(success)
                }
            }
            MainScope().launch {
                request.collect { sender.send(it) }
                sender.finish()
            }
            awaitClose {}
        }
    }

    /**
     * Kotlin interface for a Swift object that feeds messages to a
     * client-streaming gRPC call.
     *
     * @param T message type.
     */
    interface ClientStreamer<T> {
        /**
         * Send a message.
         *
         * @param message
         */
        fun send(message: T)

        /**
         * Should be called when the input stream ends.
         */
        fun finish()
    }
}