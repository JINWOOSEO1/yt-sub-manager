package com.youtube.submanager.data.api

import com.youtube.submanager.data.repository.TokenStore
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject

class AuthInterceptor @Inject constructor(
    private val tokenStore: TokenStore
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val token = tokenStore.getToken()

        // Skip auth for the login endpoint
        if (original.url.encodedPath.contains("auth/google")) {
            return chain.proceed(original)
        }

        if (token != null) {
            val request = original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
            return chain.proceed(request)
        }

        return chain.proceed(original)
    }
}
