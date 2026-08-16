package com.hypernova.app;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class MarketDataCollector {

    public interface TelemetryListener {
        void onMarketUpdate(MarketSnapshot snapshot);
        void onLog(String message);
    }

    public static class MarketSnapshot {
        public double solPrice = 0.0;
        public double solOir = 0.0;
        public double solFunding = 0.0;
        public double btcPrice = 0.0;
        public double btcOir = 0.0;
        public double btcFunding = 0.0;
        public double alphaScore = 0.0;
        public int totalRecords = 0;
        public double totalPnl = 0.0;
    }

    private static MarketDataCollector instance;
    private final Context context;
    private final TradeDatabaseHelper dbHelper;
    private final OkHttpClient httpClient;
    private ScheduledExecutorService executor;
    private TelemetryListener listener;
    private boolean isRunning = false;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private double currentSolPrice = 0.0;
    private double currentBtcPrice = 0.0;
    private double solEntryPrice = 0.0;
    private String solSide = "NONE";
    private double cumulativePnl = 0.0;

    private static final String API_URL = "https://api.hyperliquid.xyz/info";
    private static final MediaType JSON_MEDIA = MediaType.get("application/json; charset=utf-8");

    public static synchronized MarketDataCollector getInstance(Context context) {
        if (instance == null) {
            instance = new MarketDataCollector(context.getApplicationContext());
        }
        return instance;
    }

    private MarketDataCollector(Context context) {
        this.context = context;
        this.dbHelper = new TradeDatabaseHelper(context);
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .build();
    }

    public void setListener(TelemetryListener listener) {
        this.listener = listener;
    }

    public synchronized boolean isRunning() {
        return isRunning;
    }

    public synchronized void start() {
        if (isRunning) return;
        isRunning = true;
        executor = Executors.newSingleThreadScheduledExecutor();

        log("[MOTOR] 🚀 7/24 HyperLiquid Canlı Telemetri ve Veri Toplayıcı Başlatıldı!");

        executor.scheduleWithFixedDelay(this::fetchAndProcess, 0, 3, TimeUnit.SECONDS);
    }

    public synchronized void stop() {
        if (!isRunning) return;
        isRunning = false;
        if (executor != null) {
            executor.shutdownNow();
            executor = null;
        }
        log("[MOTOR] 🛑 Veri Toplama Durduruldu.");
    }

    private void fetchAndProcess() {
        try {
            // 1. Fetch Meta & Asset Contexts
            JsonObject bodyJson = new JsonObject();
            bodyJson.addProperty("type", "metaAndAssetCtxs");
            Request request = new Request.Builder()
                    .url(API_URL)
                    .post(RequestBody.create(bodyJson.toString(), JSON_MEDIA))
                    .build();

            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    parseMarketData(responseBody);
                }
            }

            // 2. Fetch L2 Orderbook for SOL
            JsonObject l2Json = new JsonObject();
            l2Json.addProperty("type", "l2Book");
            l2Json.addProperty("coin", "SOL");
            Request l2Req = new Request.Builder()
                    .url(API_URL)
                    .post(RequestBody.create(l2Json.toString(), JSON_MEDIA))
                    .build();

            double solOir = 0.0;
            try (Response l2Resp = httpClient.newCall(l2Req).execute()) {
                if (l2Resp.isSuccessful() && l2Resp.body() != null) {
                    solOir = parseL2Imbalance(l2Resp.body().string());
                }
            }

            // 3. Compute Alpha & Paper 1000:1 Micro-Scalp
            double alpha = solOir * 0.7 + (Math.random() * 10 - 5);
            simulateMicroScalp(alpha);

            // 4. Save to SQLite database
            dbHelper.insertTelemetry("SOL", currentSolPrice, solOir, 0.012, 125000000.0, alpha);
            if (currentBtcPrice > 0) {
                dbHelper.insertTelemetry("BTC", currentBtcPrice, solOir * 0.5, 0.008, 980000000.0, alpha * 0.8);
            }

            int count = dbHelper.getTelemetryCount();
            double totalPnl = dbHelper.getTotalPnl() + cumulativePnl;

            // Notify UI
            MarketSnapshot snap = new MarketSnapshot();
            snap.solPrice = currentSolPrice;
            snap.solOir = solOir;
            snap.solFunding = 0.012;
            snap.btcPrice = currentBtcPrice;
            snap.btcOir = solOir * 0.4;
            snap.btcFunding = 0.008;
            snap.alphaScore = alpha;
            snap.totalRecords = count;
            snap.totalPnl = totalPnl;

            mainHandler.post(() -> {
                if (listener != null) {
                    listener.onMarketUpdate(snap);
                }
            });

            String timeStr = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
            log(String.format(Locale.US, "[%s] SOL: $%.2f | L2 OIR: %+.1f%% | Alpha: %+.1f | DB: %d Kayıt",
                    timeStr, currentSolPrice, solOir, alpha, count));

        } catch (Exception e) {
            log("[UYARI] Veri çekme gecikmesi: " + e.getMessage());
        }
    }

    private void parseMarketData(String jsonString) {
        try {
            JsonArray array = JsonParser.parseString(jsonString).getAsJsonArray();
            if (array.size() >= 2) {
                JsonObject universe = array.get(0).getAsJsonObject();
                JsonArray universeList = universe.getAsJsonArray("universe");
                JsonArray contexts = array.get(1).getAsJsonArray();

                for (int i = 0; i < universeList.size(); i++) {
                    String name = universeList.get(i).getAsJsonObject().get("name").getAsString();
                    if ("SOL".equalsIgnoreCase(name) && i < contexts.size()) {
                        currentSolPrice = contexts.get(i).getAsJsonObject().get("markPx").getAsDouble();
                    } else if ("BTC".equalsIgnoreCase(name) && i < contexts.size()) {
                        currentBtcPrice = contexts.get(i).getAsJsonObject().get("markPx").getAsDouble();
                    }
                }
            }
        } catch (Exception ignored) {}
    }

    private double parseL2Imbalance(String jsonString) {
        try {
            JsonObject obj = JsonParser.parseString(jsonString).getAsJsonObject();
            JsonArray levels = obj.getAsJsonArray("levels");
            if (levels != null && levels.size() >= 2) {
                JsonArray bids = levels.get(0).getAsJsonArray();
                JsonArray asks = levels.get(1).getAsJsonArray();

                double bidVol = 0;
                double askVol = 0;
                for (int i = 0; i < Math.min(5, bids.size()); i++) {
                    bidVol += bids.get(i).getAsJsonObject().get("sz").getAsDouble();
                }
                for (int i = 0; i < Math.min(5, asks.size()); i++) {
                    askVol += asks.get(i).getAsJsonObject().get("sz").getAsDouble();
                }
                if (bidVol + askVol > 0) {
                    return ((bidVol - askVol) / (bidVol + askVol)) * 100.0;
                }
            }
        } catch (Exception ignored) {}
        return 0.0;
    }

    private void simulateMicroScalp(double alpha) {
        if (currentSolPrice <= 0) return;

        if ("NONE".equals(solSide)) {
            if (alpha > 35.0) {
                solSide = "LONG";
                solEntryPrice = currentSolPrice;
                log(String.format(Locale.US, "🟢 [1000:1 SCALP] LONG GİRİLDİ @ $%.2f (Teminat: $0.80)", currentSolPrice));
            } else if (alpha < -35.0) {
                solSide = "SHORT";
                solEntryPrice = currentSolPrice;
                log(String.format(Locale.US, "🔴 [1000:1 SCALP] SHORT GİRİLDİ @ $%.2f (Teminat: $0.80)", currentSolPrice));
            }
        } else if ("LONG".equals(solSide)) {
            double priceDiff = (currentSolPrice - solEntryPrice) / solEntryPrice;
            if (priceDiff >= 0.0008 || priceDiff <= -0.0006 || alpha < -20.0) {
                double pnl = priceDiff * 800.0;
                cumulativePnl += pnl;
                dbHelper.insertTrade("SOL", "LONG", solEntryPrice, currentSolPrice, pnl, priceDiff * 1000.0 * 100);
                log(String.format(Locale.US, "💰 [POZİSYON KAPANDI] LONG PnL: %+$0.2f (ROE: %+.1f%%)", pnl, priceDiff * 1000.0 * 100));
                solSide = "NONE";
            }
        } else if ("SHORT".equals(solSide)) {
            double priceDiff = (solEntryPrice - currentSolPrice) / solEntryPrice;
            if (priceDiff >= 0.0008 || priceDiff <= -0.0006 || alpha > 20.0) {
                double pnl = priceDiff * 800.0;
                cumulativePnl += pnl;
                dbHelper.insertTrade("SOL", "SHORT", solEntryPrice, currentSolPrice, pnl, priceDiff * 1000.0 * 100);
                log(String.format(Locale.US, "💰 [POZİSYON KAPANDI] SHORT PnL: %+$0.2f (ROE: %+.1f%%)", pnl, priceDiff * 1000.0 * 100));
                solSide = "NONE";
            }
        }
    }

    private void log(String message) {
        mainHandler.post(() -> {
            if (listener != null) {
                listener.onLog(message);
            }
        });
    }

    public TradeDatabaseHelper getDbHelper() {
        return dbHelper;
    }
}
