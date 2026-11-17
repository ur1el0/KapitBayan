package com.example.mobile

import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.kapitbayan.mobile/direct_caller"
    private val CALL_PERMISSION_REQUEST_CODE = 1001
    private var pendingNumber: String? = null
    private var pendingResult: MethodChannel.Result? = null

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

                if (hasCallPermission) {
                    executeDirectCall(phoneNumber)
                    result.success(true)
                } else {
                    pendingNumber = phoneNumber
                    pendingResult = result
                    ActivityCompat.requestPermissions(
                        this,
                        arrayOf(android.Manifest.permission.CALL_PHONE),
                        CALL_PERMISSION_REQUEST_CODE
                    )
                }
            } else {
                result.notImplemented()
            }
        }
    }

    private fun executeDirectCall(phoneNumber: String) {
        val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$phoneNumber")).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        startActivity(intent)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CALL_PERMISSION_REQUEST_CODE) {
            val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
            val number = pendingNumber
            if (number != null) {
                if (granted) {
                    executeDirectCall(number)
                } else {
                    val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$number")).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    startActivity(dialIntent)
                }
            }
            pendingResult?.success(granted)
            pendingNumber = null
            pendingResult = null
        }
    }
}
