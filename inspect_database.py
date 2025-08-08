"""
Comprehensive database inspection script for TextLayer financial database
"""
import os
from pathlib import Path

try:
    import duckdb
    DB_TYPE = "duckdb"
except ImportError:
    try:
        import sqlite3
        DB_TYPE = "sqlite"
        print("⚠️  DuckDB not found, falling back to SQLite")
    except ImportError:
        print("❌ Neither DuckDB nor SQLite available!")
        exit(1)

def inspect_database():
    """Inspect the database structure and show all details"""
    
    # Find the database file
    db_path = "app/data/data.db" 
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("Looking for database files...")
        
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".db"):
                    print(f"  Found: {os.path.join(root, file)}")
        return
    
    print("=" * 70)
    print("🔍 DATABASE STRUCTURE INSPECTION")
    print("=" * 70)
    print(f"📂 Database: {db_path}")
    print(f"🔧 Using: {DB_TYPE.upper()}")
    
    try:
        if DB_TYPE == "duckdb":
            conn = duckdb.connect(db_path)
            cursor = conn.cursor()
            
            print(f"\n{'='*20} 📊 TABLES {'='*20}")
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name;")
            tables = cursor.fetchall()
        else:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print(f"\n{'='*20} 📊 TABLES {'='*20}")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in database!")
            return
        
        table_names = [table[0] for table in tables]
        print(f"Found {len(tables)} tables:")
        for i, table in enumerate(table_names, 1):
            print(f"  {i:2d}. {table}")
        
        for table_name in table_names:
            print(f"\n{'='*50}")
            print(f"🔍 TABLE: {table_name.upper()}")
            print(f"{'='*50}")
            
            if DB_TYPE == "duckdb":
                cursor.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
                columns_info = cursor.fetchall()
                
                print(f"\n📋 COLUMNS ({len(columns_info)} total):")
                print(f"{'No.':<4} {'Name':<25} {'Type':<15} {'Nullable'}")
                print("-" * 70)
                
                for i, (name, data_type, nullable) in enumerate(columns_info, 1):
                    print(f"{i:<4} {name:<25} {data_type:<15} {nullable}")
            else:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                print(f"\n📋 COLUMNS ({len(columns)} total):")
                print(f"{'No.':<4} {'Name':<20} {'Type':<12} {'Null':<6} {'Default':<10} {'PK'}")
                print("-" * 65)
                
                for col in columns:
                    col_id, name, data_type, not_null, default, pk = col
                    null_str = "NO" if not_null else "YES"
                    default_str = str(default) if default else ""
                    pk_str = "YES" if pk else ""
                    
                    print(f"{col_id+1:<4} {name:<20} {data_type:<12} {null_str:<6} {default_str:<10} {pk_str}")
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"\n📈 ROW COUNT: {row_count:,}")
            
            if row_count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                sample_data = cursor.fetchall()
                
                print(f"\n🔬 SAMPLE DATA (first 3 rows):")
                col_names = [desc[0] for desc in cursor.description]
                
                # Print headers
                header = " | ".join(f"{name[:15]:<15}" for name in col_names)
                print(header)
                print("-" * len(header))
                
                # Print data rows
                for row in sample_data:
                    row_str = " | ".join(f"{str(val)[:15]:<15}" for val in row)
                    print(row_str)
            else:
                print("📭 Table is empty")
        
        print(f"\n{'='*30} 🔗 RELATIONSHIPS {'='*30}")
        
        if DB_TYPE == "duckdb":
            print("Foreign key information not readily available in DuckDB")
        else:
            has_relationships = False
            
            for table_name in table_names:
                cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                fks = cursor.fetchall()
                
                if fks:
                    has_relationships = True
                    print(f"\n{table_name}:")
                    for fk in fks:
                        id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                        print(f"  └─ {from_col} → {ref_table}.{to_col}")
            
            if not has_relationships:
                print("No foreign key relationships defined")
        
        if DB_TYPE == "sqlite":
            print(f"\n{'='*30} 📇 INDEXES {'='*30}")
            cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY tbl_name;")
            indexes = cursor.fetchall()
            
            if indexes:
                for index_name, table_name, sql in indexes:
                    print(f"  {index_name} on {table_name}")
            else:
                print("No custom indexes found")
        
        print(f"\n{'='*30} 📁 FILE INFO {'='*30}")
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"File size: {file_size:,} bytes ({file_size_mb:.2f} MB)")

        key_tables = ['financial_data', 'account', 'customer', 'product', 'time']
        existing_key_tables = [t for t in key_tables if t in table_names]
        
        if existing_key_tables:
            print(f"\n{'='*25} 📊 KEY TABLE SUMMARY {'='*25}")
            for table in existing_key_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                
                if DB_TYPE == "duckdb":
                    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position LIMIT 5;")
                    cols_result = cursor.fetchall()
                    first_cols = [col[0] for col in cols_result]
                else:
                    cursor.execute(f"PRAGMA table_info({table});")
                    cols = cursor.fetchall()
                    first_cols = [col[1] for col in cols[:5]]
                
                sample_info = ""
                if first_cols and count > 0:
                    try:
                        first_col = first_cols[0]
                        cursor.execute(f"SELECT DISTINCT {first_col} FROM {table} WHERE {first_col} IS NOT NULL LIMIT 3;")
                        samples = cursor.fetchall()
                        if samples:
                            sample_values = [str(s[0])[:20] for s in samples if s[0]]
                            if sample_values:
                                sample_info = f" (e.g., {', '.join(sample_values[:2])})"
                    except:
                        pass 
                
                cols_str = ', '.join(first_cols[:3]) + ('...' if len(first_cols) > 3 else '')
                print(f"  {table:<15}: {count:>6,} rows | Cols: {cols_str}{sample_info}")
        
        conn.close()
        
        print(f"\n{'='*70}")
        print("✅ INSPECTION COMPLETE!")
        print("💡 Use this information to write accurate SQL queries")
        print("💡 Pay attention to column names, data types, and relationships")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

def quick_table_overview():
    """Quick overview of tables and columns"""
    db_path = "app/data/data.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    try:
        if DB_TYPE == "duckdb":
            conn = duckdb.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name;")
        else:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        
        tables = cursor.fetchall()
        
        print("🚀 QUICK TABLE OVERVIEW")
        print("=" * 40)
        
        for table in tables:
            table_name = table[0]
            
            if DB_TYPE == "duckdb":
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
                columns = cursor.fetchall()
                col_names = [col[0] for col in columns]
            else:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            
            print(f"\n📊 {table_name.upper()}")
            print(f"   Rows: {row_count:,}")
            print(f"   Cols: {', '.join(col_names[:6])}" + ("..." if len(col_names) > 6 else ""))
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Choose inspection type:")
    print("1. Full detailed inspection (recommended)")
    print("2. Quick overview")
    print()
    
    choice = input("Enter choice (1 or 2, or just press Enter for full): ").strip()
    
    if choice == "2":
        quick_table_overview()
    else:
        inspect_database()
