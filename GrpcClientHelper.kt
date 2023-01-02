package org.example.proto

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlin.coroutines.*

object GrpcClientHelper {
    suspend fun<T, R> unaryCall(
        request: T,
        closure: (T, (R?, String?) -> Unit) -> Unit
    ): R {
        return suspendCoroutine { continuation ->
            closure(request) { success, failure ->
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

    fun<T, R> serverStreamingCall(
        request: T,
        closure: (T, (R?, String?) -> Unit) -> Unit
    ): Flow<R> {
        return callbackFlow {
            closure(request) { success, failure ->
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

    suspend fun<T, R, S> bidirectionalStreamingCall(
        request: Flow<T>,
        start: ((R?, String?)->Unit)->ClientStreamer<T>,
    ): Flow<R> {
        val context = coroutineContext
        return callbackFlow {
            val producerScope = this
            val sender = start { success, failure ->
                if (failure != null) {
                    cancel("GRPC stream error: $failure")
                } else if (success == null) {
                    cancel("Received null from GRPC stream")
                } else {
                    trySend(success)
                }
            }
            CoroutineScope(context).launch {
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