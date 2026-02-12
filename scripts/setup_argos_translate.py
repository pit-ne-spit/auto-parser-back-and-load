"""Скрипт для установки языковых пакетов Argos Translate."""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import logger

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    logger.error("Библиотека argostranslate не установлена!")
    logger.info("Установите: pip install argostranslate")
    sys.exit(1)


class DownloadProgress:
    """Индикатор прогресса скачивания."""
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.is_downloading = False
        self.start_time = None
        self.thread = None
    
    def start(self):
        """Начать показ прогресса."""
        self.is_downloading = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._show_progress, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Остановить показ прогресса."""
        self.is_downloading = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _show_progress(self):
        """Показывать прогресс каждые 5 секунд."""
        dots = 0
        while self.is_downloading:
            elapsed = int(time.time() - self.start_time) if self.start_time else 0
            dots = (dots + 1) % 4
            progress_dots = '.' * dots + ' ' * (3 - dots)
            logger.info(f"Скачивание пакета {self.package_name} {progress_dots} ({elapsed} сек)")
            time.sleep(5)


def setup_argos_languages():
    """Устанавливает языковые пакеты для китайского и русского."""
    logger.info("Установка языковых пакетов Argos Translate...")
    logger.info("Это может занять несколько минут...")
    
    try:
        # Обновляем список доступных языков
        logger.info("Обновление списка доступных языков...")
        argostranslate.package.update_package_index()
        logger.info("Список языков обновлен")
        
        # Получаем список доступных пакетов
        packages = argostranslate.package.get_available_packages()
        logger.info(f"Доступно пакетов для установки: {len(packages)}")
        
        # Ищем пакет для перевода с китайского на русский
        zh_ru = [p for p in packages if p.from_code == 'zh' and p.to_code == 'ru']
        
        if zh_ru:
            logger.info("Установка пакета перевода: китайский -> русский...")
            try:
                # Согласно документации: скачиваем и устанавливаем через install_from_path
                package_to_install = zh_ru[0]
                package_name = f"{package_to_install.from_code}->{package_to_install.to_code}"
                logger.info(f"Начало скачивания пакета {package_name}...")
                logger.info("Пакеты могут быть большими (200-500 МБ), это может занять несколько минут...")
                
                # Запускаем индикатор прогресса
                progress = DownloadProgress(package_name)
                progress.start()
                
                try:
                    package_path = package_to_install.download()
                finally:
                    progress.stop()
                
                logger.info(f"Скачивание завершено. Установка пакета из {package_path}...")
                argostranslate.package.install_from_path(package_path)
                logger.info("[OK] Пакет zh->ru установлен успешно")
            except Exception as e:
                logger.error(f"Ошибка при установке пакета zh->ru: {e}")
                logger.info("Попробуем установить через промежуточный язык (английский)...")
                zh_ru = []  # Пробуем альтернативный путь
        else:
            logger.info("Прямого пакета zh->ru нет, пробуем через английский...")
        
        if not zh_ru:
            # Пробуем установить через английский как промежуточный язык
            logger.info("Установка пакетов: китайский -> английский, английский -> русский...")
            zh_en = [p for p in packages if p.from_code == 'zh' and p.to_code == 'en']
            en_ru = [p for p in packages if p.from_code == 'en' and p.to_code == 'ru']
            
            if zh_en and en_ru:
                try:
                    # Первый пакет: zh->en
                    zh_en_name = f"{zh_en[0].from_code}->{zh_en[0].to_code}"
                    logger.info(f"Начало скачивания пакета {zh_en_name}...")
                    logger.info("Пакеты могут быть большими (200-500 МБ), это может занять несколько минут...")
                    
                    progress1 = DownloadProgress(zh_en_name)
                    progress1.start()
                    try:
                        zh_en_path = zh_en[0].download()
                    finally:
                        progress1.stop()
                    
                    logger.info(f"Скачивание завершено. Установка пакета из {zh_en_path}...")
                    argostranslate.package.install_from_path(zh_en_path)
                    logger.info(f"[OK] Пакет {zh_en_name} установлен")
                    
                    # Второй пакет: en->ru
                    en_ru_name = f"{en_ru[0].from_code}->{en_ru[0].to_code}"
                    logger.info(f"Начало скачивания пакета {en_ru_name}...")
                    
                    progress2 = DownloadProgress(en_ru_name)
                    progress2.start()
                    try:
                        en_ru_path = en_ru[0].download()
                    finally:
                        progress2.stop()
                    
                    logger.info(f"Скачивание завершено. Установка пакета из {en_ru_path}...")
                    argostranslate.package.install_from_path(en_ru_path)
                    logger.info(f"[OK] Пакет {en_ru_name} установлен")
                    logger.info("[OK] Пакеты установлены через промежуточный язык (английский)")
                except Exception as e:
                    logger.error(f"Ошибка при установке промежуточных пакетов: {e}", exc_info=True)
                    return False
            else:
                logger.error("Не найдены необходимые пакеты для установки!")
                if not zh_en:
                    logger.error("  Не найден пакет zh->en")
                if not en_ru:
                    logger.error("  Не найден пакет en->ru")
                return False
        
        # Проверяем установленные языки
        logger.info("\nПроверка установленных языков...")
        langs = argostranslate.translate.get_installed_languages()
        if langs:
            logger.info("Установленные языковые пакеты:")
            for lang in langs:
                logger.info(f"  {lang.code}: {lang.name}")
        else:
            logger.warning("Языковые пакеты не обнаружены после установки!")
            return False
        
        logger.info("\n[OK] Установка завершена!")
        logger.info("Теперь можно использовать Argos Translate для офлайн перевода")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при установке: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = setup_argos_languages()
    sys.exit(0 if success else 1)
