#!/usr/bin/env python3
"""
Script de prueba para validar la integración del Heatmap.

Este script verifica que:
1. El HeatmapAdapter se puede importar correctamente
2. Los módulos de Heatmap_Project son accesibles
3. El widget de heatmap se puede crear
4. Las utilidades de carga funcionan
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """Test que todos los imports funcionan."""
    print("=" * 60)
    print("TEST 1: Verificando imports...")
    print("=" * 60)
    
    try:
        from video_gait_analyzer.core.heatmap_adapter import HeatmapAdapter
        print("✓ HeatmapAdapter importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando HeatmapAdapter: {e}")
        return False
    
    try:
        from video_gait_analyzer.widgets.heatmap_widget import HeatmapWidget
        print("✓ HeatmapWidget importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando HeatmapWidget: {e}")
        return False
    
    try:
        from video_gait_analyzer.utils.heatmap_utils import (
            load_heatmap_data_from_directory,
            find_heatmap_data
        )
        print("✓ heatmap_utils importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando heatmap_utils: {e}")
        return False
    
    print("\n✓ Todos los imports funcionan correctamente\n")
    return True


def test_heatmap_adapter():
    """Test que el HeatmapAdapter se puede instanciar."""
    print("=" * 60)
    print("TEST 2: Verificando HeatmapAdapter...")
    print("=" * 60)
    
    try:
        from video_gait_analyzer.core.heatmap_adapter import HeatmapAdapter
        
        adapter = HeatmapAdapter()
        print(f"✓ HeatmapAdapter instanciado")
        print(f"  - Available: {adapter.is_available()}")
        print(f"  - Params: {list(adapter.params.keys())[:5]}...")
        
        # Test API methods
        print("\n✓ Verificando API methods...")
        methods = ['start', 'stop', 'pause', 'resume', 'set_rate', 'set_data', 'seek']
        for method in methods:
            if hasattr(adapter, method):
                print(f"  - {method}(): ✓")
            else:
                print(f"  - {method}(): ✗ NO ENCONTRADO")
                return False
        
        print("\n✓ HeatmapAdapter funciona correctamente\n")
        return True
        
    except Exception as e:
        print(f"✗ Error con HeatmapAdapter: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_heatmap_widget():
    """Test que el HeatmapWidget se puede instanciar."""
    print("=" * 60)
    print("TEST 3: Verificando HeatmapWidget...")
    print("=" * 60)
    
    try:
        # Qt debe estar disponible
        from PyQt5 import QtWidgets
        from video_gait_analyzer.widgets.heatmap_widget import HeatmapWidget
        
        # Create QApplication if not exists
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        
        widget = HeatmapWidget()
        print("✓ HeatmapWidget instanciado")
        print(f"  - Size: {widget.minimumWidth()}x{widget.minimumHeight()}")
        
        print("\n✓ HeatmapWidget funciona correctamente\n")
        return True
        
    except Exception as e:
        print(f"✗ Error con HeatmapWidget: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_loading():
    """Test las funciones de carga de datos."""
    print("=" * 60)
    print("TEST 4: Verificando carga de datos...")
    print("=" * 60)
    
    try:
        from video_gait_analyzer.utils.heatmap_utils import find_heatmap_data
        
        # Test con directorio de ejemplo
        test_dir = os.path.join(project_root, "Heatmap_Project", "test_data")
        
        if os.path.exists(test_dir):
            print(f"✓ Directorio de prueba encontrado: {test_dir}")
            
            files = find_heatmap_data(test_dir)
            if files:
                print("✓ Archivos de heatmap encontrados:")
                for key, path in files.items():
                    if path:
                        print(f"  - {key}: {os.path.basename(path)}")
                    else:
                        print(f"  - {key}: (no encontrado)")
            else:
                print("⚠ No se encontraron archivos de heatmap (puede ser normal)")
        else:
            print(f"⚠ Directorio de prueba no existe: {test_dir}")
            print("  (esto es normal si no tienes test_data)")
        
        print("\n✓ Funciones de carga disponibles\n")
        return True
        
    except Exception as e:
        print(f"✗ Error probando carga de datos: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_heatmap_project_availability():
    """Test si Heatmap_Project está disponible."""
    print("=" * 60)
    print("TEST 5: Verificando Heatmap_Project...")
    print("=" * 60)
    
    try:
        heatmap_path = os.path.join(project_root, "Heatmap_Project")
        
        if not os.path.exists(heatmap_path):
            print(f"✗ Directorio Heatmap_Project no encontrado: {heatmap_path}")
            return False
        
        print(f"✓ Directorio Heatmap_Project encontrado")
        
        # Check required files
        required_files = ['animator.py', 'heatmap.py', 'prerenderer.py']
        for fname in required_files:
            fpath = os.path.join(heatmap_path, fname)
            if os.path.exists(fpath):
                print(f"  - {fname}: ✓")
            else:
                print(f"  - {fname}: ✗ NO ENCONTRADO")
                return False
        
        print("\n✓ Heatmap_Project está disponible\n")
        return True
        
    except Exception as e:
        print(f"✗ Error verificando Heatmap_Project: {e}")
        return False


def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE INTEGRACIÓN DEL HEATMAP")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Heatmap_Project disponible", test_heatmap_project_availability()))
    results.append(("Imports", test_imports()))
    results.append(("HeatmapAdapter", test_heatmap_adapter()))
    results.append(("HeatmapWidget", test_heatmap_widget()))
    results.append(("Carga de datos", test_data_loading()))
    
    # Summary
    print("=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "=" * 60)
    print(f"Total: {passed}/{total} tests pasados")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("✓ ¡Todos los tests pasaron! La integración está lista.")
        return 0
    else:
        print("✗ Algunos tests fallaron. Revisar errores arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
