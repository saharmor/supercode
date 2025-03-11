try:
    from super_surf.mac_app import SuperSurfApp
    from super_surf.utils import load_config, is_surf_running
    print("✅ Importações bem-sucedidas!")
except ImportError as e:
    print(f"❌ Erro na importação: {e}") 