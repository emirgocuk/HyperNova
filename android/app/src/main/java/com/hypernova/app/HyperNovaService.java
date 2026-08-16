package com.hypernova.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import androidx.core.app.NotificationCompat;

public class HyperNovaService extends Service {

    private static final String CHANNEL_ID = "HyperNova_Telemetry_Channel";
    private static final int NOTIFICATION_ID = 2026;
    private PowerManager.WakeLock wakeLock;
    private MarketDataCollector collector;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();

        // 1. Acquire WakeLock (Keeps CPU running 7/24 even with screen off)
        PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (powerManager != null) {
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HyperNova::TelemetryWakeLock");
            wakeLock.acquire();
        }

        // 2. Start Foreground Notification
        Notification notification = buildNotification("7/24 Kesintisiz Veri Toplama Aktif...");
        startForeground(NOTIFICATION_ID, notification);

        // 3. Start Native Background Telemetry Engine
        collector = MarketDataCollector.getInstance(this);
        collector.start();
    }

    private Notification buildNotification(String text) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("⚡ HyperNova 7/24 Veri Toplayıcı")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "HyperNova 7/24 Telemetry Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("7/24 Kesintisiz L2 Derinlik, Fonlama ve İşlem Verisi Toplayıcı");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (collector != null) {
            collector.stop();
        }
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
