try:
    from super_cursor.mac_app import SuperCursorApp
    from super_cursor.utils import load_config, is_cursor_running
    print("✅ Importações bem-sucedidas!")
except ImportError as e:
    print(f"❌ Erro na importação: {e}") 