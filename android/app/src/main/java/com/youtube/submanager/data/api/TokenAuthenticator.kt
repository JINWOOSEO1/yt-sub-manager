package com.youtube.submanager.data.api

import android.util.Log
import com.youtube.submanager.data.repository.TokenStore
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import javax.inject.Inject
import javax.inject.Provider

class TokenAuthenticator @Inject constructor(
    private val tokenStore: TokenStore,
    private val apiServiceProvider: Provider<ApiService>
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        // Don't retry if we already retried
        if (response.request.header("X-Retry-Auth") != null) {
            return null
        }

        // Don't retry auth endpoints
        if (response.request.url.encodedPath.contains("auth/")) {
            return null
        }

        synchronized(this) {
            return try {
                kotlinx.coroutines.runBlocking {
                    // Try to refresh the token
                    val apiService = apiServiceProvider.get()
                    val tokenResponse = apiService.refreshToken()

                    // Save new token
                    tokenStore.saveToken(tokenResponse.access_token)
                    Log.d("TokenAuthenticator", "JWT refreshed successfully")

                    // Retry the original request with new token
                    response.request.newBuilder()
                        .header("Authorization", "Bearer ${tokenResponse.access_token}")
                        .header("X-Retry-Auth", "true")
                        .build()
                }
            } catch (e: Exception) {
                Log.e("TokenAuthenticator", "JWT refresh failed", e)
                // Clear token - user needs to re-login
                kotlinx.coroutines.runBlocking { tokenStore.clearToken() }
                null
            }
        }
    }
}
