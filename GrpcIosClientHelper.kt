package org.example.proto

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.*
import kotlin.coroutines.*

object GrpcIosClientHelper {
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

    fun<R> serverStreamingCall(
        closure: ((R?, String?) -> Unit) -> Unit
    ): Flow<R> {
        return callbackFlow {
            closure { success, failure ->
                if (failure != null) {
                    cancel("GRPC stream error: $failure")
                } else if (success == null) {
                    cancel("Received null from GRPC stream")
                } else {
                    trySend(success)
                }
            }
            awaitClose {}
        }
    }

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

    interface ClientStreamer<T> {
        fun send(message: T)
        fun finish()
    }
}