package com.erno.app.data.repository

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.google.firebase.FirebaseApp
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** AES-GCM encrypted storage for revocable opaque ERRNO sessions. Firebase tokens remain in Firebase Auth. */
object ErrnoSessionStore {
    private const val alias = "errno.backend.session.aes"
    private const val preferenceFile = "errno_secure_session"
    private const val tokenKey = "access_token"

    private fun prefs() = FirebaseApp.getInstance().applicationContext.getSharedPreferences(preferenceFile, 0)
    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true).build())
        return generator.generateKey()
    }
    fun save(token: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, secretKey()) }
        val packed = cipher.iv + cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        prefs().edit().putString(tokenKey, Base64.encodeToString(packed, Base64.NO_WRAP)).apply()
    }
    fun read(): String? = runCatching {
        val packed = Base64.decode(prefs().getString(tokenKey, null) ?: return null, Base64.NO_WRAP)
        val iv = packed.copyOfRange(0, 12)
        val data = packed.copyOfRange(12, packed.size)
        String(Cipher.getInstance("AES/GCM/NoPadding").run {
            init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv)); doFinal(data)
        }, Charsets.UTF_8)
    }.getOrNull()
    fun clear() { prefs().edit().remove(tokenKey).apply() }
    fun hasToken(): Boolean = read() != null
}
