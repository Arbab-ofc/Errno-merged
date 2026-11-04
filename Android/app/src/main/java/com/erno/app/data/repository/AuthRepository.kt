package com.erno.app.data.repository

import com.erno.app.data.model.AuthResponse
import com.erno.app.data.model.RegisterRequest
import com.erno.app.data.model.SendOtpRequest
import com.erno.app.data.model.SendOtpResponse
import com.erno.app.data.model.VerifyOtpRequest
import com.erno.app.data.remote.ErnoApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

interface AuthRepository {
    fun sendOtp(phoneNumber: String, role: String? = null): Flow<Result<SendOtpResponse>>
    fun verifyOtp(phoneNumber: String, otpCode: String): Flow<Result<AuthResponse>>
    fun register(fullName: String, phoneNumber: String, role: String): Flow<Result<AuthResponse>>
}

class AuthRepositoryImpl(
    private val apiService: ErnoApiService? = null
) : AuthRepository {

    override fun sendOtp(phoneNumber: String, role: String?): Flow<Result<SendOtpResponse>> = flow {
        try {
            if (apiService != null) {
                val response = apiService.sendOtp(SendOtpRequest(phoneNumber, role))
                emit(Result.success(response))
            } else emit(Result.failure(IllegalStateException("Phone OTP is unavailable. Sign in with Google.")))
        } catch (e: Exception) {
            emit(Result.failure(e))
        }
    }

    override fun verifyOtp(phoneNumber: String, otpCode: String): Flow<Result<AuthResponse>> = flow {
        try {
            if (apiService != null) {
                val response = apiService.verifyOtp(VerifyOtpRequest(phoneNumber, otpCode))
                emit(Result.success(response))
            } else emit(Result.failure(IllegalStateException("Phone OTP is unavailable. Sign in with Google.")))
        } catch (e: Exception) {
            emit(Result.failure(e))
        }
    }

    override fun register(fullName: String, phoneNumber: String, role: String): Flow<Result<AuthResponse>> = flow {
        try {
            if (apiService != null) {
                val response = apiService.register(RegisterRequest(fullName, phoneNumber, role))
                emit(Result.success(response))
            } else emit(Result.failure(IllegalStateException("Registration requires verified Firebase authentication.")))
        } catch (e: Exception) {
            emit(Result.failure(e))
        }
    }
}
