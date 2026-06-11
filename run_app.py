# run_app.py
import sys
import traceback

from style_loader import load_styles

def check_database_before_gui():
    """Проверка БД перед запуском GUI"""
    print("🔍 Предварительная проверка подключения к БД...")
    
    try:
        import mysql.connector
        from db_config import mysql_connect_kwargs

        conn = mysql.connector.connect(
            **mysql_connect_kwargs(),
            connection_timeout=3,
        )
        
        if conn.is_connected():
            print("✅ Подключение к БД успешно!")
            conn.close()
            return True
        else:
            print("❌ Не удалось подключиться к БД")
            return False
            
    except ImportError:
        print("❌ Библиотека mysql-connector-python не установлена")
        print("   Установите: pip install mysql-connector-python")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def main():
    """Главная функция запуска"""
    
    # Проверяем БД перед запуском GUI
    if not check_database_before_gui():
        print("\n⚠️ Продолжить без БД? (y/n)")
        choice = input().lower().strip()
        
        if choice != 'y':
            print("Выход...")
            sys.exit(1)
    
    # Запускаем GUI
    print("\n🚀 Запуск графического интерфейса...")
    
    try:
        from main import MainWindow
        from PyQt5 import QtWidgets
        
        app = QtWidgets.QApplication(sys.argv)
        load_styles(app) 
            
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Ошибка при запуске GUI: {e}")
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()