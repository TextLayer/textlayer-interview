#!/usr/bin/env python3
"""
Quick database schema checker
"""
import sqlite3
import os

def quick_schema():
    """Quick schema check with just the essentials"""
    
    db_path = "app/data/data.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found at app/data/data.db")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("🔍 DATABASE QUICK CHECK")
    print("=" * 30)
    print(f"📂 Database: {db_path}")
    print(f"📊 Tables: {len(tables)}")
    print()
    
    for table in tables:
        # Get columns
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        
        print(f"🗂️  {table.upper()}")
        print(f"   📈 Rows: {count:,}")
        print(f"   📋 Columns: {len(columns)}")
        
        # Show column names and types
        for col in columns[:5]:  # Show first 5 columns
            name, dtype = col[1], col[2]
            print(f"      • {name} ({dtype})")
        
        if len(columns) > 5:
            print(f"      • ... and {len(columns) - 5} more columns")
        print()
    
    conn.close()
    print("✅ Done!")

if __name__ == "__main__":
    quick_schema()
