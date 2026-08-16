package com.hypernova.app;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.io.File;

public class TradeDatabaseHelper extends SQLiteOpenHelper {

    private static final String DATABASE_NAME = "trade_memory.db";
    private static final int DATABASE_VERSION = 1;

    public static final String TABLE_TELEMETRY = "market_telemetry";
    public static final String TABLE_TRADES = "trade_records";

    public TradeDatabaseHelper(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        String createTelemetry = "CREATE TABLE " + TABLE_TELEMETRY + " (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, " +
                "symbol TEXT, " +
                "price REAL, " +
                "oir REAL, " +
                "funding_apr REAL, " +
                "volume_24h REAL, " +
                "alpha_score REAL);";

        String createTrades = "CREATE TABLE " + TABLE_TRADES + " (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, " +
                "symbol TEXT, " +
                "side TEXT, " +
                "entry_price REAL, " +
                "exit_price REAL, " +
                "pnl REAL, " +
                "roe REAL);";

        db.execSQL(createTelemetry);
        db.execSQL(createTrades);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_TELEMETRY);
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_TRADES);
        onCreate(db);
    }

    public synchronized void insertTelemetry(String symbol, double price, double oir, double fundingApr, double volume24h, double alphaScore) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues cv = new ContentValues();
        cv.put("symbol", symbol);
        cv.put("price", price);
        cv.put("oir", oir);
        cv.put("funding_apr", fundingApr);
        cv.put("volume_24h", volume24h);
        cv.put("alpha_score", alphaScore);
        db.insert(TABLE_TELEMETRY, null, cv);
    }

    public synchronized void insertTrade(String symbol, String side, double entryPrice, double exitPrice, double pnl, double roe) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues cv = new ContentValues();
        cv.put("symbol", symbol);
        cv.put("side", side);
        cv.put("entry_price", entryPrice);
        cv.put("exit_price", exitPrice);
        cv.put("pnl", pnl);
        cv.put("roe", roe);
        db.insert(TABLE_TRADES, null, cv);
    }

    public int getTelemetryCount() {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = db.rawQuery("SELECT COUNT(*) FROM " + TABLE_TELEMETRY, null);
        int count = 0;
        if (cursor.moveToFirst()) {
            count = cursor.getInt(0);
        }
        cursor.close();
        return count;
    }

    public double getTotalPnl() {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = db.rawQuery("SELECT SUM(pnl) FROM " + TABLE_TRADES, null);
        double total = 0.0;
        if (cursor.moveToFirst()) {
            total = cursor.getDouble(0);
        }
        cursor.close();
        return total;
    }

    public void clearAllData() {
        SQLiteDatabase db = this.getWritableDatabase();
        db.execSQL("DELETE FROM " + TABLE_TELEMETRY);
        db.execSQL("DELETE FROM " + TABLE_TRADES);
    }

    public static File getDatabaseFile(Context context) {
        return context.getDatabasePath(DATABASE_NAME);
    }
}
