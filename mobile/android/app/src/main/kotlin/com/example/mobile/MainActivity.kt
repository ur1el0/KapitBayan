package com.example.mobile

import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.kapitbayan.mobile/direct_caller"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "callPhone") {
                val phoneNumber = call.argument<String>("phoneNumber")
                if (phoneNumber.isNullOrBlank()) {
                    result.error("INVALID_NUMBER", "Phone number is empty", null)
                    return@setMethodCallHandler
                }

                val hasCallPermission = ContextCompat.checkSelfPermission(
                    this,
                    android.Manifest.permission.CALL_PHONE
                ) == PackageManager.PERMISSION_GRANTED

                try {
                    val intent = if (hasCallPermission) {
                        Intent(Intent.ACTION_CALL, Uri.parse("tel:$phoneNumber")).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }
                    } else {
                        Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phoneNumber")).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }
                    }
                    startActivity(intent)
                    result.success(true)
                } catch (e: Exception) {
                    result.error("CALL_FAILED", e.localizedMessage, null)
                }
            } else {
                result.notImplemented()
            }
        }
    }
}

