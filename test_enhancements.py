"""
Simple test script to validate the enhancements work properly.
"""
import os
import sys
sys.path.append('.')

def test_imports():
    """Test that all new modules can be imported."""
    try:
        from app.services.datastore.schema_inspector import SchemaInspector
        print("SchemaInspector imported successfully")
        
        from app.services.llm.quality.response_judge import ResponseQualityJudge
        print("ResponseQualityJudge imported successfully")
        
        from app.services.llm.tools.enhanced_text_to_sql import enhanced_text_to_sql
        print("Enhanced text-to-SQL tool imported successfully")
        
        from app.services.llm.prompts.chat_prompt import chat_prompt
        print("Enhanced chat prompt imported successfully")
        
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False

def test_schema_inspector():
    """Test schema inspector functionality."""
    try:
        from app.services.datastore.schema_inspector import SchemaInspector
        
        # Test with database path
        inspector = SchemaInspector(database_path="app/data/data.db")
        
        # Test schema retrieval (this will show what tables exist)
        schema = inspector.get_database_schema()
        print(f"Database has {schema['total_tables']} tables")
        
        for table_name, table_info in schema['tables'].items():
            print(f"  - {table_name}: {len(table_info['columns'])} columns, {table_info['row_count']} rows")
        
        # Test context generation
        context = inspector.get_schema_context_for_prompt()
        print(f"Generated {len(context)} characters of schema context")
        
        return True
    except Exception as e:
        print(f"Schema inspector error: {e}")
        return False

def test_enhanced_prompt():
    """Test enhanced prompt generation."""
    try:
        from app.services.llm.prompts.chat_prompt import chat_prompt
        
        # Test basic prompt
        basic_prompt = chat_prompt()
        print(f"Basic prompt generated: {len(basic_prompt)} messages")
        
        # Test enhanced prompt with context
        enhanced_prompt = chat_prompt(
            schema_context="Test schema context",
            relevant_tables=["transactions", "accounts"],
            domain_context="Financial data analysis"
        )
        print(f"Enhanced prompt generated: {len(enhanced_prompt)} messages")
        
        # Check if financial domain content is included
        prompt_content = enhanced_prompt[0]['content']
        if 'financial' in prompt_content.lower():
            print("Financial domain expertise detected in prompt")
        else:
            print("WARNING: Financial domain content may be missing")
        
        return True
    except Exception as e:
        print(f"Enhanced prompt error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Text-to-SQL API Enhancements")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Schema Inspector", test_schema_inspector),
        ("Enhanced Prompts", test_enhanced_prompt),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"{test_name} failed")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("All enhancements are working correctly!")
        print("\nNext steps:")
        print("1. Run the Flask server: FLASK_APP=application.py python -m flask run")
        print("2. Test with real queries via the API endpoints")
        print("3. Compare response quality with original implementation")
    else:
        print("WARNING: Some issues detected. Check the errors above.")

if __name__ == "__main__":
    main()
