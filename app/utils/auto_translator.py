"""Автоматический переводчик через внешние API."""

import os
import time
from typing import Dict, Any, Optional, List
import requests
from app.utils.logger import logger


class AutoTranslator:
    """Автоматический переводчик с поддержкой нескольких провайдеров."""
    
    def __init__(self, provider: str = "argos", api_key: Optional[str] = None):
        """
        Инициализация переводчика.
        
        Args:
            provider: Провайдер перевода ("argos" - офлайн, "deep_translator", "translators", "google", "deepl", "yandex")
            api_key: API ключ (если требуется)
        """
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_TRANSLATE_API_KEY")
        self.rate_limit_delay = 0.1  # Задержка между запросами (секунды)
        
    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "ru") -> str:
        """
        Переводит текст с китайского на русский.
        
        Args:
            text: Текст для перевода
            source_lang: Исходный язык (по умолчанию: zh - китайский)
            target_lang: Целевой язык (по умолчанию: ru - русский)
        
        Returns:
            Переведенный текст или оригинал при ошибке
        """
        if not text or not isinstance(text, str):
            return text
        
        # Убираем лишние пробелы
        text = text.strip()
        if not text:
            return text
        
        try:
            if self.provider == "deep_translator":
                return self._translate_deep_translator(text, source_lang, target_lang)
            elif self.provider == "translators":
                return self._translate_translators(text, source_lang, target_lang)
            elif self.provider == "argos":
                return self._translate_argos(text, source_lang, target_lang)
            elif self.provider == "google":
                return self._translate_google(text, source_lang, target_lang)
            elif self.provider == "deepl":
                return self._translate_deepl(text, source_lang, target_lang)
            elif self.provider == "yandex":
                return self._translate_yandex(text, source_lang, target_lang)
            else:
                logger.warning(f"Неизвестный провайдер: {self.provider}, используем deep_translator")
                return self._translate_deep_translator(text, source_lang, target_lang)
        except Exception as e:
            logger.error(f"Ошибка при переводе '{text[:50]}...': {e}")
            return text
    
    def _translate_deep_translator(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через deep-translator (рекомендуется)."""
        try:
            from deep_translator import GoogleTranslator
            
            time.sleep(self.rate_limit_delay)
            
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            return result
        except ImportError:
            logger.error("Библиотека deep-translator не установлена. Установите: pip install deep-translator")
            return text
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "language" in error_msg:
                logger.debug(f"Не удалось перевести '{text[:50]}...' через deep-translator")
            else:
                logger.debug(f"Ошибка deep-translator для '{text[:50]}...': {e}")
            return text
    
    def _translate_translators(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через библиотеку translators (поддержка множества провайдеров)."""
        try:
            import translators as ts
            
            time.sleep(self.rate_limit_delay)
            
            # Используем Google как провайдер по умолчанию
            result = ts.google(text, from_language=source_lang, to_language=target_lang)
            return result
        except ImportError:
            logger.error("Библиотека translators не установлена. Установите: pip install translators")
            return text
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "language" in error_msg:
                logger.debug(f"Не удалось перевести '{text[:50]}...' через translators")
            else:
                logger.debug(f"Ошибка translators для '{text[:50]}...': {e}")
            return text
    
    def _translate_argos(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через Argos Translate (полностью офлайн)."""
        try:
            import argostranslate.translate
            
            # Устанавливаем языковые коды для Argos
            # Argos использует коды: 'zh' для китайского, 'ru' для русского
            argos_source = "zh" if source_lang == "zh" else source_lang
            argos_target = "ru" if target_lang == "ru" else target_lang
            
            # Используем функцию translate с кодами языков (самый простой способ)
            # Argos автоматически найдет подходящий пакет (прямой или через промежуточный язык)
            try:
                result = argostranslate.translate.translate(text, argos_source, argos_target)
                if result and result != text:
                    return result
                else:
                    logger.debug(f"Argos Translate вернул оригинал для '{text[:50]}...' (zh->ru)")
                    return text
            except Exception as e:
                logger.debug(f"Ошибка при переводе через Argos: {e}")
                return text
        except ImportError:
            logger.error("Библиотека argostranslate не установлена. Установите: pip install argostranslate")
            return text
        except Exception as e:
            logger.debug(f"Ошибка Argos Translate для '{text[:50]}...': {e}")
            return text
    
    def _translate_google(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через Google Translate (бесплатный API через googletrans)."""
        try:
            from googletrans import Translator
            
            translator = Translator()
            time.sleep(self.rate_limit_delay)  # Rate limiting
            
            # Пробуем сначала с указанным языком
            try:
                result = translator.translate(text, src=source_lang, dest=target_lang)
                return result.text
            except Exception as e1:
                # Если не получилось с указанным языком, пробуем автоопределение
                if "invalid source language" in str(e1).lower() or "invalid" in str(e1).lower():
                    try:
                        logger.debug(f"Пробуем автоопределение языка для: {text[:50]}")
                        result = translator.translate(text, src='auto', dest=target_lang)
                        # Проверяем, что результат действительно переведен
                        if result.src != target_lang and result.text != text:
                            return result.text
                        else:
                            # Если язык определен как целевой или текст не изменился, возвращаем оригинал
                            logger.debug(f"Язык определен как {result.src}, текст не изменен")
                            return text
                    except Exception as e2:
                        logger.debug(f"Ошибка при автоопределении языка: {e2}")
                        return text
                else:
                    raise e1
        except ImportError:
            logger.error("Библиотека googletrans не установлена. Установите: pip install googletrans==4.0.0rc1")
            return text
        except Exception as e:
            # Для частых ошибок (invalid source language) не логируем как ERROR
            error_msg = str(e).lower()
            if "invalid source language" in error_msg or "invalid" in error_msg:
                logger.debug(f"Не удалось определить язык для '{text[:50]}...'")
            else:
                logger.debug(f"Ошибка Google Translate для '{text[:50]}...': {e}")
            return text
    
    def _translate_deepl(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через DeepL API."""
        if not self.api_key:
            logger.error("DeepL API ключ не установлен. Установите DEEPL_TRANSLATE_API_KEY")
            return text
        
        try:
            # DeepL использует коды языков: ZH для китайского, RU для русского
            deepl_source = "ZH" if source_lang == "zh" else source_lang.upper()
            deepl_target = "RU" if target_lang == "ru" else target_lang.upper()
            
            url = "https://api-free.deepl.com/v2/translate" if "free" in self.api_key.lower() else "https://api.deepl.com/v2/translate"
            
            response = requests.post(
                url,
                headers={
                    "Authorization": f"DeepL-Auth-Key {self.api_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "text": text,
                    "source_lang": deepl_source,
                    "target_lang": deepl_target
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["translations"][0]["text"]
            else:
                logger.error(f"DeepL API ошибка: {response.status_code} - {response.text}")
                return text
        except Exception as e:
            logger.error(f"Ошибка DeepL API: {e}")
            return text
    
    def _translate_yandex(self, text: str, source_lang: str, target_lang: str) -> str:
        """Перевод через Yandex Translate API."""
        if not self.api_key:
            logger.error("Yandex API ключ не установлен. Установите YANDEX_TRANSLATE_API_KEY")
            return text
        
        try:
            url = "https://translate.yandex.net/api/v1.5/tr.json/translate"
            
            response = requests.post(
                url,
                params={
                    "key": self.api_key,
                    "text": text,
                    "lang": f"{source_lang}-{target_lang}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return " ".join(result["text"])
            else:
                logger.error(f"Yandex API ошибка: {response.status_code} - {response.text}")
                return text
        except Exception as e:
            logger.error(f"Ошибка Yandex API: {e}")
            return text
    
    def translate_batch(self, texts: List[str], source_lang: str = "zh", target_lang: str = "ru") -> List[str]:
        """
        Переводит список текстов батчами.
        
        Args:
            texts: Список текстов для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Список переведенных текстов
        """
        results = []
        for text in texts:
            translated = self.translate(text, source_lang, target_lang)
            results.append(translated)
        return results


def get_auto_translator(provider: Optional[str] = None) -> AutoTranslator:
    """
    Создает экземпляр автоматического переводчика.
    
    Args:
        provider: Провайдер ("deep_translator", "translators", "argos", "google", "deepl", "yandex") 
                 или None для автоопределения
    
    Returns:
        Экземпляр AutoTranslator
    """
    if provider:
        return AutoTranslator(provider=provider)
    
    # Автоопределение провайдера по переменным окружения
    if os.getenv("DEEPL_TRANSLATE_API_KEY"):
        return AutoTranslator(provider="deepl")
    elif os.getenv("YANDEX_TRANSLATE_API_KEY"):
        return AutoTranslator(provider="yandex")
    else:
        # По умолчанию используем Argos (офлайн, не требует интернета)
        try:
            import argostranslate
            return AutoTranslator(provider="argos")
        except ImportError:
            # Если Argos не установлен, пробуем deep-translator
            try:
                import deep_translator
                return AutoTranslator(provider="deep_translator")
            except ImportError:
                # Если deep-translator не установлен, пробуем translators
                try:
                    import translators
                    return AutoTranslator(provider="translators")
                except ImportError:
                    # В крайнем случае используем старый googletrans
                    return AutoTranslator(provider="google")
