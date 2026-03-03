package com.youtube.submanager.data.repository

import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import com.youtube.submanager.data.api.ApiService
import com.youtube.submanager.data.model.FcmTokenRequest
import com.youtube.submanager.data.model.GoogleAuthRequest
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val tokenStore: TokenStore
) {
    suspend fun login(serverAuthCode: String): Result<Unit> {
        return try {
            val response = api.googleAuth(GoogleAuthRequest(auth_code = serverAuthCode))
            tokenStore.saveToken(response.access_token)
            // Register FCM token after successful login
            registerFcmToken()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private suspend fun registerFcmToken() {
        try {
            val fcmToken = FirebaseMessaging.getInstance().token.await()
            api.registerFcmToken(FcmTokenRequest(fcm_token = fcmToken))
            Log.d("AuthRepository", "FCM token registered after login")
        } catch (e: Exception) {
            Log.e("AuthRepository", "Failed to register FCM token", e)
        }
    }

    suspend fun logout() {
        tokenStore.clearToken()
    }

    fun isLoggedIn(): Boolean = tokenStore.isLoggedIn()
}
